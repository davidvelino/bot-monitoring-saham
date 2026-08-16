import os
import time
import requests

# Mengambil konfigurasi dari Environment Variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

# Kata kunci yang dipantau
KEYWORDS = ["saham", "crypto", "bitcoin", "ihsg", "btc"]
MIN_VIEWS = 5000  # Trigger 5k views

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

    apify_url = f"https://api.apify.com/v2/acts/apify~tweet-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"

    for keyword in KEYWORDS:
        print(f"Mencetak keyword: {keyword}")
        payload = {
            "searchTerms": [keyword],
            "maxItems": 10
        }
        try:
            response = requests.post(apify_url, json=payload, timeout=60)
            print(f"Status Apify [{keyword}]: {response.status_code}")
            
            if response.status_code in [200, 201]:
                items = response.json()
                print(f"Dapat {len(items)} postingan dari Apify.")
                for item in items:
                    views = item.get("viewCount", 0) or item.get("views", 0)
                    if views >= MIN_VIEWS:
                        text = item.get("text", "")
                        url = item.get("url", "")
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
