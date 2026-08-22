import os
import time
import requests
import feedparser
from newspaper import Article
from deep_translator import GoogleTranslator

# Konfigurasi Railway
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# DAFTAR RSS FEEDS RESMI DARI SITUS YANG DIMINTA
RSS_FEEDS = {
    "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
    "Investing.com": "https://www.investing.com/rss/news_25.rss",
    "CNBC World": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrptogo&id=100727362",
    "CME Group": "https://www.cmegroup.com/cme-group-news.rss",
    "SEC": "https://www.sec.gov/news/pressreleases.rss",
    "World Bank": "https://www.worldbank.org/en/news/all/rss",
    "IMF": "https://www.imf.org/en/News/RSS",
    "Investopedia": "https://www.investopedia.com/feedbuilder/feed/getfeed/?feedName=news",
    "Forex Factory": "https://www.forexfactory.com/news.xml", # Alternatif news
    "Bloomberg / General Macro": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml" # Fallback untuk WSJ/Macro karena Bloomberg memblokir RSS publik
}

# File untuk menyimpan berita yang sudah dikirim agar tidak double
HISTORY_FILE = "sent_news.txt"

def load_sent_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_to_history(url):
    with open(HISTORY_FILE, "a") as f:
        f.write(url + "\n")

def split_text(text, max_length=4000):
    """Membagi teks jika melebihi batas pesan Telegram"""
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

def send_to_telegram(title, original_url, photo_url, full_text_id, source):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Token Telegram belum diset!")
        return

    # Kirim Foto + Judul terlebih dahulu (Caption max 1024 karakter)
    caption = f"🚨 <b>BERITA TERBARU DARI {source}</b> 🚨\n\n<b>{title}</b>\n\n🔗 <a href='{original_url}'>Baca Asli di Web</a>"
    
    if photo_url:
        photo_req_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
        requests.post(photo_req_url, json=payload)
    else:
        text_req_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "HTML"}
        requests.post(text_req_url, json=payload)

    # Kirim Full Text Artikel yang sudah diterjemahkan sebagai pesan susulan
    if full_text_id:
        text_chunks = split_text(full_text_id)
        for chunk in text_chunks:
            msg_payload = {"chat_id": TELEGRAM_CHAT_ID, "text": chunk}
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json=msg_payload)
            time.sleep(1) # Hindari spam limit Telegram

def fetch_and_translate_article(url):
    """Menyedot isi artikel dan gambar asli, lalu menerjemahkan"""
    try:
        article = Article(url)
        article.download()
        article.parse()
        
        raw_text = article.text
        top_image = article.top_image

        if not raw_text:
            return "Teks artikel dikunci oleh sistem keamanan web.", top_image

        # Terjemahkan ke Bahasa Indonesia
        translator = GoogleTranslator(source='auto', target='id')
        
        # Batasi terjemahan jika artikel terlalu panjang (deep-translator limit ~5000 chars)
        if len(raw_text) > 4900:
            raw_text = raw_text[:4900] + "... [Artikel dipotong karena terlalu panjang]"
            
        translated_text = translator.translate(raw_text)
        return translated_text, top_image

    except Exception as e:
        print(f"Gagal scrape artikel {url}: {e}")
        return None, None

def check_news():
    print("Memeriksa berita terbaru dari sumber global...")
    sent_urls = load_sent_history()
    translator = GoogleTranslator(source='auto', target='id')

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            
            # Ambil 2 artikel terbaru dari masing-masing feed
            for entry in feed.entries[:2]:
                url = entry.link
                
                if url in sent_urls:
                    continue # Lewati jika sudah pernah dikirim
                
                print(f"--> Memproses berita baru dari {source_name}...")
                
                # Terjemahkan Judul
                raw_title = entry.title
                title_id = translator.translate(raw_title)

                # Sedot isi lengkap web dan gambarnya
                full_text_id, image_url = fetch_and_translate_article(url)
                
                # Kirim ke Telegram
                send_to_telegram(title_id, url, image_url, full_text_id, source_name)
                
                # Simpan ke histori agar tidak dikirim ulang
                save_to_history(url)
                sent_urls.add(url)
                
                time.sleep(3) # Jeda antar berita
                
        except Exception as e:
            print(f"Error membaca {source_name}: {e}")

if __name__ == "__main__":
    while True:
        check_news()
        print("Selesai putaran. Menunggu 60 detik agar IP tidak diblokir web...")
        time.sleep(60) # Interval 1 menit adalah batas paling aman agar tidak di-banned
