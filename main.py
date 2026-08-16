import os
import time
import requests

# Mengambil konfigurasi dari Environment Variables Railway
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

# Kata kunci yang dipantau
KEYWORDS = ["saham", "crypto", "bitcoin", "ihsg", "btc"]
MIN_VIEWS = 100  # Trigger minimal views / likes

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload)
        print(f"Status kirim Telegram: {res.status_code}")
    except Exception as e:
        print(f"ERROR TELEGRAM: {e}")

def extract_metrics(item):
    """Mengekstrak views dan likes"""
    if not isinstance(item, dict):
        return 0, 0

    views = 0
    for key in ["viewCount", "viewsCount", "view_count", "views", "impressionCount"]:
        val = item.get(key)
        if val is not None and isinstance(val, (int, float)) and val > 0:
            views = int(val)
            break
        elif isinstance(val, str) and val.isdigit():
            views = int(val)
            break

    likes = item.get("likeCount") or item.get("likes") or item.get("favorite_count") or 0
    try:
        likes = int(likes)
    except Exception:
        likes = 0

    return views, likes

def check_social_media():
    print("Memulai pengecekan postingan viral...")
    
    if not APIFY_TOKEN:
        print("ERROR: APIFY_TOKEN tidak ditemukan di Variables Railway!")
        return

    apify_url = f"https://api.apify.com/v2/acts/apidojo~tweet-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"

    for keyword in KEYWORDS:
        print(f"Mencetak keyword: {keyword}")
        
        payload = {
            "searchTerms": [keyword],
            "maxItems": 10,
            "sort": "Top"
        }
        
        try:
            response = requests.post(apify_url, json=payload, timeout=120)
            print(f"Status Apify [{keyword}]: {response.status_code}")
            
            if response.status_code in [200, 201]:
                items = response.json()
                print(f"Dapat {len(items)} item dari Apify untuk [{keyword}].")
                
                valid_count = 0
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    
                    # Hanya lewati jika nilai 'noResults' bernilai True secara eksplisit
                    if item.get("noResults") is True:
                        continue
                    
                    text = item.get("text") or item.get("fullText") or item.get("full_text") or ""
                    url = item.get("url") or item.get("twitterUrl") or item.get("tweetUrl") or ""
                    
                    if not text:
                        continue
                        
                    valid_count += 1
                    views, likes = extract_metrics(item)

                    print(f"--> Postingan Found [{keyword}] | Views: {views} | Likes: {likes} | Teks: {text[:30]}...")

                    metric_text = f"{views} views" if views > 0 else f"{likes} likes"
                    msg = f"🔥 <b>Postingan Viral Found ({metric_text})!</b>\n\nKeyword: #{keyword}\n\n{text}\n\n<a href='{url}'>Buka Postingan</a>"
                    send_telegram_alert(msg)
                    
                if valid_count == 0:
                    print(f"--> Apify: Tidak ada postingan valid untuk '{keyword}'")
            else:
                print(f"Apify Gagal [{keyword}]: {response.text}")
        except Exception as e:
            print(f"ERROR SAAT MEMANGGIL APIFY [{keyword}]: {e}")

if __name__ == "__main__":
    while True:
        check_social_media()
        print("Selesai cek. Tidur selama 4 jam...")
        time.sleep(14400)
