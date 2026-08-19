import os
import time
import html
import requests

# Mengambil konfigurasi dari Environment Variables Railway
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

# Kata kunci & Hashtag yang dipantau
KEYWORDS = ["saham", "crypto", "bitcoin", "ihsg", "btc"]

def send_telegram_alert(caption, photo_url=None):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_TOKEN atau TELEGRAM_CHAT_ID belum diisi di Railway!")
        return

    # Batasi panjang caption Telegram agar tidak melebihi limit 1024 karakter
    if len(caption) > 1000:
        caption = caption[:995] + "..."

    # 1. Coba kirimkan sebagai Foto jika URL gambar tersedia
    if photo_url:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "HTML"
        }
        try:
            res = requests.post(url, json=payload, timeout=30)
            if res.status_code == 200:
                print("Status Telegram: 200 (Foto Berhasil Terkirim)")
                return
            else:
                print(f"Gagal kirim foto ({res.status_code}), beralih ke pesan teks...")
        except Exception as e:
            print(f"Error kirim foto: {e}")

    # 2. Fallback kirim sebagai Pesan Teks Biasa
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": caption, 
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        res = requests.post(url, json=payload, timeout=30)
        print(f"Status Telegram: {res.status_code} | Respon: {res.text}")
    except Exception as e:
        print(f"ERROR TELEGRAM: {e}")

# ==================== 1. MODUL X (TWITTER) ====================
def extract_twitter_media(item):
    if not isinstance(item, dict):
        return None
    images = item.get("images") or item.get("photos") or []
    if isinstance(images, list) and len(images) > 0:
        first = images[0]
        return first if isinstance(first, str) else first.get("url")
    return None

def fetch_twitter_news():
    print("--- Checking Twitter/X ---")
    apify_url = f"https://api.apify.com/v2/acts/apidojo~tweet-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"

    for keyword in KEYWORDS:
        payload = {"searchTerms": [keyword], "maxItems": 3, "sort": "Top"}
        try:
            res = requests.post(apify_url, json=payload, timeout=120)
            if res.status_code in [200, 201]:
                items = res.json()
                for item in items:
                    if not isinstance(item, dict) or item.get("noResults") is True:
                        continue
                    
                    text = item.get("fullText") or item.get("text") or item.get("full_text")
                    if not text:
                        continue
                        
                    photo_url = extract_twitter_media(item)
                    tweet_url = item.get("url") or item.get("twitterUrl") or "https://x.com"
                    author = item.get("author", {}).get("name") or "Twitter User"
                    likes = item.get("likeCount") or item.get("likes") or 0

                    caption = (
                        f"🌐 <b>BERITA / POSTINGAN X (TWITTER)</b>\n"
                        f"🏷️ <b>Topic:</b> #{keyword}\n"
                        f"👤 <b>Sumber:</b> {html.escape(author)}\n"
                        f"❤️ <b>Likes:</b> {likes}\n\n"
                        f"📝 <b>Deskripsi:</b>\n{html.escape(text)}\n\n"
                        f"🔗 <a href='{tweet_url}'>Buka Postingan Asli</a>"
                    )
                    send_telegram_alert(caption, photo_url=photo_url)
        except Exception as e:
            print(f"Error Twitter [{keyword}]: {e}")

# ==================== 2. MODUL INSTAGRAM ====================
def fetch_instagram_news():
    print("--- Checking Instagram ---")
    apify_url = f"https://api.apify.com/v2/acts/apify~instagram-hashtag-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"

    for keyword in KEYWORDS:
        payload = {
            "hashtags": [keyword],
            "resultsLimit": 3
        }
        try:
            res = requests.post(apify_url, json=payload, timeout=120)
            if res.status_code in [200, 201]:
                items = res.json()
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    
                    caption_text = item.get("caption") or ""
                    photo_url = item.get("displayUrl") or item.get("display_url")
                    post_url = item.get("url") or f"https://www.instagram.com/p/{item.get('shortCode')}/"
                    owner = item.get("ownerUsername") or "Instagram User"
                    likes = item.get("likesCount") or 0

                    if not caption_text and not photo_url:
                        continue

                    caption = (
                        f"📸 <b>BERITA / POSTINGAN INSTAGRAM</b>\n"
                        f"🏷️ <b>Hashtag:</b> #{keyword}\n"
                        f"👤 <b>Akun:</b> @{html.escape(owner)}\n"
                        f"❤️ <b>Likes:</b> {likes}\n\n"
                        f"📝 <b>Deskripsi Berita:</b>\n{html.escape(caption_text if caption_text else 'Postingan Gambar Instagram')}\n\n"
                        f"🔗 <a href='{post_url}'>Buka di Instagram</a>"
                    )
                    send_telegram_alert(caption, photo_url=photo_url)
        except Exception as e:
            print(f"Error Instagram [{keyword}]: {e}")

# ==================== MAIN EXECUTION ====================
def check_social_media():
    print("Memulai pengecekan berita saham & crypto di X dan Instagram...")
    if not APIFY_TOKEN:
        print("ERROR: APIFY_TOKEN tidak ditemukan!")
        return

    fetch_twitter_news()
    fetch_instagram_news()

if __name__ == "__main__":
    while True:
        check_social_media()
        print("Selesai cek. Tidur selama 4 jam...")
        time.sleep(14400)
