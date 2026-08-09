import os
import time
import random
import asyncio
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from google import genai
import edge_tts
from moviepy.editor import ColorClip, CompositeVideoClip, AudioFileClip, ImageClip

# 1. Environment dəyişənləri
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")

# 2. Google GenAI
client = genai.Client(api_key=GEMINI_API_KEY)

FALLBACK_FACTS = [
    "Bugatti Chiron mühərriki tam gücü ilə işləyərkən 100 litrlik yanacaq çənini cəmi 9 dəqiqəyə boşaldır! 🏎️ #bugatti #hypercar #supercar #azərbaycan",
    "Dünyada ilk yol hərəkəti işıqları 1868-ci ildə Londonda quraşdırılıb və qazla işləyirdi. 🚦 #avto #tarix #maraqli #baku",
    "Rolls-Royce avtomobillərinin salondakı saatı o qədər sakit işləyir ki, 100 km/saat sürətlə gedərkən eşidilən tək səs həmin saatın çıqqıltısı olur. 🚘 #rollsroyce #luxury #avtomobil #azerbaijan",
    "Dünyanın ən uzun tıxacı 2010-cu ildə Çində baş verib və tam 12 gün davam edib! Sürücülər gündə cəmi 1 km hərəkət edə bilirdilər. 🚗 #carfacts #maraqlifactlar #autolife #azərbaycan"
]

def generate_car_fact():
    prompt = (
        "Avtomobillər haqqında maraqlı, qısa və cəlb edici bir fakt yaz (Azərbaycan dilində). "
        "Mətn maksimum 2-3 cümlə olsun, Reels videosu üçün səsli oxunacaq. "
        "Sonda da 3-4 cəlbedici həştəq əlavə et."
    )
    candidate_models = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]
    for model_name in candidate_models:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            return response.text
        except Exception:
            continue
    return random.choice(FALLBACK_FACTS)

# 3. Video Yaratma
def create_text_image(text, width=1080, height=1920):
    img = Image.new('RGBA', (width, height), (15, 15, 20, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 46)
    except:
        font = ImageFont.load_default()
    
    tts_text = text.split("#")[0].strip()
    words = tts_text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 22:
            lines.append(" ".join(current_line[:-1]))
            current_line = [word]
    if current_line: lines.append(" ".join(current_line))
    display_text = "\n".join(lines)
    
    bbox = draw.multiline_textbbox((0, 0), display_text, font=font, align="center")
    draw.multiline_text(((width - (bbox[2]-bbox[0]))/2, (height - (bbox[3]-bbox[1]))/2), display_text, fill=(255, 255, 255, 255), font=font, align="center")
    return np.array(img)

def create_video(text):
    asyncio.run(edge_tts.Communicate(text.split("#")[0].strip(), voice="az-AZ-BabekNeural").save("voice.mp3"))
    audio = AudioFileClip("voice.mp3")
    txt_clip = ImageClip(create_text_image(text)).set_duration(audio.duration + 1)
    video = CompositeVideoClip([txt_clip]).set_audio(audio)
    video.write_videofile("reel.mp4", fps=24, codec="libx264", audio_codec="aac")
    audio.close(); video.close()

# 4. Yükləmə (İkiqat server)
def upload_to_tmp_host(file_path):
    with open(file_path, 'rb') as f:
        try:
            res = requests.post('https://tmpfiles.org/api/v1/upload', files={'file': f})
            if res.status_code == 200: return res.json()['data']['url'].replace("tmpfiles.org/", "tmpfiles.org/dl/")
        except: pass
    with open(file_path, 'rb') as f:
        res = requests.post('https://envs.sh', files={'file': f})
        return res.text.strip()

# 5. Instagram Paylaşım (Daha detallı loqlar ilə)
def post_to_instagram(video_url, caption):
    print(f"DEBUG: Yüklənən video URL: {video_url}")
    
    # 1. Konteyner yarat
    url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/media"
    payload = {"media_type": "REELS", "video_url": video_url, "caption": caption, "access_token": META_ACCESS_TOKEN}
    res = requests.post(url, data=payload).json()
    
    if "id" not in res:
        print("!!! XƏTA: Konteyner yaradılmadı. Cavab:", res)
        return
    
    creation_id = res["id"]
    print(f"DEBUG: Konteyner yaradıldı. ID: {creation_id}")

    # 2. Statusu yoxla
    status_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code,status_info&access_token={META_ACCESS_TOKEN}"
    for i in range(20):
        time.sleep(15)
        status_res = requests.get(status_url).json()
        print(f"DEBUG: Status yoxlaması {i+1}: {status_res}")
        
        if status_res.get("status_code") == "FINISHED": break
        if status_res.get("status_code") == "ERROR":
            print("!!! XƏTA: Facebook videonu rədd etdi!", status_res.get("status_info"))
            return

    # 3. Paylaş
    pub_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
    pub_res = requests.post(pub_url, data={"creation_id": creation_id, "access_token": META_ACCESS_TOKEN}).json()
    print("!!! YAKUN CAVAB (PAYLAŞIM):", pub_res)

if __name__ == "__main__":
    caption = generate_car_fact()
    create_video(caption)
    url = upload_to_tmp_host("reel.mp4")
    post_to_instagram(url, caption)

