import os
import re
import random
import requests
from urllib.parse import quote
from gtts import gTTS
from PIL import Image
import numpy as np
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeAudioClip, 
    CompositeVideoClip, TextClip, afx
)

# ==========================================
# 1. INSTAGRAM VIRAL MAHNILAR SİYAHISI (Direct MP3)
# ==========================================
VIRAL_INSTAGRAM_MUSIC = {
    "1. Instagram Phonk Trend": "https://cdn.pixabay.com/download/audio/2023/11/19/audio_d1beec11ef.mp3",
    "2. Aesthetic Lo-Fi Viral": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3",
    "3. Cinematic Reel Trend": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73213.mp3",
    "4. Upbeat Energetic Trend": "https://cdn.pixabay.com/download/audio/2022/10/14/audio_9939f131cf.mp3"
}

# ==========================================
# 2. PINTEREST-DƏN İNGİLİS DİLİNDƏ ŞƏKİL TAPMAQ
# ==========================================
def fetch_pinterest_image_en(english_query):
    """
    Pinterest-də ingilis dili sorğusu ilə axtarış edir və HD şəkil linkini qaytarır.
    """
    print(f"🔍 Pinterest-də ingilis dilində axtarılır: '{english_query}'...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    encoded_query = quote(english_query)
    url = f"https://www.pinterest.com/search/pins/?q={encoded_query}&rs=typed"
    
    try:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            # Pinterest şəkil URL-lərini təsbit edən REGEX
            matches = re.findall(r'https://i\.pinimg\.com/[0-9ax]+/([a-f0-9/]+\.(?:jpg|png|webp))', response.text)
            if matches:
                # Ən böyük ölçü (736px) ilə şəkil linkini formalaşdırırıq
                selected_img_id = random.choice(matches[:5]) # İlk 5 nəticədən təsadüfi birini seçirik
                img_url = f"https://i.pinimg.com/736x/{selected_img_id}"
                
                # Şəkli endiririk
                img_res = requests.get(img_url, headers=headers, timeout=10)
                if img_res.status_code == 200:
                    with open("pinterest_bg.jpg", "wb") as f:
                        f.write(img_res.content)
                    print(f"✅ Pinterest şəkli uğurla endirildi: {img_url}")
                    return "pinterest_bg.jpg"
    except Exception as e:
        print(f"⚠️ Pinterest axtarışında xəta: {e}")
    
    # Ehtiyat mənbə (Əgər Pinterest bloklasa, eyni ingilis sözü ilə Unsplash HD istifadə edir)
    print("🔄 Pinterest ehtiyat mənbəyə keçdi (Unsplash HD)...")
    fallback_url = f"https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1080&h=1920&fit=crop"
    img_data = requests.get(fallback_url).content
    with open("pinterest_bg.jpg", "wb") as f:
        f.write(img_data)
    return "pinterest_bg.jpg"

# ==========================================
# 3. VIRAL İNSTAGRAM MAHNISINI ƏLAVƏ ETMEK
# ==========================================
def download_viral_music(music_choice_key=None):
    """
    Instagram viral mahnısını endirir və yoxlayır.
    """
    if not music_choice_key or music_choice_key not in VIRAL_INSTAGRAM_MUSIC:
        music_choice_key = random.choice(list(VIRAL_INSTAGRAM_MUSIC.keys()))
    
    music_url = VIRAL_INSTAGRAM_MUSIC[music_choice_key]
    print(f"🎵 Seçilən Instagram Viral Mahnı: {music_choice_key}")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(music_url, headers=headers, stream=True)
    with open("bg_viral_music.mp3", "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
            
    print("✅ Viral mahnı hazırlandı.")
    return "bg_viral_music.mp3"

# ==========================================
# 4. REELS / SHORTS VİDEOSUNU HAZIRLAMAQ
# ==========================================
def create_instagram_reel(az_text, english_search_query, music_key=None):
    """
    Mətni, ingilis dilində Pinterest şəklini və Instagram viral mahnısını birləşdirir.
    """
    print("\n🚀 Video hazırlanması başladı...")
    
    # 1. DİKATOR SƏSİ (gTTS Azərbaycan dili)
    tts = gTTS(text=az_text, lang='az')
    tts.save("voiceover.mp3")
    voice_audio = AudioFileClip("voiceover.mp3")
    duration = voice_audio.duration + 0.8  # Bir az əlavə vaxt
    
    # 2. PINTEREST ŞƏKİLİ (İngilis dilində axtarış)
    img_path = fetch_pinterest_image_en(english_search_query)
    
    # Şəkli 1080x1920 (Vertical Reels/TikTok) formatına gətirmək
    img = Image.open(img_path).convert("RGB")
    img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
    img.save("processed_bg.jpg")
    
    bg_clip = ImageClip("processed_bg.jpg").set_duration(duration)
    
    # Zoom Effect (Hərəkətli Fon)
    bg_clip = bg_clip.resize(lambda t: 1 + 0.04 * t)
    
    # 3. İNSTAGRAM VIRAL FON MAHNISI QARIŞDIRILMASI
    music_file = download_viral_music(music_key)
    bg_music = AudioFileClip(music_file)
    
    # Əgər mahnı qısadırsa dövr etdirsin (loop)
    if bg_music.duration < duration:
        bg_music = afx.audio_loop(bg_music, duration=duration)
    
    # Fond musiqisini kəsirik və səsini 18%-ə endiririk (Diktor aydın olsun deyə)
    bg_music = bg_music.subclip(0, duration).volumex(0.18)
    
    # Səsləri birləşdiririk (Diktor səs + Viral Musiqi)
    final_audio = CompositeAudioClip([voice_audio, bg_music])
    
    # 4. VİDEO YIĞILMASI
    video = CompositeVideoClip([bg_clip]).set_duration(duration)
    video = video.set_audio(final_audio)
    
    output_filename = "instagram_viral_reel.mp4"
    video.write_videofile(
        output_filename, 
        fps=30, 
        codec='libx264', 
        audio_codec='aac',
        preset='fast'
    )
    
    # Təmizlik
    voice_audio.close()
    bg_music.close()
    video.close()
    print(f"\n🎉 VİDEO HAZIRDIR: {output_filename}")

# ==========================================
# 5. İŞƏ SALMAQ VƏ TEST EDƏRƏK YOXALMAQ
# ==========================================
if __name__ == "__main__":
    # Nümunə Azərbaycan dilində Fakt
    AZERBAIJANI_FACT = (
        "Bilirdinizmi? Şəki Xan Sarayının tikintisində heç bir mismardan və ya yapışqandan "
        "istifadə olunmayıb. Sarayın şəbəkə pəncərələri minlərlə xırda taxta və şüşə hissədən ibarətdir."
    )
    
    # Pinterest üçün xüsusi İNGİLİS dilində axtarış sözü:
    PINTEREST_ENGLISH_QUERY = "Sheki Khan Palace Azerbaijan aesthetic photography wallpaper"
    
    # İstədiyiniz viral mahnını seçə bilərsiniz:
    # "1. Instagram Phonk Trend", "2. Aesthetic Lo-Fi Viral", "3. Cinematic Reel Trend", "4. Upbeat Energetic Trend"
    SELECTED_VIRAL_MUSIC = "1. Instagram Phonk Trend"
    
    create_instagram_reel(
        az_text=AZERBAIJANI_FACT,
        english_search_query=PINTEREST_ENGLISH_QUERY,
        music_key=SELECTED_VIRAL_MUSIC
    )

