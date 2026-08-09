import os
import time
import random
import asyncio
import re
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

# 🎵 INSTAGRAM VIRAL PHONK MUSİQİLƏRİ (Direct CDN Links)
VIRAL_MUSIC_LIST = [
    {
        "name": "Aggressive Drift Phonk Trend",
        "url": "https://ia801503.us.archive.org/15/items/phonk-background-music/phonk1.mp3",
        "start": 10
    },
    {
        "name": "Cyber Phonk Beat",
        "url": "https://ia801503.us.archive.org/15/items/phonk-background-music/phonk2.mp3",
        "start": 15
    },
    {
        "name": "Rio Drift Funk",
        "url": "https://ia801503.us.archive.org/15/items/phonk-background-music/phonk3.mp3",
        "start": 12
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

# 2. PINTEREST VƏ İNGİLİS DİLİNDƏ ŞƏKİL AXTARIŞI
def fetch_pinterest_image_en(fact_text):
    print("AI mövzunun ingiliscə açar sözlərini hazırlayır...")
    try:
        kw_prompt = (
            "Extract ONLY 1-3 English keywords describing the main car or vehicle in this text for Pinterest search "
            "(e.g. 'Bugatti Chiron supercar', 'Traffic jam highway', 'Car engine detail'). "
            f"Do not write full sentences:\n{fact_text[:250]}"
        )
        kw_res = client.models.generate_content(model="gemini-2.0-flash", contents=kw_prompt)
        english_query = kw_res.text.strip().replace('"', '').replace("'", "").replace(".", "")
        print(f"🔍 Pinterest-də ingilis dilində axtarılır: '{english_query}'")

        # Pinterest Axtarışı
        pinterest_url = f"https://www.pinterest.com/search/pins/?q={requests.utils.quote(english_query)}"
        p_res = requests.get(pinterest_url, headers=HEADERS, timeout=10)
        if p_res.status_code == 200:
            matches = re.findall(r'https://i\.pinimg\.com/[0-9ax]+/([a-f0-9/]+\.(?:jpg|png|webp))', p_res.text)
            if matches:
                img_url = f"https://i.pinimg.com/736x/{random.choice(matches[:5])}"
                img_data = requests.get(img_url, headers=HEADERS, timeout=10)
                if img_data.status_code == 200 and len(img_data.content) > 10000:
                    with open("car_image.jpg", "wb") as f:
                        f.write(img_data.content)
                    print(f"✅ Pinterest-dən HD şəkil tapıldı: {img_url}")
                    return "car_image.jpg"
    except Exception as e:
        print(f"⚠️ Pinterest axtarış xətası: {e}")

    # Fallback: Wikipedia / Unsplash
    try:
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={requests.utils.quote(english_query)}&format=json"
        s_res = requests.get(wiki_url, headers=HEADERS, timeout=8).json()
        results = s_res.get("query", {}).get("search", [])
        if results:
            page_title = results[0]["title"]
            sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(page_title)}"
            p_res = requests.get(sum_url, headers=HEADERS, timeout=8).json()
            if "originalimage" in p_res:
                img_url = p_res["originalimage"]["source"]
                img_data = requests.get(img_url, headers=HEADERS, timeout=10)
                if img_data.status_code == 200:
                    with open("car_image.jpg", "wb") as f:
                        f.write(img_data.content)
                    print(f"✅ Wikipedia-dan foto yükləndi: {img_url}")
                    return "car_image.jpg"
    except Exception as e:
        print(f"Wikipedia xətası: {e}")

    # Ən son fallback HD şəkillər
    fallbacks = [
        "https://images.unsplash.com/photo-1617814076367-b759c7d7e738?q=80&w=1080",
        "https://images.unsplash.com/photo-1503376780353-7e6692767b70?q=80&w=1080",
        "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?q=80&w=1080"
    ]
    img_data = requests.get(random.choice(fallbacks), headers=HEADERS).content
    with open("car_image.jpg", "wb") as f:
        f.write(img_data)
    return "car_image.jpg"

# 3. YUXARI ŞƏKİL, AŞAĞI MƏTN DİZAYNI
def create_split_frame(text, img_path, width=1080, height=1920):
    canvas = Image.new('RGB', (width, height), (15, 23, 42))

    # Yuxarı Hissə (1080x1080 Şəkil)
    img_h = 1080
    try:
        top_img = Image.open(img_path).convert('RGB')
        top_img = ImageOps.fit(top_img, (width, img_h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        canvas.paste(top_img, (0, 0))
    except Exception as e:
        print("Şəkil işlənmədi:", e)

    draw = ImageDraw.Draw(canvas)
    
    # İki hissə arasında bəzək mavi xətti
    draw.line([(0, img_h), (width, img_h)], fill=(59, 130, 246), width=8)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
    except Exception:
        font = ImageFont.load_default()

    tts_text = text.split("#")[0].strip()
    words = tts_text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 28:
            lines.append(" ".join(current_line[:-1]))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    display_text = "\n".join(lines)

    bbox = draw.multiline_textbbox((0, 0), display_text, font=font, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    bottom_area_h = height - img_h
    text_x = (width - text_w) / 2
    text_y = img_h + (bottom_area_h - text_h) / 2

    # Yazını tam aşağı tünd fonun mərkəzinə yazmaq
    draw.multiline_text((text_x, text_y), display_text, fill=(255, 255, 255), font=font, align="center", spacing=15)

    return np.array(canvas)

# 4. INSTAGRAM VIRAL MAHNISINI MİKSLƏMƏK
def get_background_music(duration):
    tracks = VIRAL_MUSIC_LIST.copy()
    random.shuffle(tracks)
    for track in tracks:
        try:
            print(f"🎵 Viral mahnı yüklənir: {track['name']}...")
            res = requests.get(track["url"], headers=HEADERS, timeout=15)
            if res.status_code == 200 and len(res.content) > 30000:
                with open("bg_music.mp3", "wb") as f:
                    f.write(res.content)
                
                full_bg = AudioFileClip("bg_music.mp3")
                start_time = track.get("start", 0)
                if start_time + duration > full_bg.duration:
                    start_time = max(0, full_bg.duration - duration)
                    
                bg_audio = full_bg.subclip(start_time, start_time + duration)
                bg_audio = bg_audio.volumex(0.20)  # Mahnı səsi 20%
                print("✅ Viral mahnı uğurla arxa fona əlavə olundu!")
                return bg_audio
        except Exception as e:
            print(f"Musiqi yükləmə xətası ({track['name']}):", e)
    return None

def create_video(text):
    print("1. Azərbaycan dilində diktor səsi hazırlanır (edge-tts)...")
    asyncio.run(edge_tts.Communicate(text.split("#")[0].strip(), voice="az-AZ-BabekNeural").save("voice.mp3"))
    voice_audio = AudioFileClip("voice.mp3")
    duration = voice_audio.duration + 1.5

    print("2. Viral fon musiqisi yüklənir...")
    bg_audio = get_background_music(duration)
    
    if bg_audio:
        final_audio = CompositeAudioClip([voice_audio, bg_audio])
    else:
        final_audio = voice_audio

    print("3. Pinterest-dən İngilis dilində şəkil axtarılır və kadr hazırlanır...")
    img_path = fetch_pinterest_image_en(text)
    frame_array = create_split_frame(text, img_path)
    txt_clip = ImageClip(frame_array).set_duration(duration)

    print("4. Video render edilir...")
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

    create_video(caption)

    public_url = upload_to_tmp_host("reel.mp4")

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

