import os
import time
import html
import requests

# Mengambil konfigurasi dari Environment Variables Railway
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

KEYWORDS = ["saham", "crypto", "bitcoin", "ihsg", "btc"]

def send_telegram_alert(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Variable TELEGRAM_TOKEN atau TELEGRAM_CHAT_ID belum diisi di Railway!")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload, timeout=30)
        print(f"Status Telegram: {res.status_code} | Respon: {res.text}")
    except Exception as e:
        print(f"ERROR TELEGRAM: {e}")

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
            "maxItems": 5,
            "sort": "Top"
        }
        
        try:
            response = requests.post(apify_url, json=payload, timeout=120)
            print(f"Status Apify [{keyword}]: {response.status_code}")
            
            if response.status_code in [200, 201]:
                items = response.json()
                print(f"Dapat {len(items)} item dari Apify untuk [{keyword}].")
                
                if isinstance(items, list) and len(items) > 0:
                    # Menampilkan nama field asli untuk debugging log
                    if isinstance(items[0], dict):
                        print(f"KEYS DATA APIFY [{keyword}]: {list(items[0].keys())}")
                    
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        
                        # Pengambilan teks dengan beberapa skenario fallback
                        text = item.get("text") or item.get("fullText") or item.get("full_text")
                        if not text and isinstance(item.get("tweet"), dict):
                            text = item.get("tweet", {}).get("text")
                            
                        url = item.get("url") or item.get("twitterUrl") or "https://x.com"

                        if not text:
                            text = f"Postingan terkait #{keyword}"

                        safe_text = html.escape(str(text))
                        msg = f"🔥 <b>Postingan Found!</b>\n\nKeyword: #{keyword}\n\n{safe_text}\n\n<a href='{url}'>Buka Postingan</a>"
                        
                        print(f"--> Mengirim postingan [{keyword}] ke Telegram...")
                        send_telegram_alert(msg)
            else:
                print(f"Apify Gagal [{keyword}]: {response.text}")
        except Exception as e:
            print(f"ERROR APIFY [{keyword}]: {e}")

if __name__ == "__main__":
    while True:
        check_social_media()
        print("Selesai cek. Tidur selama 4 jam...")
        time.sleep(14400)
