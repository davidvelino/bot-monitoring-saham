Markdown 
# 🤖 Telegram News Bot (RSS & Auto Translate)

Bot Telegram otomatis untuk memantau rilis berita terbaru dari berbagai portal finansial, kripto, dan berita global. Bot ini akan melakukan *scraping*, meringkas berita, menterjemahkan ke Bahasa Indonesia secara otomatis, serta menyaring pesan *error* sebelum dikirim ke channel Telegram Anda.

---

## 📋 Fitur Utama
* 🔄 **Auto Check Every 1 Minute:** Memeriksa rilis berita terbaru setiap 60 detik.
* 🌐 **Multi-Source RSS Feed:** Mendukung berbagai sumber berita (Cointelegraph, CoinDesk, CNBC Indonesia, Bisnis.com, Yahoo Finance, dll).
* 🇮🇩 **Auto Translate & Summary:** Menterjemahkan judul dan meringkas isi berita ke Bahasa Indonesia menggunakan `deep-translator`.
* 🛡️ **Error Filtering:** Fitur otomatis untuk memblokir dan mengabaikan halaman *Error 500*, *404*, atau *Access Denied* agar tidak terkirim ke channel.
* ⚡ **Anti-Sleep Server:** Dilengkapi dengan HTTP Healthcheck server mini agar bot tetap aktif 24/7 saat di-host di Cloud (seperti Render).

---

## 🛠️ Persyaratan Sistem (Prerequisites)

