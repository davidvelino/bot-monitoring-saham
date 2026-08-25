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

RSS_FEEDS = {
    # Makro Ekonomi & Global
    "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
    "Investing.com": "https://www.investing.com/rss/news_25.rss",
    "FRED St. Louis Fed": "https://fredblog.stlouisfed.org/feed/",
    "CME Group": "https://www.cmegroup.com/cme-group-news.rss",
    "SEC": "https://www.sec.gov/news/pressreleases.rss",
    "World Bank": "https://www.worldbank.org/en/news/all/rss",
    "IMF": "https://www.imf.org/en/News/RSS",
    "BLS (Labor Statistics)": "https://www.bls.gov/feed/bls_latest.rss",
    
    # Forex & Market
    "BabyPips": "https://www.babypips.com/feed",
    "Forex Factory": "https://www.forexfactory.com/news.xml",
    "Bloomberg / WSJ": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
    "CNBC World": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrptogo&id=100727362",
    "Investopedia": "https://www.investopedia.com/feedbuilder/feed/getfeed/?feedName=news",

    # Saham Indonesia
    "CNBC Indonesia": "https://www.cnbcindonesia.com/market/rss",
    "Bisnis.com Market": "https://market.bisnis.com/rss",
    "Kontan Investasi": "https://investasi.kontan.co.id/rss",

    # Crypto
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Blockchain Media": "https://blockchainmedia.id/feed/",
    "Cryptowave": "https://cryptowave.co.id/feed/",
    "Pintu News": "https://pintu.co.id/blog/feed"
}

HISTORY_FILE = "sent_news.txt"

def load_sent_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_to_history(url):
    with open(HISTORY_FILE, "a") as f:
        f.write(url + "\n")

def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator="\n").strip()

def safe_translate(text):
    """Sistem Penerjemah Ganda: Google -> MyMemory -> Teks Asli"""
    if not text or len(text.strip()) == 0:
        return ""
    
    chunk = text[:1000] # Potong agar tidak melebihi batasan API

    # Opsi 1: Coba Google Translator
    try:
        translated = GoogleTranslator(source='auto', target='id').translate(chunk)
        if "Error 500" not in translated and "Server Error" not in translated and "Please try again" not in translated:
            return translated
    except Exception as e:
        print(f"Google Translate gagal: {e}")

    # Opsi 2: Coba MyMemory Translator (Lebih stabil di server cloud)
    try:
        translated = MyMemoryTranslator(source='auto', target='id').translate(chunk)
        if translated and "MYMEMORY WARNING" not in translated:
            return translated
    except Exception as e:
        print(f"MyMemory Translate gagal: {e}")

    # Opsi 3: Tampilkan teks asli jika semua penerjemah gagal
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
        config.request_timeout = 15

        article = Article(url, config=config)
        article.download()
        article.parse()
        
        raw_text = article.text
        top_image = article.top_image

        if not raw_text or len(raw_text) < 100:
            raw_text = clean_html(rss_summary)
            if not raw_text:
                raw_text = "Berita dikunci oleh sekuriti web. Klik link untuk membaca langsung."

        summary_text = create_summary(raw_text)
        if not summary_text:
            summary_text = raw_text[:500] + "..."

        return safe_translate(summary_text), top_image

    except Exception as e:
        print(f"Error scrape {url}: {e}")
        fallback_text = clean_html(rss_summary)
        if fallback_text:
            return safe_translate(fallback_text[:500]), None
        return "Gagal memuat isi berita.", None

def check_news():
    print("Memeriksa berita terbaru...")
    sent_urls = load_sent_history()

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:
                url = entry.link
                if url in sent_urls:
                    continue
                
                print(f"--> Memproses: {source_name} | {entry.title[:30]}...")
                title_id = safe_translate(entry.title)
                rss_summary = entry.summary if 'summary' in entry else ""

                summary_id, image_url = process_and_translate_article(url, rss_summary)
                send_telegram_news(title_id, url, image_url, summary_id, source_name)
                
                save_to_history(url)
                sent_urls.add(url)
                time.sleep(3)
        except Exception as e:
            print(f"Error {source_name}: {e}")

if __name__ == "__main__":
    threading.Thread(target=start_health_check_server, daemon=True).start()
    while True:
        check_news()
        print("Selesai patroli. Menunggu 60 detik...")
        time.sleep(60)
