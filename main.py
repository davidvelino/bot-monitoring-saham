import os
import time
import requests

# Mengambil konfigurasi dari Environment Variables Railway
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

# Kata kunci yang dipantau
KEYWORDS = ["saham", "crypto", "bitcoin", "ihsg", "btc"]
MIN_VIEWS = 100  # Trigger minimal 100 views (bisa dinaikkan lagi nanti)

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload)
        print(f"Status kirim Telegram: {res.status_code}")
    except Exception as e:
        print(f"ERROR TELEGRAM: {e}")

def check_social_media():
    print("Memulai pengecekan postingan viral...")
    
    if not APIFY_TOKEN:
        print("ERROR: APIFY_TOKEN tidak ditemukan di Variables Railway!")
        return

    # Menggunakan Actor Apify yang aktif: apidojo~tweet-scraper
    apify_url = f"https://api.apify.com/v2/acts/apidojo~tweet-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"

    for keyword in KEYWORDS:
        print(f"Mencetak keyword: {keyword}")
        payload = {
            "searchQueries": [keyword],
            "maxItems": 10
        }
        try:
            response = requests.post(apify_url, json=payload, timeout=120)
            print(f"Status Apify [{keyword}]: {response.status_code}")
            
            if response.status_code in [200, 201]:
                items = response.json()
                print(f"Dapat {len(items)} postingan dari Apify.")
                for item in items:
                    # Memeriksa beberapa kemungkinan nama field views dari Apify
                    views = (
                        item.get("viewCount") 
                        or item.get("viewsCount") 
                        or item.get("views") 
                        or item.get("impressionCount") 
                        or 0
                    )
                    text = item.get("text") or item.get("fullText") or ""
                    url = item.get("url") or item.get("twitterUrl") or ""

                    print(f"--> Views terbaca: {views} | Teks: {text[:30]}...")

                    if views >= MIN_VIEWS:
                        msg = f"🔥 <b>Postingan Viral Found ({views} views)!</b>\n\n{text}\n\n<a href='{url}'>Buka Postingan</a>"
                        send_telegram_alert(msg)
            else:
                print(f"Apify Gagal: {response.text}")
        except Exception as e:
            print(f"ERROR SAAT MEMANGGIL APIFY [{keyword}]: {e}")

if __name__ == "__main__":
    while True:
        check_social_media()
        print("Selesai cek. Tidur selama 4 jam...")
        time.sleep(14400)
