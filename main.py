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

def get_tweet_text(item):
    """Mencari teks tweet di berbagai kemungkinan lokasi kunci JSON"""
    if not isinstance(item, dict):
        return ""
    
    # 1. Cek kunci langsung
    for key in ["text", "fullText", "full_text", "caption", "body", "content"]:
        val = item.get(key)
        if val and isinstance(val, str):
            return val
            
    # 2. Cek jika terbungkus di dalam objek berlapis (tweet / legacy / data)
    for sub in ["tweet", "legacy", "data"]:
        nested = item.get(sub)
        if isinstance(nested, dict):
            res = get_tweet_text(nested)
            if res:
                return res
                
    return ""

def get_tweet_url(item):
    if not isinstance(item, dict):
        return "https://x.com"
    
    for key in ["url", "twitterUrl", "tweetUrl", "canonicalUrl"]:
        val = item.get(key)
        if val and isinstance(val, str):
            return val
            
    return "https://x.com"

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
                    
                    # Abaikan jika ini hanya indikator tidak ada hasil
                    if item.get("noResults") is True:
                        continue
                    
                    text = get_tweet_text(item)
                    url = get_tweet_url(item)
                    
                    if not text:
                        print(f"--> [DEBUG] Item tanpa teks. Key yang ada: {list(item.keys())[:8]}")
                        continue
                        
                    valid_count += 1
                    safe_text = html.escape(text)

                    print(f"--> MENGIRIM TWEET [{keyword}]: {text[:30]}...")

                    msg = f"🔥 <b>Postingan Viral Found!</b>\n\nKeyword: #{keyword}\n\n{safe_text}\n\n<a href='{url}'>Buka Postingan</a>"
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
