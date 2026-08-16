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
        requests.post(url, json=payload)
    except Exception as e:
    print(f"ERROR APIFY: {e}")

def check_social_media():
    print("Memulai pengecekan postingan viral...")
    
    # Memanggil Apify Scraper untuk mencari postingan X / Instagram
    # Menggunakan Actor populer Apify: apify/tweet-scraper
    apify_url = f"https://api.apify.com/v2/acts/apify~tweet-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    
    for keyword in KEYWORDS:
        payload = {
            "searchTerms": [keyword],
            "maxItems": 10
        }
        try:
            response = requests.post(apify_url, json=payload, timeout=60)
            if response.status_code == 201 or response.status_code == 200:
                items = response.json()
                for item in items:
                    views = item.get("viewCount", 0) or item.get("views", 0)
                    url = item.get("url", "")
                    text = item.get("text", "")[:150]
                    
                    if views >= MIN_VIEWS:
                        msg = (
                            f"🚀 <b>POSTINGAN VIRAL TERDETEKSI!</b>\n\n"
                            f"📌 <b>Topik:</b> {keyword}\n"
                            f"👁 <b>Views:</b> {views:,}\n"
                            f"📝 <b>Teks:</b> {text}...\n\n"
                            f"🔗 <b>Link:</b> {url}"
                        )
                        send_telegram_alert(msg)
        except Exception as e:
            print(f"Error saat mengecek keyword {keyword}: {e}")

def main():
    send_telegram_alert("🤖 Bot Monitoring Saham & Crypto Aktif 24/7!")
    while True:
        check_social_media()
        print("Selesai cek. Tidur selama 4 jam...")
        # 4 jam = 4 * 60 * 60 = 14400 detik
        time.sleep(14400)

if __name__ == "__main__":
    main()
