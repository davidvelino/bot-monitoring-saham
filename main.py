import os
import time
import requests
import feedparser
from newspaper import Article, Config
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup

# Konfigurasi Railway
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# DAFTAR RSS FEEDS (GABUNGAN GLOBAL, INDONESIA & CRYPTO)
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
    
    # Forex & General Market
    "BabyPips": "https://www.babypips.com/feed",
    "Forex Factory": "https://www.forexfactory.com/news.xml",
    "Bloomberg / WSJ": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
    "CNBC World": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrptogo&id=100727362",
    "Investopedia": "https://www.investopedia.com/feedbuilder/feed/getfeed/?feedName=news",

    # Saham & Market Indonesia Baru
    "CNBC Indonesia": "https://www.cnbcindonesia.com/market/rss",
    "Bisnis.com Market": "https://market.bisnis.com/rss",
    "Kontan Investasi": "https://investasi.kontan.co.id/rss",

    # Crypto Global & Indonesia Baru
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
    """Membersihkan tag HTML kotor dari bawaan web/RSS"""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator="\n").strip()

def create_summary(raw_text):
    """Mengekstrak inti sari / 3 paragraf pertama agar enak dibaca di Telegram"""
    if not raw_text:
        return ""
    
    # Memisahkan berdasarkan paragraf dan mengambil yang berbobot (bukan sekadar spasi/iklan)
    paragraphs = [p.strip() for p in raw_text.split('\n') if len(p.strip()) > 80]
    
    # Ambil maksimal 3 paragraf utama sebagai kesimpulan
    summary_text = "\n\n".join(paragraphs[:3])
    return summary_text

def send_telegram_news(title, original_url, photo_url, summary_id, source):
    """Mengirim pesan dengan format ringkas yang profesional"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Token Telegram belum diset!")
        return

    # Merakit pesan elegan (Judul, Ringkasan, Link Asli)
    caption = (
        f"🚨 <b>BERITA TERBARU: {source}</b> 🚨\n\n"
        f"📰 <b>{title}</b>\n\n"
        f"📝 <b>Inti Sari Berita:</b>\n{summary_id}\n\n"
        f"🔗 <a href='{original_url}'>Baca Selengkapnya di Sini</a>"
    )

    # Batasi limit 1024 karakter Telegram untuk caption foto
    if len(caption) > 1000:
        caption = caption[:950] + f"...\n\n🔗 <a href='{original_url}'>Baca Selengkapnya di Sini</a>"

    try:
        # Prioritaskan kirim beserta Gambar (Foto)
        if photo_url:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
            res = requests.post(url, json=payload, timeout=20)
            
            # Jika gagal kirim foto (misal url gambar corrupt), fallback ke teks biasa
            if res.status_code != 200:
                url_text = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                payload_text = {"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "HTML"}
                requests.post(url_text, json=payload_text, timeout=20)
        else:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "HTML"}
            requests.post(url, json=payload, timeout=20)
            
    except Exception as e:
        print(f"Gagal mengirim ke Telegram: {e}")

def process_and_translate_article(url, rss_summary):
    """Menyedot artikel, membuat ringkasan, dan menerjemahkannya ke Bahasa Indonesia"""
    try:
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        config = Config()
        config.browser_user_agent = user_agent
        config.request_timeout = 15

        article = Article(url, config=config)
        article.download()
        article.parse()
        
        raw_text = article.text
        top_image = article.top_image

        # Jika website memblokir bot, ambil ringkasan resmi dari RSS feed
        if not raw_text or len(raw_text) < 100:
            raw_text = clean_html(rss_summary)
            if not raw_text:
                raw_text = "Berita ini dikunci oleh sekuriti web. Silakan langsung klik link untuk membaca langsung."

        # Ekstrak 3 Paragraf Utama Saja (Kesimpulan)
        summary_text = create_summary(raw_text)
        
        # Jika peringkas gagal, gunakan potong karakter standar
        if not summary_text:
            summary_text = raw_text[:500] + "..."

        # Terjemahkan ke Bahasa Indonesia
        translator = GoogleTranslator(source='auto', target='id')
        translated_summary = translator.translate(summary_text)
        
        return translated_summary, top_image

    except Exception as e:
        print(f"Gagal scrape {url}: {e}")
        # Sistem Cadangan Darurat
        fallback_text = clean_html(rss_summary)
        if fallback_text:
            try:
                translated = GoogleTranslator(source='auto', target='id').translate(fallback_text[:500])
                return translated + "...", None
            except:
                return fallback_text, None
        return "Gagal memuat isi berita.", None

def check_news():
    print("Mencari berita terbaru (Global & Indonesia)...")
    sent_urls = load_sent_history()
    translator = GoogleTranslator(source='auto', target='id')

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            
            # Cek 2 berita paling atas dari setiap sumber
            for entry in feed.entries[:2]:
                url = entry.link
                
                # Jangan kirim berita yang sama dua kali
                if url in sent_urls:
                    continue
                
                print(f"--> Memproses: {source_name} | {entry.title[:30]}...")
                
                # Terjemahkan Judul
                raw_title = entry.title
                title_id = translator.translate(raw_title)

                rss_summary = entry.summary if 'summary' in entry else ""

                # Sedot isi berita & Buat Ringkasan (Kesimpulan)
                summary_id, image_url = process_and_translate_article(url, rss_summary)
                
                # Kirim Pesan Tunggal ke Telegram (Gambar + Judul + Ringkasan + Link)
                send_telegram_news(title_id, url, image_url, summary_id, source_name)
                
                # Catat agar tidak dikirim ulang
                save_to_history(url)
                sent_urls.add(url)
                
                # Jeda agar tidak dianggap serangan spam oleh server Telegram
                time.sleep(3)
                
        except Exception as e:
            print(f"Error membaca {source_name}: {e}")

if __name__ == "__main__":
    while True:
        check_news()
        print("Selesai cek semua portal. Tidur 60 detik sebelum patroli berikutnya...")
        time.sleep(60)
