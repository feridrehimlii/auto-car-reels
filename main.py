import os
import time
import random
import asyncio
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from google import genai
import edge_tts
from moviepy.editor import CompositeVideoClip, AudioFileClip, ImageClip, CompositeAudioClip

# 1. Environment dəyişənləri
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

# Yüksək keyfiyyətli avtomobil şəkilləri
CAR_IMAGES = [
    "https://images.unsplash.com/photo-1617814076367-b759c7d7e738?q=80&w=1080&auto=format&fit=crop", # Porsche
    "https://images.unsplash.com/photo-1503376780353-7e6692767b70?q=80&w=1080&auto=format&fit=crop", # Supercar
    "https://images.unsplash.com/photo-1544829099-b9a0c07fad1a?q=80&w=1080&auto=format&fit=crop", # BMW
    "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?q=80&w=1080&auto=format&fit=crop", # Mercedes
    "https://images.unsplash.com/photo-1603584173870-7f23fdae1b7a?q=80&w=1080&auto=format&fit=crop"  # Audi
]

# Doğrudan yüklənə bilən arxa fon musiqisi keçidi
BG_MUSIC_URL = "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

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

def create_styled_frame(text, width=1080, height=1920):
    img_url = random.choice(CAR_IMAGES)
    try:
        res = requests.get(img_url, headers=HEADERS, timeout=10)
        img = Image.open(requests.get(img_url, headers=HEADERS, stream=True).raw).convert('RGBA')
        img = img.resize((width, height))
    except Exception:
        img = Image.new('RGBA', (width, height), (20, 20, 30, 255))

    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 160))
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    except Exception:
        font = ImageFont.load_default()

    tts_text = text.split("#")[0].strip()
    words = tts_text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 20:
            lines.append(" ".join(current_line[:-1]))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    display_text = "\n".join(lines)

    bbox = draw.multiline_textbbox((0, 0), display_text, font=font, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    x = (width - text_w) / 2
    y = (height - text_h) / 2

    draw.multiline_text((x+3, y+3), display_text, fill=(0, 0, 0, 255), font=font, align="center")
    draw.multiline_text((x, y), display_text, fill=(255, 255, 255, 255), font=font, align="center")

    return np.array(img.convert('RGB'))

def create_video(text):
    print("Mətn səsə çevrilir...")
    asyncio.run(edge_tts.Communicate(text.split("#")[0].strip(), voice="az-AZ-BabekNeural").save("voice.mp3"))
    voice_audio = AudioFileClip("voice.mp3")
    duration = voice_audio.duration + 1.5

    # Musiqini təhlükəsiz yükləmək
    final_audio = voice_audio
    try:
        print("Arxa fon musiqisi yüklənir...")
        res = requests.get(BG_MUSIC_URL, headers=HEADERS, timeout=10)
        if res.status_code == 200 and len(res.content) > 10000:
            with open("bg_music.mp3", "wb") as f:
                f.write(res.content)
            
            bg_audio = AudioFileClip("bg_music.mp3").subclip(0, duration)
            bg_audio = bg_audio.volumex(0.15)
            final_audio = CompositeAudioClip([voice_audio, bg_audio])
            print("Musiqi uğurla əlavə edildi!")
        else:
            print("⚠️ Musiqi faylı tam yüklənmədi, yalnız diktor səsi istifadə olunur.")
    except Exception as e:
        print(f"⚠️ Musiqi yüklənərkən xəta yarandı ({e}), yalnız diktor səsi ilə davam edilir.")

    frame_array = create_styled_frame(text)
    txt_clip = ImageClip(frame_array).set_duration(duration)

    video = CompositeVideoClip([txt_clip]).set_audio(final_audio)
    video.write_videofile("reel.mp4", fps=24, codec="libx264", audio_codec="aac")

    voice_audio.close()
    video.close()

def upload_to_tmp_host(file_path):
    print("Video serverə yüklənir...")
    try:
        with open(file_path, 'rb') as f:
            res = requests.post('https://tmpfiles.org/api/v1/upload', files={'file': f}, headers=HEADERS)
            if res.status_code == 200:
                return res.json()['data']['url'].replace("tmpfiles.org/", "tmpfiles.org/dl/")
    except Exception as e:
        print("tmpfiles xətası:", e)

    with open(file_path, 'rb') as f:
        res = requests.post('https://envs.sh', files={'file': f}, headers=HEADERS)
        return res.text.strip()

def post_to_instagram(video_url, caption):
    print(f"Instagram-a göndərilir: {video_url}")
    url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/media"
    payload = {"media_type": "REELS", "video_url": video_url, "caption": caption, "access_token": META_ACCESS_TOKEN}
    res = requests.post(url, data=payload).json()
    
    if "id" not in res:
        print("!!! XƏTA: Konteyner yaradılmadı:", res)
        return

    creation_id = res["id"]
    print(f"Container ID: {creation_id}. Emal olunur...")

    status_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code,status_info&access_token={META_ACCESS_TOKEN}"
    for i in range(20):
        time.sleep(12)
        status_res = requests.get(status_url).json()
        print(f"Status yoxlaması {i+1}: {status_res}")
        if status_res.get("status_code") == "FINISHED": break
        if status_res.get("status_code") == "ERROR":
            print("!!! XƏTA: Video rədd edildi!", status_res.get("status_info"))
            return

    pub_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
    pub_res = requests.post(pub_url, data={"creation_id": creation_id, "access_token": META_ACCESS_TOKEN}).json()
    print("!!! YAKUN CAVAB (PAYLAŞIM):", pub_res)

if __name__ == "__main__":
    print("1. Fakt seçilir...")
    caption = generate_car_fact()
    print(f"Mətn:\n{caption}\n")

    print("2. Şəkilli və Musiqili Video yaradılır...")
    create_video(caption)

    print("3. Yüklənir...")
    public_url = upload_to_tmp_host("reel.mp4")

    print("4. Paylaşılır...")
    post_to_instagram(public_url, caption)

