import os
import time
import requests

# Mengambil konfigurasi dari Environment Variables Railway
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

# Kata kunci yang dipantau
KEYWORDS = ["saham", "crypto", "bitcoin", "ihsg", "btc"]
MIN_VIEWS = 100  # Trigger minimal 100 views

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload)
        print(f"Status kirim Telegram: {res.status_code}")
    except Exception as e:
        print(f"ERROR TELEGRAM: {e}")

def extract_views(item):
    """Mencari views secara pintar dari angka, string, maupun objek berlapis"""
    if not isinstance(item, dict):
        return 0
    
    # 1. Cari key yang mengandung kata 'view' atau 'impression'
    for key, val in item.items():
        key_lower = str(key).lower()
        if "view" in key_lower or "impression" in key_lower:
            if isinstance(val, (int, float)) and val > 0:
                return int(val)
            if isinstance(val, str) and val.isdigit():
                return int(val)
            if isinstance(val, dict):
                for sub_val in val.values():
                    if isinstance(sub_val, (int, float)) and sub_val > 0:
                        return int(sub_val)
                    if isinstance(sub_val, str) and sub_val.isdigit():
                        return int(sub_val)

    # 2. Periksa objek berlapis seperti metrics/legacy/stats
    for nested_key in ["metrics", "legacy", "stats", "public_metrics"]:
        nested = item.get(nested_key)
        if isinstance(nested, dict):
            res = extract_views(nested)
            if res > 0:
                return res

    return 0

def check_social_media():
    print("Memulai pengecekan postingan viral...")
    
    if not APIFY_TOKEN:
        print("ERROR: APIFY_TOKEN tidak ditemukan di Variables Railway!")
        return

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
                
                if items and isinstance(items, list) and isinstance(items[0], dict):
                    # Menampilkan struktur kunci data pertama untuk debugging
                    print(f"DEBUG - Sample Keys Tweet: {list(items[0].keys())}")

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    
                    views = extract_views(item)
                    text = item.get("text") or item.get("fullText") or item.get("full_text") or ""
                    url = item.get("url") or item.get("twitterUrl") or item.get("tweetUrl") or ""

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
