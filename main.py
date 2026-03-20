# import os
# import io
# import json
# import textwrap
# import asyncio
# from PIL import Image, ImageDraw, ImageFont
# from fontTools.ttLib import TTFont
# from dotenv import load_dotenv
# from pydantic import BaseModel

# # ✅ Modern SDK Imports
# from huggingface_hub import AsyncInferenceClient
# from google import genai
# from google.genai import types

# # -----------------------------
# # SETUP & CONFIG
# # -----------------------------
# load_dotenv()

# # Clients
# client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# hf_client = AsyncInferenceClient(token=os.getenv("HF_TOKEN"))

# WIDTH = 1024
# HEIGHT = 1024
# FONT_PATH = "Montserrat-Bold.ttf" 
# FONT_SIZE = 65  # Large, bold impact

# # Colors based on your reference image
# YELLOW_HIGHLIGHT = (255, 215, 0) # The "Transformers" yellow
# TEXT_COLOR = (255, 255, 255)
# BAR_COLOR = (0, 0, 0) # Pure black bars

# class TopicList(BaseModel):
#     topics: list[str]

# class PostContent(BaseModel):
#     headline: str
#     highlights: list[str]
#     image_prompt: str

# # -----------------------------
# # HELPERS
# # -----------------------------
# def clean_json(text):
#     start = text.find('{')
#     end = text.rfind('}')
#     return text[start:end+1] if start != -1 else "{}"

# # -----------------------------
# # STEP 1: CONTENT GENERATION
# # -----------------------------
# async def generate_topics(num=1):
#     prompt = f"Generate {num} viral movie or tech news facts. Max 8 words."
#     try:
#         res = await client.aio.models.generate_content(
#             model="gemini-2.5-flash",
#             contents=prompt,
#             config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=TopicList)
#         )
#         data = json.loads(clean_json(res.text))
#         return data.get("topics", ["Transformers 8 is coming back"])
#     except: return ["Transformers 8 is coming back"]

# async def generate_content(topic):
#     prompt = f"Create a viral headline and image prompt for: {topic}. Provide 2-3 keywords to highlight."
#     try:
#         res = await client.aio.models.generate_content(
#             model="gemini-2.5-flash",
#             contents=prompt,
#             config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=PostContent)
#         )
#         data = json.loads(clean_json(res.text))
#         return data["headline"].upper(), [h.upper() for h in data["highlights"]], data["image_prompt"]
#     except: return "NEWS ALERT", [], "cinematic movie poster"

# # -----------------------------
# # STEP 2: IMAGE GENERATION (FREE HF)
# # -----------------------------
# async def generate_image(prompt, filename):
#     model_id = "stabilityai/stable-diffusion-xl-base-1.0"
#     try:
#         image = await hf_client.text_to_image(prompt=prompt, model=model_id)
#         image = image.resize((WIDTH, HEIGHT), Image.LANCZOS)
#         image.save(filename)
#         return filename
#     except Exception as e:
#         print(f"⚠️ HF Error: {e}. Using fallback grey.")
#         img = Image.new('RGB', (WIDTH, HEIGHT), color=(40, 40, 40))
#         img.save(filename)
#         return filename

# # -----------------------------
# # STEP 3: DRAWING THE UI (THE TRANSFORMERS STYLE)
# # -----------------------------
# def apply_transformers_style(bg_path, headline, highlights, output_path):
#     img = Image.open(bg_path).convert("RGBA")
#     draw = ImageDraw.Draw(img)
    
#     try:
#         font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
#     except:
#         font = ImageFont.load_default()

#     # Wrap text to fit width
#     lines = textwrap.wrap(headline, width=22)
    
#     # Calculate starting Y (bottom of image)
#     line_height = FONT_SIZE + 15
#     total_text_height = len(lines) * line_height
#     current_y = HEIGHT - total_text_height - 60 # 60px padding from bottom

