import os
import time
import html
import requests
import feedparser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from newspaper import Article, Config
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# Server Mini Anti-Sleep untuk Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Active 24/7")

def start_health_check_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

def self_ping():
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    while True:
        time.sleep(300)
        if render_url:
            try:
                requests.get(render_url, timeout=10)
            except Exception:
                pass

CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TOKEN = os.getenv("TELEGRAM_TOKEN")

RSS_FEEDS = {
    # Crypto
    "Cointelegraph": "https://cointelegraph.com/rss",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Pintu News": "https://pintu.co.id/blog/feed",
    "Blockchain Media ID": "https://blockchainmedia.id/feed/",

    # Indonesia Finance
    "CNBC Indonesia Market": "https://www.cnbcindonesia.com/market/rss",
    "CNBC Indonesia News": "https://www.cnbcindonesia.com/news/rss",
    "CNBC Indonesia Investment": "https://www.cnbcindonesia.com/investment/rss",
    "Bisnis.com Market": "https://market.bisnis.com/rss",
    "Kontan Investasi": "https://investasi.kontan.co.id/rss",
    "Detik Finance": "https://finance.detik.com/rss",

    # Global Market
    "CNBC World News": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrptogo&id=100727362",
    "MarketWatch Top Stories": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
    "Investing.com": "https://www.investing.com/rss/news.rss"
}

SENT_URLS_CACHE = set()

def clean_html(raw_html):
    """Menghapus tag HTML dan merapikan spasi"""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ").strip()

def safe_translate(text):
    """Menterjemahkan teks ke Bahasa Indonesia menggunakan Deep Translator"""
    if not text or len(text.strip()) == 0:
        return ""
    
    # Potong maksimal 450 karakter agar aman dari pembatasan
    text_to_translate = text[:450].strip()
    
    try:
        translated = GoogleTranslator(source='auto', target='id').translate(text_to_translate)
        if translated:
            return translated
    except Exception as e:
        print(f"Gagal translate: {e}")
        
    return text_to_translate

def make_summary(text, fallback_title=""):
    """Membuat ringkasan padat 1-2 kalimat dalam Bahasa Indonesia"""
    clean_text = clean_html(text)
    
    if not clean_text or len(clean_text) < 15:
        clean_text = fallback_title

    words = clean_text.split()
    if len(words) > 35:
        short_text = " ".join(words[:35]) + "..."
    else:
        short_text = clean_text

    translated_summary = safe_translate(short_text)
    
    if not translated_summary:
        translated_summary = safe_translate(fallback_title)

    return f"• {translated_summary}"

def send_to_channel_only(text, image_url=None):
    if not CHAT_ID or not TOKEN:
        print("ERROR: CHAT_ID atau TOKEN belum diset di Environment Variables!")
        return

    # Kirim Foto jika tersedia
    if image_url:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        payload = {
            "chat_id": CHAT_ID,
            "photo": image_url,
            "caption": text,
            "parse_mode": "HTML"
        }
        try:
            res = requests.post(url, data=payload, timeout=15)
            if res.status_code == 200:
                return
        except Exception as e:
            print(f"Gagal kirim photo, fallback ke text: {e}")

    # Fallback Kirim Pesan Teks
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        requests.post(url, data=payload, timeout=15)
    except Exception as e:
        print(f"Gagal kirim pesan ke Channel: {e}")

def process_article(url, rss_summary, raw_title):
    top_image = None
    extracted_text = ""

    # 1. Coba Scraping Isi Artikel Web
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        config = Config()
        config.browser_user_agent = headers['User-Agent']
        config.request_timeout = 5

        article = Article(url, config=config)
        article.download()
        article.parse()
        extracted_text = article.text
        top_image = article.top_image
    except Exception:
        pass

    # 2. Jika Scraping Web Gagal/Kosong, Gunakan Ringkasan bawaan RSS Feed
    if not extracted_text or len(extracted_text.strip()) < 30:
        extracted_text = rss_summary

    # 3. Proses Ringkasan & Terjemahan
    summary_id = make_summary(extracted_text, fallback_title=raw_title)
    return summary_id, top_image

def check_news():
    print("Memeriksa rilis berita terbaru...")

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            # Ambil 2 berita teratas dari setiap portal
            for entry in feed.entries[:2]:
                url = entry.link
                
                if url in SENT_URLS_CACHE:
                    continue

                # Tandai URL agar tidak terkirim ganda
                SENT_URLS_CACHE.add(url)

                raw_title = entry.title
                print(f"--> [KIRIM KE CHANNEL] {source_name}: {raw_title[:30]}...")
                
                # Terjemahkan Judul
                title_id = safe_translate(raw_title)
                
                # Ambil deskripsi dari RSS
                rss_summary = ""
                if 'summary' in entry:
                    rss_summary = entry.summary
                elif 'description' in entry:
                    rss_summary = entry.description

                summary_id, image_url = process_article(url, rss_summary, raw_title)
                
                safe_source = html.escape(source_name)
                safe_title = html.escape(title_id if title_id else raw_title)
                safe_summary = html.escape(summary_id)

                message = (
                    f"🚨 <b>{safe_source}</b> 🚨\n\n"
                    f"📌 <b>{safe_title}</b>\n\n"
                    f"💡 <b>Ringkasan Berita:</b>\n{safe_summary}\n\n"
                    f"🔗 <a href='{url}'>Baca Artikel Selengkapnya</a>"
                )

                if len(message) > 1000:
                    message = message[:950] + f"...\n\n🔗 <a href='{url}'>Baca Artikel Selengkapnya</a>"

                send_to_channel_only(message, image_url)
                time.sleep(3) # Jeda antar pengiriman pesan
        except Exception as e:
            print(f"Error pada {source_name}: {e}")

if __name__ == "__main__":
    threading.Thread(target=start_health_check_server, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    
    # Tanpa initialize_cache() yang memblokir berita awal
    while True:
        check_news()
        print("Selesai cek. Menunggu 60 detik...")
        time.sleep(60)
