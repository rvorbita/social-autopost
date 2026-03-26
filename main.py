
import os
import io
import sys
import json
import textwrap
import asyncio
import requests
import smtplib
from email.mime.text import MIMEText
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from dotenv import load_dotenv
from pydantic import BaseModel

# ✅ Modern SDK Imports
from huggingface_hub import AsyncInferenceClient
from google import genai
from google.genai import types

# -----------------------------
# LOG CAPTURE (New Feature)
# -----------------------------
# This captures everything printed to the console so we can email it later
log_buffer = io.StringIO()

class LogCatcher:
    def __init__(self, terminal, buffer):
        self.terminal = terminal
        self.buffer = buffer

    def write(self, message):
        self.terminal.write(message)
        self.buffer.write(message)

    def flush(self):
        self.terminal.flush()
        self.buffer.flush()

# Redirect standard output to our catcher
sys.stdout = LogCatcher(sys.stdout, log_buffer)

# -----------------------------
# SETUP & CONFIG
# -----------------------------
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
hf_client = AsyncInferenceClient(token=os.getenv("HF_TOKEN"))

WIDTH = 1024
HEIGHT = 1024
FONT_PATH = "Montserrat-Bold.ttf" 
FONT_SIZE = 65

YELLOW_HIGHLIGHT = (255, 215, 0)
TEXT_COLOR = (255, 255, 255)
BAR_COLOR = (0, 0, 0)

# -----------------------------
# SCHEMAS
# -----------------------------
class TopicList(BaseModel):
    topics: list[str]

class PostContent(BaseModel):
    headline: str
    main_topic: str
    caption: str
    image_prompt: str

# -----------------------------
# HELPERS
# -----------------------------
def clean_json(text):
    start = text.find('{')
    end = text.rfind('}')
    return text[start:end+1] if start != -1 else "{}"

def post_to_facebook(image_path: str, caption: str):
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_ACCESS_TOKEN")
    
    if not page_id or not token:
        print("⚠️ Facebook credentials missing. Skipping upload.")
        return False

    url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
    
    with open(image_path, 'rb') as f:
        payload = {'message': caption, 'access_token': token}
        files = {'source': f}
        res = requests.post(url, data=payload, files=files)
        
    if res.status_code == 200:
        print(f"✅ Facebook post successful! Post ID: {res.json().get('id')}")
        return True
    else:
        print(f"❌ Facebook post failed: {res.text}")
        return False

# -----------------------------
# NOTIFICATION SYSTEM (New Feature)
# -----------------------------
def send_email_report(status, topic_name):
    """Sends an email with the execution status and attached logs."""
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_PASSWORD") # Must be an App Password
    receiver_email = os.getenv("EMAIL_RECEIVER")
    
    if not all([sender_email, sender_password, receiver_email]):
        print("⚠️ Email credentials missing in secrets. Skipping email notification.")
        return

    # Set subject based on success or failure
    icon = "✅ SUCCESS" if status == "success" else "❌ FAILED"
    subject = f"{icon}: No Way Daily Auto-Post ({topic_name})"
    
    # Grab all the captured print statements
    captured_logs = log_buffer.getvalue()
    
    # Construct the email body
    body = f"The No Way Daily automation has completed.\n\n"
    body += f"Status: {status.upper()}\n"
    body += f"Topic: {topic_name}\n\n"
    body += "-"*40 + "\n"
    body += "GITHUB ACTION LOGS:\n"
    body += "-"*40 + "\n\n"
    body += captured_logs

    msg = MIMEText(body, 'plain',  'utf-8')
    msg['Subject'] = subject
    msg['From'] = f"No Way Daily Bot <{sender_email}>"
    msg['To'] = receiver_email

    try:
        # Connect to Gmail SMTP (Change if using Outlook/Yahoo)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print("📧 Execution report email sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# -----------------------------
# STEP 1: CONTENT GENERATION
# -----------------------------
async def generate_content(topic):
    prompt = f""" 
        Analyze the topic: {topic}

        Provide the following in JSON format:
        1. headline: A short viral headline (max 12 words).
        2. main_topic: Identify the core subject/entity (1-3 words) from the headline to be highlighted.
        3. caption: Write a Facebook post in a story style. MUST use double line breaks (\\n\\n) between paragraphs for readability. 
        Format exactly like this structure:
        [Paragraph 1: Surprising insight or fact to hook readers]
        
        [Paragraph 2: Context or reasons behind it in 2-3 sentences]
        
        [Paragraph 3: Broader observation or implication]
        
        [Paragraph 4: Response, shift, or action being taken]
        
        [Paragraph 5: Short punchy takeaway sentence. 1-2 emojis max.]
        [Question to encourage comments]
        
        [Exactly 5 SEO-friendly hashtags]
        
        Do NOT invent fake statistics. If implying data, speak generally.
        4. image_prompt: A highly detailed, cinematic image generation prompt. Specify lighting (e.g., volumetric, dramatic, golden hour), camera style (e.g., 35mm lens, depth of field), and subject focus. The background MUST be described as "clean, dark, and uncluttered with negative space for text overlays." Do NOT include instructions to write words or text in the image.
        """

    try:
        res = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=PostContent)
        )
        data = json.loads(clean_json(res.text))
        return data["headline"].upper(), data["main_topic"].upper(), data["caption"], data["image_prompt"]
    except Exception as e: 
        print(f"❌ Content Gen Error: {e}")
        return "TECH NEWS ALERT", "TECH", "Discover the latest in tech! #Tech #News", "cinematic tech background"