Sebelum memulai, pastikan Anda telah menyiapkan:
1. **Akun GitHub**
2. **Akun Render** (atau platform cloud hosting lainnya)
3. **Bot Telegram & Channel Telegram**
   * Token Bot dari [@BotFather](https://t.me/BotFather)
   * Chat ID / Username Channel Telegram (misal: `@ChannelAnda`)

---

## 📁 Struktur File Repositori

Buat repositori GitHub baru dan siapkan file dengan struktur berikut:

```text
├── main.py
├── requirements.txt
├── Procfile
└── README.md

🚀 Panduan Langkah demi Langkah
Langkah 1: Buat File requirements.txt
File ini berisi semua library Python yang dibutuhkan oleh bot.

requests
feedparser
newspaper3k
beautifulsoup4
deep-translator

Langkah 2: Buat File Procfile
File ini memberitahu platform hosting cara menjalankan skrip Python Anda.

web: python main.py

Langkah 3: Buat File main.py
Isi file main.py dengan kode lengkap berikut:

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

# 1. Server Mini Anti-Sleep untuk Cloud Hosting
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

# 2. Konfigurasi Environment Variables
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TOKEN = os.getenv("TELEGRAM_TOKEN")

# 3. Daftar RSS Feeds Berita
RSS_FEEDS = {
    # Crypto
    "Cointelegraph": "[https://cointelegraph.com/rss](https://cointelegraph.com/rss)",
    "CoinDesk": "[https://www.coindesk.com/arc/outboundfeeds/rss/](https://www.coindesk.com/arc/outboundfeeds/rss/)",
    "Pintu News": "[https://pintu.co.id/blog/feed](https://pintu.co.id/blog/feed)",
    "Blockchain Media ID": "[https://blockchainmedia.id/feed/](https://blockchainmedia.id/feed/)",

    # Indonesia Finance
    "CNBC Indonesia Market": "[https://www.cnbcindonesia.com/market/rss](https://www.cnbcindonesia.com/market/rss)",
    "CNBC Indonesia News": "[https://www.cnbcindonesia.com/news/rss](https://www.cnbcindonesia.com/news/rss)",
    "CNBC Indonesia Investment": "[https://www.cnbcindonesia.com/investment/rss](https://www.cnbcindonesia.com/investment/rss)",
    "Bisnis.com Market": "[https://market.bisnis.com/rss](https://market.bisnis.com/rss)",
    "Kontan Investasi": "[https://investasi.kontan.co.id/rss](https://investasi.kontan.co.id/rss)",
    "Detik Finance": "[https://finance.detik.com/rss](https://finance.detik.com/rss)",

    # Global Market
    "CNBC World News": "[https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrptogo&id=100727362](https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrptogo&id=100727362)",
    "MarketWatch Top Stories": "[https://feeds.content.dowjones.io/public/rss/mw_topstories](https://feeds.content.dowjones.io/public/rss/mw_topstories)",
    "Yahoo Finance": "[https://finance.yahoo.com/news/rssindex](https://finance.yahoo.com/news/rssindex)",
    "Investing.com": "[https://www.investing.com/rss/news.rss](https://www.investing.com/rss/news.rss)"
}

SENT_URLS_CACHE = set()

# 4. Fungsi Pembantu (Helper Functions)
def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ").strip()

def safe_translate(text):
    if not text or len(text.strip()) == 0:
        return ""
    text_to_translate = text[:450].strip()
    try:
        translated = GoogleTranslator(source='auto', target='id').translate(text_to_translate)
        if translated:
            return translated
    except Exception as e:
        print(f"Gagal translate: {e}")
    return text_to_translate

def make_summary(text, fallback_title=""):
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
        print("ERROR: CHAT_ID atau TOKEN belum diset!")
        return

    if image_url:
        url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TOKEN}/sendPhoto"
        payload = {"chat_id": CHAT_ID, "photo": image_url, "caption": text, "parse_mode": "HTML"}
        try:
            res = requests.post(url, data=payload, timeout=15)
            if res.status_code == 200:
                return
        except Exception:
            pass

    url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}
    try:
        requests.post(url, data=payload, timeout=15)
    except Exception as e:
        print(f"Gagal kirim ke Channel: {e}")

def process_article(url, rss_summary, raw_title):
    top_image = None
    extracted_text = ""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
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

    if not extracted_text or len(extracted_text.strip()) < 30:
        extracted_text = rss_summary

    summary_id = make_summary(extracted_text, fallback_title=raw_title)
    return summary_id, top_image

# 5. Fungsi Utama Pengecekan Berita
def check_news():
    print("Memeriksa rilis berita terbaru...")
    ERROR_KEYWORDS = ["error 500", "server error", "that's an error", "404 not found", "access denied", "502 bad gateway"]

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:
                url = entry.link
                if url in SENT_URLS_CACHE:
                    continue

                raw_title = entry.title
                if any(err in raw_title.lower() for err in ERROR_KEYWORDS):
                    SENT_URLS_CACHE.add(url)
                    continue

                title_id = safe_translate(raw_title)
                if any(err in title_id.lower() for err in ERROR_KEYWORDS):
                    SENT_URLS_CACHE.add(url)
                    continue

                SENT_URLS_CACHE.add(url)
                print(f"--> [KIRIM KE CHANNEL] {source_name}: {raw_title[:30]}...")

                rss_summary = ""
                if 'summary' in entry:
                    rss_summary = entry.summary
                elif 'description' in entry:
                    rss_summary = entry.description

                summary_id, image_url = process_article(url, rss_summary, raw_title)
                if any(err in summary_id.lower() for err in ERROR_KEYWORDS):
                    continue

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
                time.sleep(3)
        except Exception as e:
            print(f"Error pada {source_name}: {e}")

# 6. Eksekusi Program
if __name__ == "__main__":
    threading.Thread(target=start_health_check_server, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    
    while True:
        check_news()
        print("Selesai cek. Menunggu 60 detik...")
        time.sleep(60)

Berikut adalah panduan lengkap dari awal sampai akhir yang disajikan dalam format **Markdown (`README.md`)**. Anda bisa langsung menyalin seluruh isi di dalam kotak kode di bawah ini dan menempelkannya (*paste*) ke file `README.md` pada repositori GitHub Anda.

---

```markdown
# 🤖 Telegram News Bot (RSS & Auto Translate)

Bot Telegram otomatis untuk memantau rilis berita terbaru dari berbagai portal finansial, kripto, dan berita global. Bot ini akan melakukan *scraping*, meringkas berita, menterjemahkan ke Bahasa Indonesia secara otomatis, serta menyaring pesan *error* sebelum dikirim ke channel Telegram Anda.

---

## 📋 Fitur Utama
* 🔄 **Auto Check Every 1 Minute:** Memeriksa rilis berita terbaru setiap 60 detik.
* 🌐 **Multi-Source RSS Feed:** Mendukung berbagai sumber berita (Cointelegraph, CoinDesk, CNBC Indonesia, Bisnis.com, Yahoo Finance, dll).
* 🇮🇩 **Auto Translate & Summary:** Menterjemahkan judul dan meringkas isi berita ke Bahasa Indonesia menggunakan `deep-translator`.
* 🛡️ **Error Filtering:** Fitur otomatis untuk memblokir dan mengabaikan halaman *Error 500*, *404*, atau *Access Denied* agar tidak terkirim ke channel.
* ⚡ **Anti-Sleep Server:** Dilengkapi dengan HTTP Healthcheck server mini agar bot tetap aktif 24/7 saat di-host di Cloud (seperti Render).

---

## 🛠️ Persyaratan Sistem (Prerequisites)

Sebelum memulai, pastikan Anda telah menyiapkan:
1. **Akun GitHub**
2. **Akun Render** (atau platform cloud hosting lainnya)
3. **Bot Telegram & Channel Telegram**
   * Token Bot dari [@BotFather](https://t.me/BotFather)
   * Chat ID / Username Channel Telegram (misal: `@ChannelAnda`)

---

## 📁 Struktur File Repositori

Buat repositori GitHub baru dan siapkan file dengan struktur berikut:

```text
├── main.py
├── requirements.txt
├── Procfile
└── README.md

```

---

## 🚀 Panduan Langkah demi Langkah

### Langkah 1: Buat File `requirements.txt`

File ini berisi semua library Python yang dibutuhkan oleh bot.

```text
requests
feedparser
newspaper3k
beautifulsoup4
deep-translator

```

---

### Langkah 2: Buat File `Procfile`

File ini memberitahu platform hosting cara menjalankan skrip Python Anda.

```text
web: python main.py

```

---

### Langkah 3: Buat File `main.py`

Isi file `main.py` dengan kode lengkap berikut:

```python
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

# 1. Server Mini Anti-Sleep untuk Cloud Hosting
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

# 2. Konfigurasi Environment Variables
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TOKEN = os.getenv("TELEGRAM_TOKEN")

# 3. Daftar RSS Feeds Berita
RSS_FEEDS = {
    # Crypto
    "Cointelegraph": "[https://cointelegraph.com/rss](https://cointelegraph.com/rss)",
    "CoinDesk": "[https://www.coindesk.com/arc/outboundfeeds/rss/](https://www.coindesk.com/arc/outboundfeeds/rss/)",
    "Pintu News": "[https://pintu.co.id/blog/feed](https://pintu.co.id/blog/feed)",
    "Blockchain Media ID": "[https://blockchainmedia.id/feed/](https://blockchainmedia.id/feed/)",

    # Indonesia Finance
    "CNBC Indonesia Market": "[https://www.cnbcindonesia.com/market/rss](https://www.cnbcindonesia.com/market/rss)",
    "CNBC Indonesia News": "[https://www.cnbcindonesia.com/news/rss](https://www.cnbcindonesia.com/news/rss)",
    "CNBC Indonesia Investment": "[https://www.cnbcindonesia.com/investment/rss](https://www.cnbcindonesia.com/investment/rss)",
    "Bisnis.com Market": "[https://market.bisnis.com/rss](https://market.bisnis.com/rss)",
    "Kontan Investasi": "[https://investasi.kontan.co.id/rss](https://investasi.kontan.co.id/rss)",
    "Detik Finance": "[https://finance.detik.com/rss](https://finance.detik.com/rss)",

    # Global Market
    "CNBC World News": "[https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrptogo&id=100727362](https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrptogo&id=100727362)",
    "MarketWatch Top Stories": "[https://feeds.content.dowjones.io/public/rss/mw_topstories](https://feeds.content.dowjones.io/public/rss/mw_topstories)",
    "Yahoo Finance": "[https://finance.yahoo.com/news/rssindex](https://finance.yahoo.com/news/rssindex)",
    "Investing.com": "[https://www.investing.com/rss/news.rss](https://www.investing.com/rss/news.rss)"
}

SENT_URLS_CACHE = set()

# 4. Fungsi Pembantu (Helper Functions)
def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ").strip()

def safe_translate(text):
    if not text or len(text.strip()) == 0:
        return ""
    text_to_translate = text[:450].strip()
    try:
        translated = GoogleTranslator(source='auto', target='id').translate(text_to_translate)
        if translated:
            return translated
    except Exception as e:
        print(f"Gagal translate: {e}")
    return text_to_translate

def make_summary(text, fallback_title=""):
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
        print("ERROR: CHAT_ID atau TOKEN belum diset!")
        return

    if image_url:
        url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TOKEN}/sendPhoto"
        payload = {"chat_id": CHAT_ID, "photo": image_url, "caption": text, "parse_mode": "HTML"}
        try:
            res = requests.post(url, data=payload, timeout=15)
            if res.status_code == 200:
                return
        except Exception:
            pass

    url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}
    try:
        requests.post(url, data=payload, timeout=15)
    except Exception as e:
        print(f"Gagal kirim ke Channel: {e}")

def process_article(url, rss_summary, raw_title):
    top_image = None
    extracted_text = ""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
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

    if not extracted_text or len(extracted_text.strip()) < 30:
        extracted_text = rss_summary

    summary_id = make_summary(extracted_text, fallback_title=raw_title)
    return summary_id, top_image

# 5. Fungsi Utama Pengecekan Berita
def check_news():
    print("Memeriksa rilis berita terbaru...")
    ERROR_KEYWORDS = ["error 500", "server error", "that's an error", "404 not found", "access denied", "502 bad gateway"]

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:
                url = entry.link
                if url in SENT_URLS_CACHE:
                    continue

                raw_title = entry.title
                if any(err in raw_title.lower() for err in ERROR_KEYWORDS):
                    SENT_URLS_CACHE.add(url)
                    continue

                title_id = safe_translate(raw_title)
                if any(err in title_id.lower() for err in ERROR_KEYWORDS):
                    SENT_URLS_CACHE.add(url)
                    continue

                SENT_URLS_CACHE.add(url)
                print(f"--> [KIRIM KE CHANNEL] {source_name}: {raw_title[:30]}...")

                rss_summary = ""
                if 'summary' in entry:
                    rss_summary = entry.summary
                elif 'description' in entry:
                    rss_summary = entry.description

                summary_id, image_url = process_article(url, rss_summary, raw_title)
                if any(err in summary_id.lower() for err in ERROR_KEYWORDS):
                    continue

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
                time.sleep(3)
        except Exception as e:
            print(f"Error pada {source_name}: {e}")

# 6. Eksekusi Program
if __name__ == "__main__":
    threading.Thread(target=start_health_check_server, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    
    while True:
        check_news()
        print("Selesai cek. Menunggu 60 detik...")
        time.sleep(60)

```

---

### Langkah 4: Panduan Deploy ke Render.com

1. Masuk ke dashboard [Render.com](https://dashboard.render.com/) dan buat **Web Service** baru.
2. Hubungkan akun GitHub Anda dan pilih repositori ini.
3. Isikan opsi konfigurasi berikut:
* **Name:** `bot-news-telegram` (atau nama lain pilihan Anda)
* **Environment:** `Python 3`
* **Build Command:** `pip install -r requirements.txt`
* **Start Command:** `python main.py`


4. Gulir ke bawah ke bagian **Environment Variables** dan tambahkan 2 variabel wajib berikut:
* `TELEGRAM_TOKEN`: Token Bot Anda dari BotFather (contoh: `123456789:ABCdefGhI...`)
* `TELEGRAM_CHAT_ID`: Username Channel Anda (contoh: `@MacroNewsOfficial`) atau ID Angka Channel.


5. Klik **Create Web Service**. Bot Anda sekarang berjalan otomatis 24/7!

---

## 📝 Catatan Penting

* Pastikan Bot Telegram Anda sudah ditambahkan sebagai **Admin** di Channel Telegram agar memiliki izin mengirimkan pesan.
* Pengaturan waktu penundaan `time.sleep(60)` disesuaikan untuk interval 1 menit. Jangan diset terlalu kecil agar IP server Anda tidak terblokir oleh penyedia RSS/Berita.

```

```
