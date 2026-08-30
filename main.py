import os
import time
import html
import requests
import feedparser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from newspaper import Article, Config
from deep_translator import GoogleTranslator
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

def force_translate_to_id(text):
    """Memaksa penerjemahan ke Bahasa Indonesia dengan potongan teks pendek"""
    if not text or len(text.strip()) == 0:
        return ""
    
    # Ambil maksimal 500 karakter agar Google Translator tidak memblokir
    short_text = text[:500]
    
    try:
        translator = GoogleTranslator(source='auto', target='id')
        translated = translator.translate(short_text)
        if translated and "Error" not in translated:
            return translated
    except Exception as e:
        print(f"Gagal Translate: {e}")
    
    return short_text

def make_bullet_summary(raw_text):
    """Mengambil 2-3 kalimat utama untuk diringkas"""
    if not raw_text:
        return ""

    paragraphs = [p.strip() for p in raw_text.split('\n') if len(p.strip()) > 50]
    if not paragraphs:
        return ""

    # Ambil 2 paragraf teratas saja
    selected = paragraphs[:2]
    bullets = []
    for p in selected:
        # Terjemahkan tiap paragraf secara terpisah
        translated_p = force_translate_to_id(p[:250])
        bullets.append(f"• {translated_p}")

    return "\n\n".join(bullets)

def send_to_channel(text, image_url=None):
    if not CHAT_ID or not TOKEN:
        print("Error: TELEGRAM_CHAT_ID atau TELEGRAM_TOKEN belum diatur!")
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
                return res.json()
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
        res = requests.post(url, data=payload, timeout=15)
        return res.json()
    except Exception as e:
        print(f"Gagal kirim ke Telegram: {e}")

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
            summary_id = "• " + force_translate_to_id(clean_html(rss_summary)[:300])

        return summary_id, top_image

    except Exception:
        fallback_text = clean_html(rss_summary)
        if fallback_text:
            return "• " + force_translate_to_id(fallback_text[:300]), None
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
                
                # Terjemahkan Judul
                title_id = force_translate_to_id(entry.title)
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

                send_to_channel(message, image_url)
                time.sleep(2)
        except Exception as e:
            print(f"Error pada {source_name}: {e}")

if __name__ == "__main__":
    threading.Thread(target=start_health_check_server, daemon=True).start()
    
    while True:
        check_news()
        print("Selesai cek. Menunggu 60 detik...")
        time.sleep(60)