# -----------------------------
# STEP 2: IMAGE GENERATION
# -----------------------------
async def generate_image(prompt, filename):
    model_id = "stabilityai/stable-diffusion-xl-base-1.0"
    try:
        image = await hf_client.text_to_image(prompt=prompt, model=model_id)
        image = image.resize((WIDTH, HEIGHT), Image.LANCZOS)
        image.save(filename)
        return filename
    except Exception as e:
        print(f"⚠️ HF Error: {e}. Using fallback.")
        Image.new('RGB', (WIDTH, HEIGHT), color=(40, 40, 40)).save(filename)
        return filename

# -----------------------------
# STEP 3: DRAWING THE UI
# -----------------------------
def apply_transformers_style(bg_path, headline, main_topic, output_path):
    img = Image.open(bg_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        watermark_font = ImageFont.truetype(FONT_PATH, 25)
    except:
        font = ImageFont.load_default()
        watermark_font = ImageFont.load_default()

    lines = textwrap.wrap(headline, width=22)
    line_height = FONT_SIZE + 15
    total_text_height = len(lines) * line_height
    bottom_padding = 80 
    current_y = HEIGHT - total_text_height - bottom_padding
    highlight_words = [w.strip(",.!?") for w in main_topic.split()]

    for line in lines:
        words = line.split(" ")
        current_x = 40 
        
        for word in words:
            clean_word = word.strip(",.!?").upper()
            bbox = draw.textbbox((0, 0), word + " ", font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

            if clean_word in highlight_words or main_topic in clean_word:
                draw.rectangle([current_x, current_y, current_x + w, current_y + line_height - 5], fill=YELLOW_HIGHLIGHT)
                draw.text((current_x, current_y), word + " ", font=font, fill=BAR_COLOR)
            else:
                draw.rectangle([current_x, current_y, current_x + w, current_y + line_height - 5], fill=BAR_COLOR)
                draw.text((current_x, current_y), word + " ", font=font, fill=TEXT_COLOR)
            
            current_x += w
        current_y += line_height

    watermark_text = "FOLLOW NO WAY DAILY"
    txt_img = Image.new('RGBA', img.size, (255, 255, 255, 0))
    txt_draw = ImageDraw.Draw(txt_img)
    wbbox = txt_draw.textbbox((0, 0), watermark_text, font=watermark_font)
    ww = wbbox[2] - wbbox[0]
    watermark_x = (WIDTH - ww) // 2 
    watermark_y = current_y + 10 
    
    txt_draw.text((watermark_x, watermark_y), watermark_text, font=watermark_font, fill=(255, 255, 255, 128))
    img = Image.alpha_composite(img, txt_img)
    img.convert("RGB").save(output_path, "PNG")

# -----------------------------
# STEP 4: ORCHESTRATION
# -----------------------------
def load_queue():
    if not os.path.exists('topics.json'):
        print("❌ Error: topics.json not found!")
        return []
    with open('topics.json', 'r') as f:
        return json.load(f)

def update_queue(queue):
    with open('topics.json', 'w') as f:
        json.dump(queue, f, indent=2)

async def create_post(topic, index, semaphore):
    async with semaphore:
        headline, main_topic, caption, img_prompt = await generate_content(topic)

        print("\n" + "="*50)
        print(f"📰 DRAFT CAPTION FOR: {topic}")
        print("="*50)
        print(caption)
        print("="*50 + "\n")
        
        bg_tmp = f"bg_{index}.jpg"
        await generate_image(img_prompt, bg_tmp)

        final_name = f"final_post_{index}.png"
        await asyncio.to_thread(apply_transformers_style, bg_tmp, headline, main_topic, final_name)
        
        if os.path.exists(bg_tmp): os.remove(bg_tmp)
        print(f"✅ Created Image: {final_name}")
        
        # Returns True if successful, False if failed
        is_success = await asyncio.to_thread(post_to_facebook, final_name, caption)
        return is_success

async def main():
    queue = load_queue()
    to_post = [item for item in queue if item.get('status') == 'approved'][:1]
    
    if not to_post:
        print("📭 No 'approved' topics found! Please approve more in topics.json.")
        send_email_report("failed", "No Approved Topics Found")
        return

    print(f"🚀 Found {len(to_post)} topics to post. Starting automation...")
    semaphore = asyncio.Semaphore(1)
    
    for i, target_item in enumerate(to_post):
        print(f"📸 Processing: {target_item['topic']}")
        
        try:
            # Process and capture success/fail
            post_success = await create_post(target_item['topic'], target_item['id'], semaphore)
            
            if post_success:
                target_item['status'] = 'posted'
                final_status = "success"
            else:
                final_status = "failed"
                
            # Update the JSON queue
            update_queue(queue)
            print("✅ topics.json updated.")
            
            # Send the final email with all the logs
            send_email_report(final_status, target_item['topic'])

        except Exception as e:
            print(f"❌ CRITICAL SCRIPT ERROR: {e}")
            send_email_report("failed", target_item['topic'])

if __name__ == "__main__":
    asyncio.run(main())