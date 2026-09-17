import subprocess
import platform
import sys
import importlib.util

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[94m"
RESET = "\033[0m"

gecikme = 2.5

def check_requirements():
    if getattr(sys, 'frozen', False):
        return
    required_packages = ["requests", "selenium", "tqdm"]
    missing_packages = []

    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            missing_packages.append(package)

    if missing_packages:
        print(f"{RED}[!] Eksik paketler tespit edildi: {', '.join(missing_packages)}\n")
        print(f"{YELLOW}[!] Bağımlılıklar kuruluyor...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--break-system-packages"] + missing_packages,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        print(f"{GREEN}[+] Tüm bağımlılıklar eksiksiz.")
check_requirements()

from tqdm import tqdm
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def get_smart_driver():
    sys_platform = platform.system()
    
    # 1. Önce Chrome'u denetle (Gelişmiş Bot Gizleme Parametreleriyle)
    try:
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        options = ChromeOptions()
        options.page_load_strategy = "eager"
        options.add_argument("--headless=new") # Modern ve daha az yakalanan headless modu
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # Otomasyon izlerini gizleyen kritik bayraklar
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        # Ekstra JavaScript koruma gizlemesi
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception:
        pass 

    # 2. Microsoft Edge'i denetle
    try:
        from selenium.webdriver.edge.options import Options as EdgeOptions
        options = EdgeOptions()
        options.page_load_strategy = "eager"
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Edge(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception:
        pass

    # 3. Firefox'u denetle
    try:
        options.page_load_strategy = "eager"
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
        options = FirefoxOptions()
        options.add_argument("-headless")
        options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0")
        return webdriver.Firefox(options=options)
    except Exception:
        pass 

    # 4. Mac için Safari'yi denetle
    if sys_platform == "Darwin":
        try:
            return webdriver.Safari()
        except Exception:
            pass

    return None

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time

def check_selenium_profile(driver, url):
    try:
        driver.set_page_load_timeout(20)
        try:
            driver.get(url)
            try:
                # DOM hazır olana kadar bekle (resim, CSS, iframe bekleme)
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except Exception:
                pass # Zaman aşımı olursa devam et
        except Exception:
            pass

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception:
            pass

        time.sleep(2.5)

        title = (driver.title or "").lower().strip()
        current_url = (driver.current_url or "").lower()

        try:
            page_text = driver.page_source.lower()
        except Exception:
            page_text = ""

        # Hangi site kuralı eşleşiyor?
        matched_rule = None
        matched_domain = None
        for domain, rule in SITE_RULES.items():
            if domain in url.lower():
                matched_rule = rule
                matched_domain = domain
                break

        # ─── KURAL YOKSA: genel sezgisel kontrol ───
        if not matched_rule:
            if "404" in title or "not found" in title or "bulunamadı" in title:
                return False
            for err in ["bulunamadı", "not found", "sayfa bulunamadı",
                        "page not found", "error", "404",
                        "bu içeriğe şu anda ulaşılamıyor"]:
                if err in title and len(title) < 50:
                    return False
            return True

        # ─── 1) Login / redirect kontrolü ───
        for login_path in matched_rule.get("login_urls", []):
            if login_path in current_url:
                return False

        # ─── 2) Yasaklı başlık kontrolü (login wall vb.) ───
        for bt in matched_rule.get("blocked_titles", []):
            if bt in title:
                return False

        # ─── 3) Negatif sinyaller (page_source'ta) ───
        for nf in matched_rule.get("not_found", []):
            if nf in page_text:
                return False

        # ─── 4) og:type zorunlu mu? ───
        og_type_required = matched_rule.get("og_type")
        if og_type_required:
            try:
                og_type = driver.find_element(
                    By.XPATH, "//meta[@property='og:type']"
                ).get_attribute("content").lower().strip()
                if og_type != og_type_required:
                    return False
            except Exception:
                return False

        # ─── 5) og:title yasaklı mı? (Telegram için) ───
        forbidden_og_titles = matched_rule.get("require_og_title_not", [])
        if forbidden_og_titles:
            try:
                og_title = driver.find_element(
                    By.XPATH, "//meta[@property='og:title']"
                ).get_attribute("content").lower().strip()
                if any(ft in og_title for ft in forbidden_og_titles):
                    return False
            except Exception:
                return False

        # ─── 6) Pozitif sinyal (en az biri geçmeli) ───
        ok_signals = matched_rule.get("ok_signals", [])
        if ok_signals and not any(s in page_text for s in ok_signals):
            return False

        return True

    except Exception:
        return False
    # finally YOK — driver Start() içinde kapatılıyor
    
found_links = []

Extra_characters = ["_", "."]

# ============================================================
# SİTE KURALLARI
# Her site için:
#   login_urls  : current_url içinde geçerse → profil yok
#   not_found   : page_source içinde geçerse → profil yok
#   ok_signals  : page_source içinde geçerse → profil var (en az biri)
#   og_type     : (opsiyonel) og:type tam olarak bu olmalı
#   require_og  : (opsiyonel) og:title zorunlu mu? (default True)
# ============================================================
SITE_RULES = {
    "facebook.com": {
        "login_urls": ["/login", "/r.php", "/checkpoint", "/recover"],
        "not_found": [
            "bu içerik şu anda kullanılamıyor", "bu içeriğe ulaşılamıyor",
            "bu sayfa mevcut değil", "aradığınız sayfa bulunamadı",
            "içerik bulunamadı", "sayfa bulunamadı",
            "this content isn't available", "this page isn't available",
            "page not found", "content not found",
        ],
        "ok_signals": ["takipçi", "arkadaş", "gönderi", "hakkında", "followers", "friends"],
        "og_type": "profile",
        "blocked_titles": ["facebook", "log into facebook", "facebook - log in or sign up"],
    },
    "instagram.com": {
        "login_urls": ["/accounts/login", "/login"],
        "not_found": [
            "üzgünüz, bu sayfaya ulaşılamıyor", "tıklandığın bağlantı bozuk olabilir",
            "sayfa kaldırılmış olabilir", "sorry, this page isn't available",
            "the link you followed may be broken", "page not found", "sayfa bulunamadı",
        ],
        "ok_signals": ["followers", "takipçi", "posts", "gönderi", "following", "takip"],
        "og_type": "profile",
    },
    "threads.net": {
        "login_urls": ["/login", "/accounts/login"],
        "not_found": [
            # Türkçe
            "üzgünüz, bu sayfa kullanılamıyor",
            "üzgünüz, bu içerik kullanılamıyor",
            "bu sayfa mevcut değil",
            "kullanıcı bulunamadı",
            "sayfa bulunamadı",
            # İngilizce
            "sorry, this page isn't available",
            "this page isn't available",
            "sorry, this content isn't available",
            "user not found",
            "page not found",
        ],
        "ok_signals": ["followers", "takipçi", "threads", "following", "takip"],
        "og_type": "profile",
        "blocked_titles": ["threads", "threads • giriş yap"],
    },
    "threads.com": {  # Threads'in yeni domaini
        "login_urls": ["/login", "/accounts/login"],
        "not_found": [
            "üzgünüz, bu sayfa kullanılamıyor",
            "üzgünüz, bu içerik kullanılamıyor",
            "bu sayfa mevcut değil",
            "kullanıcı bulunamadı",
            "sorry, this page isn't available",
            "user not found",
            "page not found",
        ],
        "ok_signals": ["followers", "takipçi", "threads", "following", "takip"],
        "og_type": "profile",
        "blocked_titles": ["threads", "threads • giriş yap"],
    },
    "youtube.com": {
        "login_urls": [],
        "not_found": [
            "this channel doesn't exist", "this page isn't available",
            "bu kanal mevcut değil", "bu sayfa kullanılamıyor",
        ],
        "ok_signals": ["subscriber", "abone", "video", "kanal", "channel"],
        "og_type": None,
    },
    "tiktok.com": {
        "login_urls": ["/login"],
        "not_found": [
            "couldn't find this account", "bu hesabı bulamadık",
            "sayfa mevcut değil", "page not available", "video currently unavailable",
        ],
        "ok_signals": ["followers", "takipçi", "likes", "beğeni", "following"],
        "og_type": None,
    },
    "twitter.com": {
        "login_urls": ["/i/flow/login", "/login", "/i/flow/signup"],
        "not_found": [
            "this account doesn't exist", "bu hesap mevcut değil",
            "account doesn't exist", "hesap bulunamadı",
            "hmm...this page doesn't exist",
            "bu sayfa mevcut değil",
            # Login wall (sayfa içeriğinde)
            "neler olduğunu gör",
            "aşağıdaki seçeneği seçin",
            "telefon ile devam et",
            "google ile devam et",
            "apple ile devam et",
            "see what's happening",
            "sign in to x",
            "sign in to twitter",
            "hesap oluştur",
            "log in",
        ],
        "ok_signals": ["followers", "takipçi", "following", "tweets", "gönderi"],
        "blocked_titles": [
            "x. it's what's happening",
            "twitter. it's what's happening",
            "neler oluyor",
        ],
        "og_type": None,
    },
    "x.com": {  # Twitter'ın yeni domaini
        "login_urls": ["/i/flow/login", "/login", "/i/flow/signup"],
        "not_found": [
            "this account doesn't exist", "bu hesap mevcut değil",
            "neler olduğunu gör",
            "aşağıdaki seçeneği seçin",
            "telefon ile devam et",
            "google ile devam et",
            "apple ile devam et",
            "see what's happening",
            "sign in to x",
        ],
        "ok_signals": ["followers", "following", "tweets"],
        "blocked_titles": ["x. it's what's happening"],
        "og_type": None,
    },
    "linkedin.com": {
        "login_urls": ["/login", "/signup", "/uas/login"],
        "not_found": [
            "page not found", "sayfa bulunamadı", "profile not found",
            "this page doesn't exist", "bu sayfa mevcut değil",
        ],
        "ok_signals": ["connections", "bağlantı", "followers", "takipçi", "experience"],
        "og_type": "profile",
        "blocked_titles": ["linkedin: log in or sign up", "giriş yap"],
    },
    "github.com": {
        "login_urls": [],
        "not_found": ["page not found", "sayfa bulunamadı", "404"],
        "ok_signals": ["repositories", "followers", "following", "depo", "takipçi"],
        "og_type": "profile",
    },
    "reddit.com": {
        "login_urls": ["/login"],
        "not_found": [
            "kimse bu adı kullanmıyor", "bu hesap yasaklanmış",
            "sorry, nobody on reddit goes by that name",
            "page not found", "not found",
        ],
        "ok_signals": ["karma", "post karma", "comment karma", "cake day"],
        "og_type": None,
    },
    "twitch.tv": {
        "login_urls": ["/login"],
        "not_found": [
            # İngilizce
            "sorry. unless you've got a time machine",
            "channel not found",
            "this channel is currently unavailable",
            # Türkçe (eklendi)
            "bir zaman makinesine sahip değilseniz",
            "bu içerik artık ulaşılamaz",
            "üzgünüz. bir zaman makinesine",
            "kanal mevcut değil",
            "bu kanal şu anda kullanılamıyor",
        ],
        "ok_signals": ["followers", "takipçi", "follow", "viewers"],
        "og_type": None,
    },
    "pinterest.com": {
        "login_urls": ["/login"],
        "not_found": ["user not found", "kullanıcı bulunamadı", "page not found"],
        "ok_signals": ["followers", "takipçi", "pins", "following"],
        "og_type": "profile",
    },
    "tumblr.com": {
        "login_urls": [],
        "not_found": [
            "there's nothing here", "burada hiçbir şey yok",
            "not found", "sayfa bulunamadı",
        ],
        "ok_signals": ["posts", "followers", "gönderi"],
        "og_type": None,
    },
    "spotify.com": {
        "login_urls": ["/login"],
        "not_found": ["page not found", "sayfa bulunamadı", "couldn't find"],
        "ok_signals": ["followers", "takipçi", "playlists", "public playlists"],
        "og_type": "profile",
    },
    "steamcommunity.com": {
        "login_urls": [],
        "not_found": [
            "the specified profile could not be found",
            "belirtilen profil bulunamadı",
        ],
        "ok_signals": ["games", "oyun", "friends", "arkadaş", "badges"],
        "og_type": "profile",
    },
    "medium.com": {
        "login_urls": [],
        "not_found": ["404", "out of nothing, something", "page not found"],
        "ok_signals": ["followers", "takipçi", "following", "stories"],
        "og_type": "profile",
    },
    "vk.com": {
        "login_urls": ["/login"],
        "not_found": ["page not found", "sayfa bulunamadı"],
        "ok_signals": ["followers", "friends", "arkadaş", "подписчики"],
        "og_type": "profile",
    },
    "quora.com": {
        "login_urls": ["/login"],
        "not_found": ["page not found", "we couldn't find"],
        "ok_signals": ["followers", "answers", "questions", "yanıt"],
        "og_type": "profile",
    },
    "soundcloud.com": {
        "login_urls": ["/signin", "/login"],
        "not_found": ["we can't find that user", "kullanıcı bulunamadı", "404"],
        "ok_signals": ["followers", "takipçi", "tracks", "parça"],
        "og_type": "profile",
    },
    "snapchat.com": {
        "login_urls": ["/login", "/accounts/login"],
        "not_found": [
            # Türkçe (eklendi)
            "üzgünüz, bu içerik bulunamadı",
            "üzgünüz, bu içerik bulunamadı",  # noktalı/noktasız varyasyon
            "bu içerik bulunamadı",
            "üzgünüz",
            "kullanıcı bulunamadı",
            # İngilizce
            "this username does not exist",
            "sorry, we couldn't find that user",
            "user not found",
            "content not found",
            "sorry, this content couldn't be found",
        ],
        # Sinyalleri sıkılaştır — sadece Snapchat'e özgü olanlar
        "ok_signals": ["bitmoji", "snapcode", "hikaye", "story", "arkadaş ekle"],
        "og_type": None,
    },
    "t.me": {
        "login_urls": [],
        "not_found": [
            # Telegram var olmayan kanal/kullanıcı için "Preview channel" veya
            # "If you have Telegram, you can contact" yerine boş sayfa basar.
            # Aslında Telegram "username not found" gibi bir metin göstermiyor,
            # ama boş sayfada og:title "Telegram" olur.
            "sorry, this username is invalid",
            "kullanıcı adı geçersiz",
        ],
        "ok_signals": ["telegram", "members", "üye", "subscribers", "abone", "preview"],
        "og_type": None,
        # t.me'de og:title boşsa veya "Telegram" ise kullanıcı yok
        "require_og_title_not": ["telegram", "telegram messenger"],
    },
    "discord.com": {
        "login_urls": ["/login", "/register"],
        "not_found": [
            "user not found", "kullanıcı bulunamadı",
            "hmm, didn't work", "bir şeyler ters gitti",
            "this user does not exist",
        ],
        "ok_signals": ["discord", "user", "kullanıcı"],
        "og_type": None,
    },
}

urls = [
    { "name": "Facebook", "url": "https://www.facebook.com/{user}", "engine": "selenium" },
    { "name": "Instagram", "url": "https://www.instagram.com/{user}/", "engine": "selenium" },
    { "name": "Threads", "url": "https://www.threads.net/@{user}", "engine": "selenium" },
    { "name": "Twitter", "url": "https://twitter.com/{user}", "engine": "selenium" },
    { "name": "TikTok", "url": "https://www.tiktok.com/@{user}", "engine": "selenium" },
    { "name": "LinkedIn", "url": "https://www.linkedin.com/in/{user}", "engine": "selenium" },
    { "name": "Pinterest", "url": "https://www.pinterest.com/{user}/", "engine": "selenium" }, 
    { "name": "Tumblr", "url": "https://{user}.tumblr.com", "engine": "selenium" },
    { "name": "Snapchat", "url": "https://www.snapchat.com/add/{user}", "engine": "selenium" },
    { "name": "Telegram", "url": "https://t.me/{user}", "engine": "selenium" },
    { "name": "Discord", "url": "https://discord.com/users/{user}", "engine": "selenium" },
    { "name": "Reddit", "url": "https://www.reddit.com/user/{user}", "engine": "selenium" },
    { "name": "Twitch", "url": "https://www.twitch.tv/{user}", "engine": "selenium" },
    { "name": "YouTube", "url": "https://www.youtube.com/@{user}", "engine": "selenium" },
    { "name": "Vimeo", "url": "https://vimeo.com/{user}", "engine": "selenium" },
    { "name": "Flickr", "url": "https://www.flickr.com/people/{user}/", "engine": "selenium" },
    { "name": "DeviantArt", "url": "https://www.deviantart.com/{user}", "engine": "selenium" },
    { "name": "Behance", "url": "https://www.behance.net/{user}", "engine": "selenium" },
    { "name": "Dribbble", "url": "https://dribbble.com/{user}", "engine": "selenium" }, 
    { "name": "Medium", "url": "https://medium.com/@{user}", "engine": "selenium" },
    { "name": "VK", "url": "https://vk.com/{user}", "engine": "selenium" },
    { "name": "GitHub", "url": "https://github.com/{user}", "engine": "selenium" },
    { "name": "GitLab", "url": "https://gitlab.com/{user}", "engine": "selenium" },
    { "name": "Bitbucket", "url": "https://bitbucket.org/{user}/", "engine": "selenium" },
    { "name": "Stack Overflow", "url": "https://stackoverflow.com/users/{user}", "engine": "selenium" },
    { "name": "Dev.to", "url": "https://dev.to/{user}", "engine": "selenium" },
    { "name": "HackerRank", "url": "https://www.hackerrank.com/{user}", "engine": "selenium" }, 
    { "name": "LeetCode", "url": "https://leetcode.com/{user}/", "engine": "selenium" },
    { "name": "CodeWars", "url": "https://www.codewars.com/users/{user}", "engine": "selenium" },
    { "name": "Docker Hub", "url": "https://hub.docker.com/u/{user}", "engine": "selenium" }, 
    { "name": "PyPI", "url": "https://pypi.org/user/{user}/", "engine": "selenium" },
    { "name": "NPM", "url": "https://www.npmjs.com/~{user}", "engine": "selenium" },
    { "name": "RubyGems", "url": "https://rubygems.org/profiles/{user}", "engine": "selenium" },
    { "name": "CodePen", "url": "https://codepen.io/{user}", "engine": "selenium" }, 
    { "name": "Replit", "url": "https://replit.com/@{user}", "engine": "selenium" },
    { "name": "Steam", "url": "https://steamcommunity.com/id/{user}", "engine": "selenium" },
    { "name": "Xbox", "url": "https://xboxgamertag.com/search/{user}", "engine": "selenium" },
    { "name": "PlayStation", "url": "https://psnprofiles.com/{user}", "engine": "selenium" }, 
    { "name": "Nintendo", "url": "https://nintendo-master.com/profile/{user}", "engine": "selenium" },
    { "name": "Epic Games", "url": "https://www.epicgames.com/id/{user}", "engine": "selenium" },
    { "name": "Roblox", "url": "https://www.roblox.com/user.aspx?username={user}", "engine": "selenium" },
    { "name": "Minecraft", "url": "https://namemc.com/profile/{user}", "engine": "selenium" }, 
    { "name": "Patreon", "url": "https://www.patreon.com/{user}", "engine": "selenium" },
    { "name": "Gumroad", "url": "https://gumroad.com/{user}", "engine": "selenium" }, 
    { "name": "Product Hunt", "url": "https://www.producthunt.com/@{user}", "engine": "selenium" },
    { "name": "Keybase", "url": "https://keybase.io/{user}", "engine": "selenium" },
    { "name": "Gravatar", "url": "https://en.gravatar.com/{user}", "engine": "selenium" },
    { "name": "Pastebin", "url": "https://pastebin.com/u/{user}", "engine": "selenium" }, 
    { "name": "HackerOne", "url": "https://hackerone.com/{user}", "engine": "selenium" },
    { "name": "Bugcrowd", "url": "https://bugcrowd.com/{user}", "engine": "selenium" },
    { "name": "AngelList", "url": "https://angel.co/u/{user}", "engine": "selenium" }, 
    { "name": "Crunchbase", "url": "https://www.crunchbase.com/person/{user}", "engine": "selenium" },
    { "name": "Xing", "url": "https://www.xing.com/profile/{user}", "engine": "selenium" }, 
    { "name": "WordPress", "url": "https://{user}.wordpress.com", "engine": "selenium" },
    { "name": "Blogger", "url": "https://{user}.blogspot.com", "engine": "selenium" },
    { "name": "Ghost", "url": "https://{user}.ghost.io", "engine": "selenium" },
    { "name": "Write.as", "url": "https://write.as/{user}", "engine": "selenium" },
    { "name": "Substack", "url": "https://{user}.substack.com", "engine": "selenium" },
    { "name": "SoundCloud", "url": "https://soundcloud.com/{user}", "engine": "selenium" },
    { "name": "Mixcloud", "url": "https://www.mixcloud.com/{user}/", "engine": "selenium" }, 
    { "name": "Bandcamp", "url": "https://bandcamp.com/{user}", "engine": "selenium" },
    { "name": "Spotify", "url": "https://open.spotify.com/user/{user}", "engine": "selenium" }, 
    { "name": "Shazam", "url": "https://www.shazam.com/artist/{user}", "engine": "selenium" }, 
    { "name": "Last.fm", "url": "https://www.last.fm/user/{user}", "engine": "selenium" },
    { "name": "About.me", "url": "https://about.me/{user}", "engine": "selenium" },
    { "name": "RebelMouse", "url": "https://www.rebelmouse.com/{user}", "engine": "selenium" },
    { "name": "Scribd", "url": "https://www.scribd.com/{user}", "engine": "selenium" }, 
    { "name": "Slideshare", "url": "https://www.slideshare.net/{user}", "engine": "selenium" }, 
    { "name": "Imgur", "url": "https://imgur.com/user/{user}", "engine": "selenium" },
    { "name": "Giphy", "url": "https://giphy.com/{user}", "engine": "selenium" }, 
    { "name": "Couchsurfing", "url": "https://www.couchsurfing.com/people/{user}", "engine": "selenium" }, 
    { "name": "HubPages", "url": "https://hubpages.com/@{user}", "engine": "selenium" },
    { "name": "Quora", "url": "https://www.quora.com/profile/{user}", "engine": "selenium" },
    { "name": "Voat", "url": "https://voat.co/user/{user}", "engine": "selenium" },
    { "name": "8kun", "url": "https://8kun.top/{user}", "engine": "selenium" }, 
    { "name": "Ekşi Sözlük", "url": "https://eksisozluk.com/biri/{user}", "engine": "selenium" },
    { "name": "DonanımHaber", "url": "https://forum.donanimhaber.com/m_anasayfa?user={user}", "engine": "selenium" }, 
    { "name": "KizlarSoruyor", "url": "https://www.kizlarsoruyor.com/kisi/{user}", "engine": "selenium" }, 
    { "name": "OpenSea", "url": "https://opensea.io/{user}", "engine": "selenium" },
    { "name": "Rarible", "url": "https://rarible.com/{user}", "engine": "selenium" },
    { "name": "ResearchGate", "url": "https://www.researchgate.net/profile/{user}", "engine": "selenium" }, 
    { "name": "Academia", "url": "https://independent.academia.edu/{user}", "engine": "selenium" },
    { "name": "ORCID", "url": "https://orcid.org/{user}", "engine": "selenium" },
]

popular_urls = [
    { "name": "Facebook", "url": "https://www.facebook.com/{user}", "engine": "selenium" },
    { "name": "Instagram", "url": "https://www.instagram.com/{user}/", "engine": "selenium" },
    { "name": "Threads", "url": "https://www.threads.net/@{user}", "engine": "selenium" },
    { "name": "YouTube", "url": "https://www.youtube.com/@{user}", "engine": "selenium" },
    { "name": "TikTok", "url": "https://www.tiktok.com/@{user}", "engine": "selenium" },
    { "name": "GitHub", "url": "https://github.com/{user}", "engine": "selenium" },
    { "name": "Spotify", "url": "https://open.spotify.com/user/{user}", "engine": "selenium" },
    { "name": "Twitter", "url": "https://twitter.com/{user}", "engine": "selenium" },
    { "name": "LinkedIn", "url": "https://www.linkedin.com/in/{user}", "engine": "selenium" },
    { "name": "Pinterest", "url": "https://www.pinterest.com/{user}/", "engine": "selenium" },
    { "name": "Tumblr", "url": "https://{user}.tumblr.com", "engine": "selenium" },
    { "name": "Snapchat", "url": "https://www.snapchat.com/add/{user}", "engine": "selenium" },
    { "name": "Telegram", "url": "https://t.me/{user}", "engine": "selenium" },
    #{ "name": "Discord", "url": "https://discord.com/users/{user}", "engine": "selenium" },
    { "name": "Reddit", "url": "https://www.reddit.com/user/{user}", "engine": "selenium" },
    { "name": "Twitch", "url": "https://www.twitch.tv/{user}", "engine": "selenium" },
]



headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

menu_header = f"""{GREEN}
                 ▓▓▓▓             
              ▒▓▓▒▒▓▒▓▓▒          
           ▒▒░░░▒▒▒▒▒▒░░░▒▒       
       ░░░░░░▒▒        ▒▒░░░ ░▒   
     ░  ░░▒▒   ▓▓▓▓▓▓▓▓   ▒▒░▒  ░░
    ░   ░░  ▓▓▓▓  ▒▒  ▓▓▓▓  ░░   ░
    ░  ░░  ▓▓▓▓▓ ░░░░ ▓▓▓▓▓  ░░  ░
    ░  ░  ▓▓▓▓▓▓  ░░  ▓▓▓▓▒▒  ░░ ░
    ░  ░  ▒▒▒▒▒▓▒▒▒▒▒▒▒▒▒▒▒▒  ░  ░
       ░  ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒  ░   
          ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒      
           ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒       
            ▒▒▒▒▒▒▒▒▒▒▒▒▒▒        
        ░░     ▒▒▒▒▒▒▒░     ░░    
               ░      ░           
               ▒ ░▒▒░ ▒                      
                               
    \t\tTepeGöz{YELLOW} by Alperen Buba

 {RESET}My Github --> https://github.com/AlperenBuba
 My Website --> https://alperenbuba.github.io/TurkByteSoftware/{YELLOW}
"""

def Start():
    clear()
    print(menu_header)
    print(" 1. Social Media Scan\n 2. Scan all sites\n")
    try:
        secim = int(input(f" >{GREEN}"))
        if secim not in [1, 2]:
            return 0
    except ValueError:
        return 0
        
    clear()
    print(menu_header)
    username = input(f" Enter the person's username:{GREEN} ")
    if username.strip() == "":
        return 0

    variants = versionCreator(username)
    try:
        if secim == 1:
            target_urls = popular_urls
            desc_text = "[+] Sosyal Medya Taranıyor"
        elif secim == 2:
            target_urls = urls
            desc_text = "[+] Tüm Siteler Taranıyor"
        else:
            pass
    except NameError:
        return 0

    driver = get_smart_driver()
    if not driver:
        print(f"{RED}[!] Tarayıcı başlatılamadı.{RESET}")
        return

    total_steps = len(variants) * len(target_urls)
    try:
        with tqdm(total=total_steps, desc=desc_text, colour="green") as pbar:
            for variant in variants:
                for url_item in target_urls:
                    name = url_item["name"]
                    adress = url_item["url"].format(user=variant)
                    engine = url_item.get("engine", "requests")
                    if engine == "selenium":
                        if check_selenium_profile(driver, adress):
                            tqdm.write(f"{BLUE}[+] {GREEN}{name} ({variant}): Link Found! --> {adress}")
                            found_links.append((name, adress))
                    else:
                        pass
                    pbar.update(1)
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    fileCreator(username)

TR_TO_EN = str.maketrans({
    "ç": "c", "Ç": "c",
    "ğ": "g", "Ğ": "g",
    "ı": "i", "I": "i", "İ": "i",
    "ö": "o", "Ö": "o",
    "ş": "s", "Ş": "s",
    "ü": "u", "Ü": "u",
})

def tr_to_en(text):
    """Türkçe karakterleri İngilizce karşılıklarına çevirir."""
    return text.translate(TR_TO_EN)

def versionCreator(name):
    ciktilar = []
    username = name

    for characters in Extra_characters:
        cikti = f"{username.replace(' ', '')}"
        ciktilar.append(cikti)

    for characters in Extra_characters:
        if characters in ".":
            continue
        cikti = f"{username.replace(' ', characters)}"
        ciktilar.append(cikti)

    for characters in Extra_characters:
        if characters in ".":
            continue
        cikti = f"{characters}{username.replace(' ', '')}{characters}"
        ciktilar.append(cikti)

    for characters in Extra_characters:
        cikti = f"{characters}{username.replace(' ', characters)}{characters}"
        ciktilar.append(cikti)

    username_en = tr_to_en(username)
    for characters in Extra_characters:
        cikti = f"{username_en.replace(' ', '')}"
        ciktilar.append(cikti)

    for characters in Extra_characters:
        cikti = f"{username_en.replace(' ', characters)}"
        ciktilar.append(cikti)

    for characters in Extra_characters:
        cikti = f"{characters}{username_en.replace(' ', '')}{characters}"
        ciktilar.append(cikti)

    for characters in Extra_characters:
        cikti = f"{characters}{username_en.replace(' ', characters)}{characters}"
        ciktilar.append(cikti)

    return list(set(ciktilar))


def finder(user):
    for url in tqdm(urls, desc=f"{RESET}[+] TepeGoz Tarıyor: ", colour="green"):
        name = url["name"]
        adress = url["url"].format(user=user)
        engine = url.get("engine", "requests")
        if engine == "selenium":
            if check_selenium_profile(adress):
                tqdm.write(f"{BLUE}[+] {GREEN}{name}: Link Found! --> {adress}")
                found_links.append((name, adress))

def easyFinder(user):
    for url in tqdm(popular_urls, desc=f"{RESET}[+] TepeGoz Tarıyor: ", colour="green"):
        name = url["name"]
        adress = url["url"].format(user=user)
        engine = url.get("engine", "requests")
        if engine == "selenium":
            if check_selenium_profile(adress):
                tqdm.write(f"{BLUE}[+] {GREEN}{name}: Link Found! --> {adress}")
                found_links.append((name, adress))

def fileCreator(user):
    if found_links:
        save_choice = input(f"\n{BLUE}[?] Should the found links be saved to a .txt file? (Y/N): {GREEN}").strip().lower()
        if save_choice in ['Y', 'yes', 'y']:
            filename = f"{user}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"--- TepeGoz OSINT Raporu: {user} ---\n\n")
                for name, adress in found_links:
                    f.write(f"{name}: {adress}\n")
            print(f"\n{GREEN}[*] The results were successfully saved to the ‘{filename}’ file.{RESET}")
        else:
            print(f"\n{YELLOW}[*] The file-saving process was skipped.{RESET}")
    else:
        print(f"\n{YELLOW}[*] No file was created because no links were found.{RESET}")

def clear():
    if platform.system() == "Windows":
        subprocess.call("cls", shell=True)
    else:
        subprocess.call("clear", shell=True)


Start()