#     for line in lines:
#         words = line.split(" ")
#         current_x = 40 # Left margin
        
#         for word in words:
#             clean_word = word.strip(",.!?").upper()
#             bbox = draw.textbbox((0, 0), word + " ", font=font)
#             w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

#             # If word is a highlight, draw the yellow bar behind it
#             if clean_word in highlights or "TRANSFORMERS" in clean_word:
#                 draw.rectangle([current_x, current_y, current_x + w, current_y + line_height - 5], fill=YELLOW_HIGHLIGHT)
#                 draw.text((current_x, current_y), word + " ", font=font, fill=BAR_COLOR)
#             else:
#                 # Draw black bar for normal text
#                 draw.rectangle([current_x, current_y, current_x + w, current_y + line_height - 5], fill=BAR_COLOR)
#                 draw.text((current_x, current_y), word + " ", font=font, fill=TEXT_COLOR)
            
#             current_x += w
        
#         current_y += line_height

#     img.convert("RGB").save(output_path, "PNG")

# # -----------------------------
# # STEP 4: ORCHESTRATION
# # -----------------------------
# async def create_post(topic, index, semaphore):
#     async with semaphore:
#         headline, highlights, img_prompt = await generate_content(topic)
        
#         bg_tmp = f"bg_{index}.jpg"
#         await generate_image(img_prompt, bg_tmp)

#         final_name = f"final_post_{index}.png"
#         # Run image manipulation in a separate thread
#         await asyncio.to_thread(apply_transformers_style, bg_tmp, headline, highlights, final_name)
        
#         if os.path.exists(bg_tmp): os.remove(bg_tmp)
#         print(f"✅ Created: {final_name}")

# async def main():
#     topics = await generate_topics(3)
#     semaphore = asyncio.Semaphore(1)
#     tasks = [create_post(t, i+1, semaphore) for i, t in enumerate(topics)]
#     await asyncio.gather(*tasks)

# if __name__ == "__main__":
#     asyncio.run(main())













import os
import io
import json
import textwrap
import asyncio
import requests
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from dotenv import load_dotenv
from pydantic import BaseModel

# ✅ Modern SDK Imports
from huggingface_hub import AsyncInferenceClient
from google import genai
from google.genai import types

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
        return

    url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
    
    with open(image_path, 'rb') as f:
        payload = {'message': caption, 'access_token': token}
        files = {'source': f}
        res = requests.post(url, data=payload, files=files)
        
    if res.status_code == 200:
        print(f"✅ Facebook post successful! Post ID: {res.json().get('id')}")
    else:
        print(f"❌ Facebook post failed: {res.text}")

# -----------------------------
# STEP 1: CONTENT GENERATION
# -----------------------------
async def generate_topics(num=1):
    # prompt = f"Generate {num} viral geopolitical news facts. Max 8 words."

    prompt = f"""
                Generate {num} geopolitical topics suitable for Facebook content.

                RULES:
                - Max 8 words per topic
                - Clear and specific (no vague phrases)
                - No fake stats or claims
                - Must be widely known or plausible current issues

                STYLE:
                - Attention-grabbing but factual
                - Designed for social media posts

                OUTPUT:
                Plain list only (no numbering, no explanation)
                """
    try:
        res = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=TopicList)
        )
        return json.loads(clean_json(res.text)).get("topics", ["The first computer bug was a real moth"])
    except: 
        return ["The first computer bug was a real moth"]

