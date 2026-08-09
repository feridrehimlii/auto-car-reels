import os
import time
import random
import asyncio
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from google import genai
import edge_tts
from moviepy.editor import CompositeVideoClip, AudioFileClip, ImageClip, CompositeAudioClip

# 1. Environment Dəyişənləri
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 🎵 Playlistdəki Təhlükəsiz Və Uyğun Phonk Trekləri (Səs 30%, Dinamik Hissələr)
PLAYLIST = [
    {
        "name": "Clovis Reyes - Fluxxwave",
        "url": "https://cdn.pixabay.com/download/audio/2023/09/24/audio_34190c1f51.mp3",
        "start": 15
    },
    {
        "name": "NBSPLV - Lost Soul",
        "url": "https://cdn.pixabay.com/download/audio/2022/11/18/audio_83d379bd43.mp3",
        "start": 18
    },
    {
        "name": "Ariis - MANDA BALA",
        "url": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3",
        "start": 12
    },
    {
        "name": "xxanteria - BAIXO",
        "url": "https://cdn.pixabay.com/download/audio/2023/06/12/audio_13a1a15750.mp3",
        "start": 20
    }
]

FALLBACK_FACTS = [
    "Dünyanın ən uzun tıxacı 2010-cu ildə Çində baş verib və tam 12 gün davam edib! Peqin-Tibet magistralında yaranan bu nəhəng tıxacın uzunluğu 100 kilometrdən çox idi. Sürücülər gün ərzində cəmi 1 kilometr hərəkət edə bilirdilər. Yolda qalan insanlara ərzaq və su satmaq üçün yerli sakinlər xüsusi ticarət şəbəkəsi qurmuşdular. 🚗 #carfacts #maraqlifactlar #autolife #azərbaycan",
    "Bugatti Chiron mühərriki tam gücü ilə işləyərkən 100 litrlik yanacaq çənini cəmi 9 dəqiqəyə tamamilə boşaldır! Bu möhtəşəm 8.0 litrlik W16 mühərriki dəqiqədə 60 min litrdən çox hava sorur. Yanacaq nasosu isə dəqiqədə 15 litr benzin vurur. Bu inanılmaz göstəricilər hiperkarın niyə dünyanın ən sürətli avtomobillərindən biri olduğunu bir daha sübut edir. 🏎️ #bugatti #hypercar #supercar #azərbaycan"
]

def generate_car_fact():
    prompt = (
        "Avtomobillər haqqında çox maraqlı, detallı və diqqətçəkən bir fakt yaz (Azərbaycan dilində). "
        "Mətn kifayət qədər zəngin və uzun olsun ki, səsli oxunuşu təxminən 15-20 saniyə çəksin (təxminən 45-60 söz). "
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

def fetch_contextual_image(fact_text):
    print("AI mövzuya tam uyğun şəkil axtarır...")
    try:
        kw_prompt = f"Extract ONLY ONE main subject in English for a Wikipedia search based on this text (e.g. 'Traffic jam', 'Bugatti Chiron', 'Traffic light', 'Automobile engine'):\n{fact_text[:200]}"
        kw_res = client.models.generate_content(model="gemini-2.0-flash", contents=kw_prompt)
        topic = kw_res.text.strip().replace("\n", "").replace('"', '').replace("'", "")
        print(f"Axtarılan mövzu: '{topic}'")

        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}"
        res = requests.get(wiki_url, headers=HEADERS, timeout=8).json()
        
        if "originalimage" in res and "source" in res["originalimage"]:
            img_url = res["originalimage"]["source"]
            print(f"Wikipedia-dan foto tapıldı: {img_url}")
            return img_url
    except Exception as e:
        print(f"Şəkil axtarış xətası: {e}")

    return "https://images.unsplash.com/photo-1503376780353-7e6692767b70?q=80&w=1080"

def create_styled_frame(text, img_url, width=1080, height=1920):
    try:
        res = requests.get(img_url, headers=HEADERS, stream=True, timeout=10)
        img = Image.open(res.raw).convert('RGBA')
        img = ImageOps.fit(img, (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    except Exception as e:
        print("Şəkil yüklənmədi, tünd fon yaradılır:", e)
        img = Image.new('RGBA', (width, height), (15, 20, 30, 255))

    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 70))
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except Exception:
        font = ImageFont.load_default()

    tts_text = text.split("#")[0].strip()
    words = tts_text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 26:
            lines.append(" ".join(current_line[:-1]))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    display_text = "\n".join(lines)

    bbox = draw.multiline_textbbox((0, 0), display_text, font=font, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # BÜTÖV MAVİ FON (AŞAĞIDA SOLDAN SAĞA BÜTÖV)
    padding_y = 35
    banner_h = text_h + (padding_y * 2)
    
    banner_y2 = height - 120
    banner_y1 = banner_y2 - banner_h

    banner_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    banner_draw = ImageDraw.Draw(banner_layer)
    banner_draw.rectangle(
        [0, banner_y1, width, banner_y2],
        fill=(10, 50, 140, 230)
    )
    img = Image.alpha_composite(img, banner_layer)

    draw = ImageDraw.Draw(img)
    text_x = (width - text_w) / 2
    text_y = banner_y1 + padding_y

    draw.multiline_text((text_x, text_y), display_text, fill=(255, 255, 255, 255), font=font, align="center")

    return np.array(img.convert('RGB'))

def create_video(text):
    print("Mətn səsə çevrilir...")
    asyncio.run(edge_tts.Communicate(text.split("#")[0].strip(), voice="az-AZ-BabekNeural").save("voice.mp3"))
    voice_audio = AudioFileClip("voice.mp3")
    duration = voice_audio.duration + 1.5

    selected_track = random.choice(PLAYLIST)
    print(f"Seçilən mahnı: {selected_track['name']}")
    final_audio = voice_audio

    try:
        res = requests.get(selected_track["url"], headers=HEADERS, timeout=10)
        if res.status_code == 200 and len(res.content) > 10000:
            with open("bg_music.mp3", "wb") as f:
                f.write(res.content)
            
            full_bg = AudioFileClip("bg_music.mp3")
            start_time = selected_track.get("start", 0)
            
            if start_time + duration > full_bg.duration:
                start_time = max(0, full_bg.duration - duration)
                
            bg_audio = full_bg.subclip(start_time, start_time + duration)
            bg_audio = bg_audio.volumex(0.30)  # SƏS 30%
            final_audio = CompositeAudioClip([voice_audio, bg_audio])
    except Exception as e:
        print("Musiqi xətası:", e)

    img_url = fetch_contextual_image(text)
    frame_array = create_styled_frame(text, img_url)
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
    except Exception:
        pass

    try:
        with open(file_path, 'rb') as f:
            res = requests.post('https://envs.sh', files={'file': f}, headers=HEADERS)
            return res.text.strip()
    except Exception:
        return None

def post_to_instagram(video_url, caption):
    print(f"Instagram-a göndərilir...")
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
    print("1. Detallı fakt hazırlanır...")
    caption = generate_car_fact()
    print(f"Mətn:\n{caption}\n")

    print("2. Video hazırlanır...")
    create_video(caption)

    print("3. Serverə yüklənir...")
    public_url = upload_to_tmp_host("reel.mp4")

    print("4. Instagram-da paylaşılır...")
    try:
        if public_url:
            post_to_instagram(public_url, caption)
    except Exception as e:
        print("Instagram xətası:", e)

    if public_url:
        print("\n" + "="*60)
        print("📌 YAKUN VİDEO LİNKİ (Brauzerdə açıb baxın):")
        print(public_url)
        print("="*60 + "\n")
        
