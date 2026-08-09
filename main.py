import os
import time
import random
import asyncio
import requests
from google import genai
import edge_tts
from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip

# 1. Environment dəyişənlərini oxu
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")

# 2. Yeni Google GenAI SDK tənzimləməsi
client = genai.Client(api_key=GEMINI_API_KEY)

# API limitdə olduqda istifadə olunacaq hazır ehtiyat faktlar
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
    
    candidate_models = ["gemini-2.0-flash", "gemini-1.5-flash"]
    
    for model_name in candidate_models:
        try:
            print(f"Sınanılan model: {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            print(f"Uğurlu model: {model_name}")
            return response.text
        except Exception as e:
            print(f"{model_name} xəta verdi: {e}")
            time.sleep(2)
            
    print("⚠️ Bütün AI modelləri limitdədir. Ehtiyat faktlardan biri istifadə olunur...")
    return random.choice(FALLBACK_FACTS)

# 3. Mətni səsə çevirmək (edge-tts)
async def create_audio(text, output_file="voice.mp3"):
    tts_text = text.split("#")[0].strip()
    communicate = edge_tts.Communicate(tts_text, voice="az-AZ-BabekNeural")
    await communicate.save(output_file)

# 4. Videonu keçici ictimai URL-ə yükləmək (Instagram API üçün lazımdır)
def upload_to_tmp_host(file_path):
    with open(file_path, 'rb') as f:
        response = requests.post('https://catbox.moe/user/api.php', data={'reqtype': 'fileupload'}, files={'fileToUpload': f})
    if response.status_code == 200:
        return response.text.strip()
    raise Exception("Fayl yüklənərkən xəta baş verdi: " + response.text)

# 5. Reels videosunu hazırlamaq
def create_video(text):
    asyncio.run(create_audio(text))
    
    audio_clip = AudioFileClip("voice.mp3")
    duration = audio_clip.duration + 1

    bg_clip = ColorClip(size=(1080, 1920), color=(15, 15, 20), duration=duration)
    
    tts_text = text.split("#")[0].strip()

    words = tts_text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 22:
            lines.append(" ".join(current_line[:-1]))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    display_text = "\n".join(lines)

    txt_clip = TextClip(
        display_text,
        fontsize=50,
        color='white',
        font='DejaVu-Sans-Bold',
        method='caption',
        size=(900, 1200)
    ).set_position('center').set_duration(duration)

    video = CompositeVideoClip([bg_clip, txt_clip]).set_audio(audio_clip)
    video.write_videofile("reel.mp4", fps=24, codec="libx264", audio_codec="aac")
    
    audio_clip.close()
    video.close()

# 6. Instagram-da avtomatik paylaşmaq
def post_to_instagram(video_url, caption):
    print("Instagram-da Media Container yaradılır...")
    url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": META_ACCESS_TOKEN
    }
    res = requests.post(url, data=payload).json()
    
    if "id" not in res:
        print("Xəta baş verdi:", res)
        return

    creation_id = res["id"]
    print(f"Container yaradıldı ID: {creation_id}. Video emal olunur...")

    status_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code&access_token={META_ACCESS_TOKEN}"
    for _ in range(20):
        time.sleep(10)
        status_res = requests.get(status_url).json()
        status = status_res.get("status_code")
        print("Status:", status)
        if status == "FINISHED":
            break
        elif status == "ERROR":
            print("Video emal edilərkən xəta yarandı.")
            return

    publish_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
    pub_res = requests.post(publish_url, data={"creation_id": creation_id, "access_token": META_ACCESS_TOKEN}).json()
    print("Paylaşım nəticəsi:", pub_res)

if __name__ == "__main__":
    print("1. Fakt hazırlanır...")
    caption = generate_car_fact()
    print(f"Mətn:\n{caption}\n")

    print("2. Video və səs yaradılır...")
    create_video(caption)

    print("3. Video serverə yüklənir...")
    public_url = upload_to_tmp_host("reel.mp4")
    print(f"Public Link: {public_url}")

    print("4. Instagram-a göndərilir...")
    post_to_instagram(public_url, caption)

