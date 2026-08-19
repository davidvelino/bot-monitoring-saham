import os
import time
import html
import requests

# Mengambil konfigurasi dari Environment Variables Railway
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

# Filter Kriteria Minimal
KEYWORDS = ["saham", "crypto", "bitcoin", "ihsg", "btc"]
MIN_VIEWS = 5000       # Minimal 5k views
MIN_FOLLOWERS = 10000   # Minimal 10k followers

def send_telegram_alert(caption, photo_url=None):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_TOKEN atau TELEGRAM_CHAT_ID belum diisi!")
        return

    if len(caption) > 1000:
        caption = caption[:995] + "..."

    # 1. Kirim Foto jika ada
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
                print("--> Telegram: Foto & Berita Terkirim (200)")
                return
        except Exception as e:
            print(f"Error kirim foto: {e}")

    # 2. Fallback Teks
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": caption, 
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        res = requests.post(url, json=payload, timeout=30)
        print(f"--> Telegram: Teks Terkirim ({res.status_code})")
    except Exception as e:
        print(f"ERROR TELEGRAM: {e}")

# ==================== 1. MODUL X (TWITTER) ====================
def fetch_twitter_news():
    print("--- Checking Twitter/X ---")
    apify_url = f"https://api.apify.com/v2/acts/apidojo~tweet-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"

    for keyword in KEYWORDS:
        payload = {"searchTerms": [keyword], "maxItems": 10, "sort": "Top"}
        try:
            res = requests.post(apify_url, json=payload, timeout=120)
            if res.status_code in [200, 201]:
                items = res.json()
                for item in items:
                    if not isinstance(item, dict) or item.get("noResults") is True:
                        continue
                    
                    author = item.get("author", {})
                    followers = author.get("followersCount") or author.get("followers_count") or 0
                    views = item.get("viewCount") or item.get("viewsCount") or item.get("impressionCount") or 0
                    
                    try:
                        followers = int(followers)
                        views = int(views)
                    except ValueError:
                        pass

                    # FILTER KETAT: Followers & Views
                    if followers < MIN_FOLLOWERS:
                        print(f"--> [SKIP X] Followers kurang ({followers} < {MIN_FOLLOWERS})")
                        continue
                    if views < MIN_VIEWS:
                        print(f"--> [SKIP X] Views kurang ({views} < {MIN_VIEWS})")
                        continue

                    text = item.get("fullText") or item.get("text") or item.get("full_text")
                    if not text:
                        continue
                        
                    images = item.get("images") or item.get("photos") or []
                    photo_url = images[0] if (isinstance(images, list) and len(images) > 0 and isinstance(images[0], str)) else None
                    tweet_url = item.get("url") or item.get("twitterUrl") or "https://x.com"
                    author_name = author.get("name") or author.get("userName") or "Twitter User"

                    caption = (
                        f"🌐 <b>BERITA AKURAT X (TWITTER)</b>\n"
                        f"🏷️ <b>Topic:</b> #{keyword}\n"
                        f"👤 <b>Sumber:</b> {html.escape(author_name)} ({followers:,} Followers)\n"
                        f"📊 <b>Views:</b> {views:,}\n\n"
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
        payload = {"hashtags": [keyword], "resultsLimit": 10}
        try:
            res = requests.post(apify_url, json=payload, timeout=120)
            if res.status_code in [200, 201]:
                items = res.json()
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    
                    followers = item.get("ownerFollowersCount") or item.get("owner", {}).get("followersCount") or 0
                    views = item.get("videoViewCount") or item.get("videoPlayCount") or item.get("likesCount") or 0
                    
                    try:
                        followers = int(followers)
                        views = int(views)
                    except ValueError:
                        pass

                    # FILTER KETAT: Followers & Views
                    if followers > 0 and followers < MIN_FOLLOWERS:
                        print(f"--> [SKIP IG] Followers kurang ({followers} < {MIN_FOLLOWERS})")
                        continue
                    if views < MIN_VIEWS:
                        print(f"--> [SKIP IG] Views/Interaksi kurang ({views} < {MIN_VIEWS})")
                        continue

                    caption_text = item.get("caption") or ""
                    photo_url = item.get("displayUrl") or item.get("display_url")
                    post_url = item.get("url") or f"https://www.instagram.com/p/{item.get('shortCode')}/"
                    owner = item.get("ownerUsername") or "Instagram User"

                    caption = (
                        f"📸 <b>BERITA AKURAT INSTAGRAM</b>\n"
                        f"🏷️ <b>Hashtag:</b> #{keyword}\n"
                        f"👤 <b>Akun:</b> @{html.escape(owner)} ({followers:,} Followers)\n"
                        f"📊 <b>Views/Likes:</b> {views:,}\n\n"
                        f"📝 <b>Deskripsi Berita:</b>\n{html.escape(caption_text if caption_text else 'Postingan Gambar Instagram')}\n\n"
                        f"🔗 <a href='{post_url}'>Buka di Instagram</a>"
                    )
                    send_telegram_alert(caption, photo_url=photo_url)
        except Exception as e:
            print(f"Error Instagram [{keyword}]: {e}")

# ==================== MAIN EXECUTION ====================
def check_social_media():
    print("Memulai pengecekan berita akurat (Min 10k Followers & 5k Views)...")
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
