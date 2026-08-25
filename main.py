import os
import time
import html
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

# DAFTAR RSS AKURAT & AKTIF 24/7
RSS_FEEDS = {
    # Crypto Real-time
    "Cointelegraph": "https://cointelegraph.com/rss",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Pintu News": "https://pintu.co.id/blog/feed",
    "Blockchain Media ID": "https://blockchainmedia.id/feed/",

    # Saham & Finansial Indonesia
    "CNBC Indonesia Market": "https://www.cnbcindonesia.com/market/rss",
    "CNBC Indonesia News": "https://www.cnbcindonesia.com/news/rss",
    "CNBC Indonesia Investment": "https://www.cnbcindonesia.com/investment/rss",
    "Bisnis.com Market": "https://market.bisnis.com/rss",
    "Kontan Investasi": "https://investasi.kontan.co.id/rss",
    "Detik Finance": "https://finance.detik.com/rss",

    # Global Market & Forex
    "CNBC World News": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrptogo&id=100727362",
    "MarketWatch Top Stories": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
    "Investing.com": "https://www.investing.com/rss/news.rss"
}

SENT_URLS_CACHE = set()

def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator="\n").strip()

def safe_translate(text):
    """Penerjemah ganda anti-error"""
    if not text or len(text.strip()) == 0:
        return ""
    chunk = text[:1000]
    
    # Coba Google Translator
    try:
        translated = GoogleTranslator(source='auto', target='id').translate(chunk)
        if "Error 500" not in translated and "Server Error" not in translated:
            return translated
    except Exception:
        pass

    # Fallback ke MyMemory
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

    # Amankan teks dari karakter khusus HTML agar Telegram tidak menolak pesan
    safe_source = html.escape(source)
    safe_title = html.escape(title)
    safe_summary = html.escape(summary_id)

    caption = (
        f"🚨 <b>BERITA TERBARU: {safe_source}</b> 🚨\n\n"
        f"📰 <b>{safe_title}</b>\n\n"
        f"📝 <b>Inti Sari Berita:</b>\n{safe_summary}\n\n"
        f"🔗 <a href='{original_url}'>Baca Selengkapnya di Sini</a>"
    )

    if len(caption) > 1000:
        caption = caption[:950] + f"...\n\n🔗 <a href='{original_url}'>Baca Selengkapnya di Sini</a>"

    try:
        # Percobaan 1: Kirim Foto + Teks
        if photo_url:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
            res = requests.post(url, json=payload, timeout=15)
            if res.status_code == 200:
                return

        # Percobaan 2: Fallback ke Teks Saja jika foto gagal/corrupt
        url_text = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload_text = {"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "HTML", "disable_web_page_preview": False}
        requests.post(url_text, json=payload_text, timeout=15)

    except Exception as e:
        print(f"Gagal kirim Telegram: {e}")

def process_and_translate_article(url, rss_summary):
    try:
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        config = Config()
        config.browser_user_agent = user_agent
        config.request_timeout = 8

        article = Article(url, config=config)
        article.download()
        article.parse()
        
        raw_text = article.text
        top_image = article.top_image

        if not raw_text or len(raw_text) < 100:
            raw_text = clean_html(rss_summary)

        summary_text = create_summary(raw_text)
        if not summary_text:
            summary_text = raw_text[:400] + "..." if raw_text else "Klik tautan di bawah untuk membaca langsung."

        return safe_translate(summary_text), top_image

    except Exception:
        fallback_text = clean_html(rss_summary)
        if fallback_text:
            return safe_translate(fallback_text[:400]), None
        return "Klik tautan di bawah untuk membaca langsung dari sumber resmi.", None

def initialize_cache():
    """Tandai berita lama saat bot baru menyala agar tidak dikirim ulang"""
    print("Memuat cache berita awal...")
    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                SENT_URLS_CACHE.add(entry.link)
        except Exception:
            pass
    print(f"Cache siap. {len(SENT_URLS_CACHE)} berita lama dilewati.")

def check_news():
    print("Memeriksa rilis berita terbaru...")

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                url = entry.link
                
                if url in SENT_URLS_CACHE:
                    continue

                # Catat ke cache sebelum diproses
                SENT_URLS_CACHE.add(url)

                print(f"--> [BERITA BARU] {source_name}: {entry.title[:30]}...")
                
                title_id = safe_translate(entry.title)
                rss_summary = entry.summary if 'summary' in entry else ""

                summary_id, image_url = process_and_translate_article(url, rss_summary)
                send_telegram_news(title_id, url, image_url, summary_id, source_name)
                
                time.sleep(2)
        except Exception as e:
            print(f"Error pada {source_name}: {e}")

if __name__ == "__main__":
    threading.Thread(target=start_health_check_server, daemon=True).start()
    
    initialize_cache()
    
    while True:
        check_news()
        print("Patroli selesai. Menunggu 60 detik...")
        time.sleep(60)
