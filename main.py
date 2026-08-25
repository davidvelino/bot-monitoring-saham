import os
import time
import requests
import feedparser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from newspaper import Article, Config
from deep_translator import GoogleTranslator, MyMemoryTranslator
from bs4 import BeautifulSoup

# Server Mini untuk Health Check Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot News Telegram Running Successfully!")

def start_health_check_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Sumber RSS Sangat Aktif & Super Cepat (Lokal & Global)
RSS_FEEDS = {
    # Crypto Real-time
    "Cointelegraph": "https://cointelegraph.com/rss",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Pintu News": "https://pintu.co.id/blog/feed",
    "Blockchain Media ID": "https://blockchainmedia.id/feed/",

    # Indonesia Finance & Stock (Update hitungan menit)
    "CNBC Indonesia Market": "https://www.cnbcindonesia.com/market/rss",
    "CNBC Indonesia News": "https://www.cnbcindonesia.com/news/rss",
    "CNBC Indonesia Investment": "https://www.cnbcindonesia.com/investment/rss",
    "Detik Finance": "https://finance.detik.com/rss",
    "Bisnis.com Market": "https://market.bisnis.com/rss",
    "Kontan Investasi": "https://investasi.kontan.co.id/rss",
    "Google News Saham & Ekonomi": "https://news.google.com/rss/search?q=saham+IHSG+kripto&hl=id&gl=ID&ceid=ID:id",

    # Global Market & Forex (Cepat Update)
    "CNBC World News": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrptogo&id=100727362",
    "MarketWatch Top Stories": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
    "Investing.com News": "https://www.investing.com/rss/news.rss"
}

SENT_URLS_CACHE = set()

def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator="\n").strip()

def safe_translate(text):
    if not text or len(text.strip()) == 0:
        return ""
    chunk = text[:1000]
    try:
        translated = GoogleTranslator(source='auto', target='id').translate(chunk)
        if "Error 500" not in translated and "Server Error" not in translated:
            return translated
    except Exception:
        pass

    try:
        translated = MyMemoryTranslator(source='auto', target='id').translate(chunk)
        if translated and "MYMEMORY WARNING" not in translated:
            return translated
    except Exception:
        pass

    return chunk

def create_summary(raw_text):
    if not raw_text:
        return ""
    paragraphs = [p.strip() for p in raw_text.split('\n') if len(p.strip()) > 80]
    return "\n\n".join(paragraphs[:3])

def send_telegram_news(title, original_url, photo_url, summary_id, source):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Token Telegram belum diset!")
        return

    caption = (
        f"🚨 <b>BERITA TERBARU: {source}</b> 🚨\n\n"
        f"📰 <b>{title}</b>\n\n"
        f"📝 <b>Inti Sari Berita:</b>\n{summary_id}\n\n"
        f"🔗 <a href='{original_url}'>Baca Selengkapnya di Sini</a>"
    )

    if len(caption) > 1000:
        caption = caption[:950] + f"...\n\n🔗 <a href='{original_url}'>Baca Selengkapnya di Sini</a>"

    try:
        if photo_url:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
            res = requests.post(url, json=payload, timeout=20)
            if res.status_code != 200:
                url_text = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                payload_text = {"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "HTML"}
                requests.post(url_text, json=payload_text, timeout=20)
        else:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "HTML"}
            requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"Gagal kirim Telegram: {e}")

def process_and_translate_article(url, rss_summary):
    try:
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        config = Config()
        config.browser_user_agent = user_agent
        config.request_timeout = 10

        article = Article(url, config=config)
        article.download()
        article.parse()
        
        raw_text = article.text
        top_image = article.top_image

        if not raw_text or len(raw_text) < 100:
            raw_text = clean_html(rss_summary)
            if not raw_text:
                raw_text = "Klik link di bawah untuk membaca langsung dari sumber asli."

        summary_text = create_summary(raw_text)
        if not summary_text:
            summary_text = raw_text[:500] + "..."

        return safe_translate(summary_text), top_image

    except Exception as e:
        print(f"Error scrape {url}: {e}")
        fallback_text = clean_html(rss_summary)
        if fallback_text:
            return safe_translate(fallback_text[:500]), None
        return "Klik link di bawah untuk membaca langsung dari sumber asli.", None

def initialize_cache():
    """Mengunci semua berita yang ADA SEKARANG di RSS agar tidak dikirim ulang saat bot restart"""
    print("Inisialisasi cache... Memblokir berita lama...")
    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                SENT_URLS_CACHE.add(entry.link)
        except Exception as e:
            print(f"Inisialisasi gagal untuk {source_name}: {e}")
    print(f"Inisialisasi selesai! {len(SENT_URLS_CACHE)} berita lama berhasil dilewati.")

def check_news():
    print("Memeriksa rilis berita baru...")

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                url = entry.link
                
                # Cek jika sudah pernah dicatat/dikirim
                if url in SENT_URLS_CACHE:
                    continue

                print(f"--> [BERITA BENAR-BENAR BARU] {source_name} | {entry.title[:30]}...")
                
                # Masukkan ke cache DULUAN agar tidak dikirim ganda
                SENT_URLS_CACHE.add(url)

                title_id = safe_translate(entry.title)
                rss_summary = entry.summary if 'summary' in entry else ""

                summary_id, image_url = process_and_translate_article(url, rss_summary)
                send_telegram_news(title_id, url, image_url, summary_id, source_name)
                
                time.sleep(2)
        except Exception as e:
            print(f"Error {source_name}: {e}")

if __name__ == "__main__":
    threading.Thread(target=start_health_check_server, daemon=True).start()
    
    # 1. Bersihkan berita lama saat start
    initialize_cache()
    
    # 2. Pantau berita baru secara real-time
    while True:
        check_news()
        print("Selesai patroli. Menunggu 60 detik...")
        time.sleep(60)