async def generate_content(topic):
    # prompt = f"""
    # Analyze the topic: {topic}

    # Provide the following:
    # 1. headline: A short viral headline (max 12 words).
    # 2. main_topic: Identify the core subject/entity (1-3 words) from the headline to be highlighted.
    # 3. caption: Write a Facebook post in a story style.
    #    - Start with a surprising insight or fact to hook readers.
    #    - Explain the context or reasons behind it in 2-3 sentences.
    #    - Include a broader observation or implication to give meaning.
    #    - End with a short, punchy takeaway sentence.
    #    - Conclude with a question or call-to-action to encourage comments.
    #    - Keep sentences short and readable for social media.
    #    - Use 1-2 emojis to add emphasis or tone.
    #    - Include exactly 5 SEO-friendly hashtags relevant to the topic.
    # 4. image_prompt: A cinematic image generation prompt.
    # """

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
        print(f"Content Gen Error: {e}")
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
# STEP 3: DRAWING THE UI (UPDATED WITH WATERMARK)
# -----------------------------
def apply_transformers_style(bg_path, headline, main_topic, output_path):
    img = Image.open(bg_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        # ✅ NEW: Define a smaller, bold font for the watermark
        watermark_font_size = 25 
        watermark_font = ImageFont.truetype(FONT_PATH, watermark_font_size)
    except:
        font = ImageFont.load_default()
        watermark_font = ImageFont.load_default()

    # Wrap text to fit width
    lines = textwrap.wrap(headline, width=22)
    
    # Calculate starting Y (bottom of image)
    line_height = FONT_SIZE + 15
    total_text_height = len(lines) * line_height
    
    # ✅ ADJUSTED: Increase bottom padding slightly to fit the watermark below
    bottom_padding = 80 
    current_y = HEIGHT - total_text_height - bottom_padding

    # Extract individual words from the main topic for accurate matching
    highlight_words = [w.strip(",.!?") for w in main_topic.split()]

    for line in lines:
        words = line.split(" ")
        current_x = 40 # Left margin
        
        for word in words:
            clean_word = word.strip(",.!?").upper()
            bbox = draw.textbbox((0, 0), word + " ", font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

            # Highlight logic
            if clean_word in highlight_words or main_topic in clean_word:
                draw.rectangle([current_x, current_y, current_x + w, current_y + line_height - 5], fill=YELLOW_HIGHLIGHT)
                draw.text((current_x, current_y), word + " ", font=font, fill=BAR_COLOR)
            else:
                draw.rectangle([current_x, current_y, current_x + w, current_y + line_height - 5], fill=BAR_COLOR)
                draw.text((current_x, current_y), word + " ", font=font, fill=TEXT_COLOR)
            
            current_x += w
        current_y += line_height

    # ✅ NEW: Add Centered Watermark below the text block
    watermark_text = "FOLLOW BFACTS"
    # Create a new image for the watermark text to handle opacity separately
    txt_img = Image.new('RGBA', img.size, (255, 255, 255, 0))
    txt_draw = ImageDraw.Draw(txt_img)
    
    # Calculate centering
    wbbox = txt_draw.textbbox((0, 0), watermark_text, font=watermark_font)
    ww = wbbox[2] - wbbox[0]
    watermark_x = (WIDTH - ww) // 2 # Center horizontally
    
    # Position it below the text block (current_y is now at the bottom of the headlines)
    watermark_y = current_y + 10 
    
    # Draw text with 50% opacity (alpha = 128)
    txt_draw.text((watermark_x, watermark_y), watermark_text, font=watermark_font, fill=(255, 255, 255, 128))
    
    # Composite the watermark layer onto the main image
    img = Image.alpha_composite(img, txt_img)

    img.convert("RGB").save(output_path, "PNG")


# -----------------------------
# STEP 4: ORCHESTRATION
# -----------------------------
async def create_post(topic, index, semaphore):
    async with semaphore:
        headline, main_topic, caption, img_prompt = await generate_content(topic)

        # 🔍 ADD THIS: Print the generated caption to your terminal for review
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
        
        # Post to Facebook
        # await asyncio.to_thread(post_to_facebook, final_name, caption)

async def main():
    topics = await generate_topics(1)
    semaphore = asyncio.Semaphore(1)
    tasks = [create_post(t, i+1, semaphore) for i, t in enumerate(topics)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())