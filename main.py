import os
import time
import html
import requests
import feedparser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from newspaper import Article, Config
from bs4 import BeautifulSoup

# 1. SERVER MINI AGAR RENDER TIDAK SLEEP/MATI
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

# CONFIG TELEGRAM
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
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator="\n").strip()

def translate_to_indonesian(text):
    """Penerjemah Menggunakan API Google Translate Langsung (Tanpa Library Rentan Block)"""
    if not text or len(text.strip()) == 0:
        return ""
    
    # Potong teks maks 400 karakter agar tidak gagal
    text_to_translate = text[:400]
    
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": "id",
        "dt": "t",
        "q": text_to_translate
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            result = response.json()
            translated_text = "".join([sentence[0] for sentence in result[0] if sentence[0]])
            return translated_text
    except Exception as e:
        print(f"Gagal translate: {e}")
        
    return text_to_translate

def make_bullet_summary(raw_text):
    """Membuat ringkasan 2 poin bahasa Indonesia"""
    if not raw_text:
        return ""

    paragraphs = [p.strip() for p in raw_text.split('\n') if len(p.strip()) > 50]
    if not paragraphs:
        return ""

    selected = paragraphs[:2]
    bullets = []
    for p in selected:
        translated_p = translate_to_indonesian(p[:200])
        bullets.append(f"• {translated_p}")

    return "\n\n".join(bullets)

def send_to_channel_only(text, image_url=None):
    if not CHAT_ID or not TOKEN:
        print("ERROR: TELEGRAM_CHAT_ID atau TELEGRAM_TOKEN belum diset!")
        return

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
        except Exception:
            pass

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
        print(f"Gagal kirim ke Channel: {e}")

def process_article(url, rss_summary):
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

        summary_id = make_bullet_summary(raw_text)
        if not summary_id:
            summary_id = "• " + translate_to_indonesian(clean_html(rss_summary)[:250])

        return summary_id, top_image

    except Exception:
        fallback_text = clean_html(rss_summary)
        if fallback_text:
            return "• " + translate_to_indonesian(fallback_text[:250]), None
        return "• Klik tautan di bawah untuk membaca langsung dari sumber resmi.", None

def check_news():
    print("Memeriksa rilis berita terbaru...")

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:
                url = entry.link
                
                if url in SENT_URLS_CACHE:
                    continue

                SENT_URLS_CACHE.add(url)

                print(f"--> [KIRIM KE CHANNEL] {source_name}: {entry.title[:30]}...")
                
                # Terjemahkan Judul Ke Bahasa Indonesia
                title_id = translate_to_indonesian(entry.title)
                rss_summary = entry.summary if 'summary' in entry else ""

                summary_id, image_url = process_article(url, rss_summary)
                
                safe_source = html.escape(source_name)
                safe_title = html.escape(title_id)
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
                time.sleep(2)
        except Exception as e:
            print(f"Error pada {source_name}: {e}")

if __name__ == "__main__":
    threading.Thread(target=start_health_check_server, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    
    # Tanpa initialize_cache() agar berita langsung masuk sekarang untuk tes
    while True:
        check_news()
        print("Selesai cek. Menunggu 120 detik...")
        time.sleep(120)
