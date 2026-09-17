import subprocess
import platform
import sys
import importlib.util
import os
import zipfile
import urllib.request
import json

ACTIVE_BROWSER = None

if platform.system() == "Windows":
    try:
        import ctypes
        # Kod sayfasını UTF-8 yap
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
        # ANSI renk kodlarını aktifleştir
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[94m"
RESET = "\033[0m"

gecikme = 1.2

def check_requirements():
    if getattr(sys, 'frozen', False):
        return  # PyInstaller exe → paketler zaten gömülü
    
    required_packages = ["requests", "selenium", "tqdm"]
    missing_packages = []
    
    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            missing_packages.append(package)
    
    if not missing_packages:
        return  # Her şey kurulu, sessizce devam et
    
    print(f"{RED}[!] Eksik paketler: {', '.join(missing_packages)}{RESET}")
    print(f"{YELLOW}[!] Otomatik kurulum başlıyor...{RESET}")
    
    # ─── pip komutunu platforma göre oluştur ───
    pip_cmd = [sys.executable, "-m", "pip", "install"]
    
    # Linux'ta PEP 668 için gerekli (Debian/Ubuntu)
    if platform.system() == "Linux":
        pip_cmd.append("--break-system-packages")
    
    pip_cmd.extend(missing_packages)

     # ─── Windows'ta konsol penceresini gizle ───
    startupinfo = None
    if platform.system() == "Windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
    
    try:
        # İlk deneme: sessiz kur
        result = subprocess.run(
            pip_cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print(f"{GREEN}[+] Paketler kuruldu: {', '.join(missing_packages)}{RESET}")
        else:
            # İkinci deneme: --user ile kur (izin sorunu olabilir)
            print(f"{YELLOW}[!] Normal kurulum başarısız, --user deneniyor...{RESET}")
            pip_cmd.insert(-len(missing_packages), "--user")
            result2 = subprocess.run(pip_cmd, capture_output=True, text=True, timeout=300)
            
            if result2.returncode == 0:
                print(f"{GREEN}[+] Paketler kuruldu (--user): {', '.join(missing_packages)}{RESET}")
            else:
                print(f"{RED}[!] Kurulum başarısız!{RESET}")
                print(f"{YELLOW}Manuel kurun:{RESET}")
                print(f"  {' '.join(pip_cmd)}")
                print(f"{YELLOW}Hata:{RESET}")
                print(result2.stderr[:500])
                sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"{RED}[!] Kurulum zaman aşımına uğradı (5 dk).{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{RED}[!] Kurulum hatası: {e}{RESET}")
        sys.exit(1)


from tqdm import tqdm
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def get_platform_arch():
    """Sistem mimarisini belirler (Windows/Mac/Linux + ARM/x64)."""
    system = platform.system()
    machine = platform.machine().lower()
    
    if system == "Windows":
        return "win-aarch64" if ("arm" in machine or "aarch" in machine) else "win64"
    elif system == "Darwin":
        return "macos-aarch64" if "arm" in machine else "macos"
    else:  # Linux
        return "linux-aarch64" if ("arm" in machine or "aarch" in machine) else "linux64"


def download_geckodriver(drivers_dir):
    ext = ".exe" if platform.system() == "Windows" else ""
    gecko_path = os.path.join(drivers_dir, f"geckodriver{ext}")
    
    if os.path.exists(gecko_path):
        return gecko_path
    
    os.makedirs(drivers_dir, exist_ok=True)
    print(f"{YELLOW}[!] Geckodriver indiriliyor...{RESET}")
    
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/mozilla/geckodriver/releases/latest",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
        
        arch = get_platform_arch()
        download_url = None
        
        # Uygun asset'i bul (öncelik: kesin mimari → genel)
        priority = {
            "win-aarch64": ["win-aarch64"],
            "win64": ["win64"],
            "macos-aarch64": ["macos-aarch64"],
            "macos": ["macos"],
            "linux-aarch64": ["linux-aarch64"],
            "linux64": ["linux64"],
        }
        
        for asset in data["assets"]:
            name = asset["name"].lower()
            for key in priority.get(arch, []):
                if key in name and (name.endswith(".zip") or name.endswith(".tar.gz")):
                    download_url = asset["browser_download_url"]
                    break
            if download_url:
                break
        
        if not download_url:
            print(f"{RED}[!] {arch} için geckodriver bulunamadı{RESET}")
            return None
        
        archive = os.path.join(drivers_dir, "gecko_archive.tmp")
        urllib.request.urlretrieve(download_url, archive)
        
        if archive.endswith(".zip") or download_url.endswith(".zip"):
            with zipfile.ZipFile(archive, "r") as z:
                z.extractall(drivers_dir)
        else:
            import tarfile
            with tarfile.open(archive, "r:gz") as t:
                t.extractall(drivers_dir)
        
        os.remove(archive)
        
        if platform.system() != "Windows":
            os.chmod(gecko_path, 0o755)
        
        print(f"{GREEN}[+] Geckodriver hazır: {gecko_path}{RESET}")
        return gecko_path
    except Exception as e:
        print(f"{RED}[!] Geckodriver indirme hatası: {e}{RESET}")
        return None


def download_msedgedriver(drivers_dir):
    """Msedgedriver'ı (Edge) Microsoft'tan indirir."""
    ext = ".exe" if platform.system() == "Windows" else ""
    edge_path = os.path.join(drivers_dir, f"msedgedriver{ext}")
    
    if os.path.exists(edge_path):
        return edge_path
    
    os.makedirs(drivers_dir, exist_ok=True)
    print(f"{YELLOW}[!] Msedgedriver indiriliyor...{RESET}")
    
    try:
        # Edge sürümünü bul
        import subprocess as sp
        edge_exe = None
        candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                edge_exe = c
                break
        
        if not edge_exe:
            print(f"{RED}[!] Edge kurulu değil{RESET}")
            return None
        
        result = sp.run([edge_exe, "--version"], capture_output=True, text=True)
        version = result.stdout.strip().split()[-1]  # "122.0.2365.92"
        
        arch = "arm64" if get_platform_arch() == "win-aarch64" else "win64"
        url = f"https://msedgedriver.microsoft.com/{version}/edgedriver_{arch}.zip"
        
        archive = os.path.join(drivers_dir, "edge_archive.tmp")
        urllib.request.urlretrieve(url, archive)
        
        with zipfile.ZipFile(archive, "r") as z:
            z.extractall(drivers_dir)
        
        # Bazen alt klasöre çıkarır
        for root, dirs, files in os.walk(drivers_dir):
            if "msedgedriver.exe" in files:
                src = os.path.join(root, "msedgedriver.exe")
                if src != edge_path:
                    import shutil
                    shutil.move(src, edge_path)
                break
        
        os.remove(archive)
        print(f"{GREEN}[+] Msedgedriver hazır: {edge_path}{RESET}")
        return edge_path
    except Exception as e:
        print(f"{RED}[!] Msedgedriver indirme hatası: {e}{RESET}")
        return None

import os
import zipfile
import urllib.request
import json
import platform

def get_arch():
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Windows":
        return "win-aarch64" if "arm" in machine or "aarch" in machine else "win64"
    elif system == "Darwin":
        return "macos-aarch64" if "arm" in machine else "macos"
    else:
        return "linux-aarch64" if "arm" in machine or "aarch" in machine else "linux64"


def ensure_geckodriver():
    base = os.path.dirname(os.path.abspath(__file__))
    drivers_dir = os.path.join(base, "drivers")
    os.makedirs(drivers_dir, exist_ok=True)
    ext = ".exe" if platform.system() == "Windows" else ""
    path = os.path.join(drivers_dir, f"geckodriver{ext}")
    
    if os.path.exists(path):
        return path
    
    print(f"{YELLOW}[!] Geckodriver indiriliyor...{RESET}")
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/mozilla/geckodriver/releases/latest",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        
        arch = get_arch()
        url = None
        for asset in data["assets"]:
            name = asset["name"].lower()
            if arch in name and name.endswith((".zip", ".tar.gz")):
                url = asset["browser_download_url"]
                break
        
        if not url:
            return None
        
        archive = os.path.join(drivers_dir, "gecko.tmp")
        with urllib.request.urlopen(url, timeout=60) as r:
            with open(archive, "wb") as f:
                f.write(r.read())
        
        if url.endswith(".zip"):
            with zipfile.ZipFile(archive, "r") as z:
                z.extractall(drivers_dir)
        else:
            import tarfile
            with tarfile.open(archive, "r:gz") as t:
                t.extractall(drivers_dir)
        
        os.remove(archive)
        if platform.system() != "Windows":
            os.chmod(path, 0o755)
        
        print(f"{GREEN}[+] Geckodriver hazır{RESET}")
        return path
    except Exception as e:
        print(f"{RED}[!] Geckodriver indirilemedi: {e}{RESET}")
        return None

def ensure_all_drivers():
    print(f"{BLUE}[i] Driver kontrol ediliyor...{RESET}")
    ensure_geckodriver()

def detect_browser():
    global ACTIVE_BROWSER
    if ACTIVE_BROWSER:
        return ACTIVE_BROWSER
    
    base = os.path.dirname(os.path.abspath(__file__))
    drivers_dir = os.path.join(base, "drivers")
    ext = ".exe" if platform.system() == "Windows" else ""
    
    # ─── 1. Chrome kurulu mu? ───
    chrome_ok = False
    if platform.system() == "Windows":
        chrome_ok = any(os.path.exists(p) for p in [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ])
    elif platform.system() == "Darwin":
        chrome_ok = os.path.exists("/Applications/Google Chrome.app")
    else:
        chrome_ok = any(os.path.exists(p) for p in 
            ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"])
    
    if chrome_ok:
        try:
            test_driver = _make_chrome_driver()
            test_driver.quit()
            ACTIVE_BROWSER = "chrome"
            return "chrome"
        except Exception:
            pass
    
    # ─── 2. Firefox kurulu mu? ───
    gecko_path = os.path.join(drivers_dir, f"geckodriver{ext}")
    if os.path.exists(gecko_path):
        try:
            test_driver = _make_firefox_driver(gecko_path)
            test_driver.quit()
            ACTIVE_BROWSER = "firefox"
            return "firefox"
        except Exception:
            pass
    
    print(f"{RED}[!] Hiçbir tarayıcı başlatılamadı{RESET}")
    return None

def _make_chrome_driver():
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    options = ChromeOptions()
    options.page_load_strategy = "eager"
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--mute-audio")
    options.add_argument("--no-first-run")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def _make_firefox_driver(gecko_path):
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.firefox.service import Service as FirefoxService
    options = FirefoxOptions()
    options.page_load_strategy = "eager"
    options.add_argument("-headless")
    options.set_preference("general.useragent.override",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0")
    options.set_preference("permissions.default.image", 2)   # Resimleri yükleme
    options.set_preference("media.volume_scale", "0.0")
    service = FirefoxService(executable_path=gecko_path)
    return webdriver.Firefox(service=service, options=options)

def get_smart_driver():
    global ACTIVE_BROWSER
    
    base = os.path.dirname(os.path.abspath(__file__))
    drivers_dir = os.path.join(base, "drivers")
    ext = ".exe" if platform.system() == "Windows" else ""
    
    if ACTIVE_BROWSER == "chrome":
        try:
            return _make_chrome_driver()
        except Exception:
            pass
    elif ACTIVE_BROWSER == "firefox":
        gecko_path = os.path.join(drivers_dir, f"geckodriver{ext}")
        if os.path.exists(gecko_path):
            try:
                return _make_firefox_driver(gecko_path)
            except Exception:
                pass
    
    # Hiçbiri yoksa fallback (nadir durum)
    return None

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
from multiprocessing import Pool

def get_worker_count():
    total_gb = None

    # 1) psutil varsa en doğru bilgi
    try:
        import psutil
        total_gb = psutil.virtual_memory().total / (1024 ** 3)
    except ImportError:
        pass

    # 2) psutil yoksa platforma göre tahmin
    if total_gb is None:
        system = platform.system()
        if system == "Darwin":       # macOS genelde 8+ GB
            total_gb = 8
        elif system == "Windows":
            total_gb = 8
        elif system == "Linux":
            total_gb = 4              # muhafazakâr varsayım
        else:
            total_gb = 4

    # 3) RAM'e göre worker
    if total_gb >= 16:
        workers = 6
    elif total_gb >= 12:
        workers = 5
    elif total_gb >= 8:
        workers = 4
    elif total_gb >= 6:
        workers = 3
    elif total_gb >= 4:
        workers = 2
    else:
        workers = 1                   # 2 GB ve altı → tek process

    print(f"{BLUE}[i] Sistem RAM: ~{total_gb:.1f} GB → {workers} paralel worker{RESET}")
    return workers

def check_one_mp(args):
    name, variant, url = args
    driver = None
    try:
        if not ACTIVE_BROWSER:
            detect_browser()
        driver = get_smart_driver()
        if not driver:
            return None
        result = check_selenium_profile(driver, url)
        return (name, variant, url) if result else None
    except Exception:
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

def _init_worker():
    detect_browser()

def parallel_scan(tasks, workers=3):
    results = []
    with Pool(processes=workers, initializer=_init_worker) as pool:
        for r in tqdm(pool.imap_unordered(check_one_mp, tasks),
                      total=len(tasks), desc="[+] Tarıyor", colour="green"):
            if r:
                results.append(r)
                tqdm.write(f"{GREEN}[+] {r[0]} ({r[1]}): Link Found! --> {r[2]}{RESET}")
    return results

def check_selenium_profile(driver, url):
    try:
        driver.set_page_load_timeout(12)
        try:
            driver.get(url)
            try:
                # DOM hazır olana kadar bekle (resim, CSS, iframe bekleme)
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
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

        time.sleep(1.2)

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
    # ═══════════════════════════════════════════════════════
    # SOSYAL MEDYA
    # ═══════════════════════════════════════════════════════
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
            "page not found • instagram",
        ],
        "ok_signals": [
            "followers", "takipçi", "posts", "gönderi", "following", "takip",
            "see instagram photos and videos",
        ],
        "og_type": "profile",
        "blocked_titles": ["page not found • instagram"],
    },
    "threads.net": {
        "login_urls": ["/login", "/accounts/login"],
        "not_found": [
            "üzgünüz, bu sayfa kullanılamıyor", "üzgünüz, bu içerik kullanılamıyor",
            "bu sayfa mevcut değil", "kullanıcı bulunamadı", "sayfa bulunamadı",
            "sorry, this page isn't available", "this page isn't available",
            "sorry, this content isn't available", "user not found", "page not found",
        ],
        "ok_signals": ["followers", "takipçi", "threads", "following", "takip"],
        "og_type": "profile",
        "blocked_titles": ["threads", "threads • giriş yap"],
    },
    "threads.com": {
        "login_urls": ["/login", "/accounts/login"],
        "not_found": [
            "üzgünüz, bu sayfa kullanılamıyor", "üzgünüz, bu içerik kullanılamıyor",
            "bu sayfa mevcut değil", "kullanıcı bulunamadı", "sayfa bulunamadı",
            "sorry, this page isn't available", "user not found", "page not found",
        ],
        "ok_signals": ["followers", "takipçi", "threads", "following", "takip"],
        "og_type": "profile",
        "blocked_titles": ["threads", "threads • giriş yap"],
    },
    "twitter.com": {
        "login_urls": ["/i/flow/login", "/login", "/i/flow/signup"],
        "not_found": [
            "this account doesn't exist", "bu hesap mevcut değil",
            "account doesn't exist", "hesap bulunamadı",
            "hmm...this page doesn't exist", "bu sayfa mevcut değil",
            "neler olduğunu gör", "aşağıdaki seçeneği seçin",
            "telefon ile devam et", "google ile devam et", "apple ile devam et",
            "see what's happening", "sign in to x", "sign in to twitter",
            "hesap oluştur", "log in",
        ],
        "ok_signals": ["followers", "takipçi", "following", "tweets", "gönderi"],
        "blocked_titles": [
            "x. it's what's happening",
            "twitter. it's what's happening",
            "neler oluyor",
        ],
        "og_type": None,
    },
    "x.com": {
        "login_urls": ["/i/flow/login", "/login", "/i/flow/signup"],
        "not_found": [
            "this account doesn't exist", "bu hesap mevcut değil",
            "neler olduğunu gör", "aşağıdaki seçeneği seçin",
            "telefon ile devam et", "google ile devam et", "apple ile devam et",
            "see what's happening", "sign in to x",
        ],
        "ok_signals": ["followers", "following", "tweets"],
        "blocked_titles": ["x. it's what's happening"],
        "og_type": None,
    },
    "tiktok.com": {
        "login_urls": ["/login"],
        "not_found": [
            "couldn't find this account", "bu hesabı bulamadık",
            "sayfa mevcut değil", "page not available", "video currently unavailable",
            "this user doesn't exist", "bu kullanıcı mevcut değil",
        ],
        "ok_signals": ["followers", "takipçi", "likes", "beğeni", "following", "videos"],
        "og_type": None,
    },
    "linkedin.com": {
        "login_urls": ["/login", "/signup", "/uas/login"],
        "not_found": [
            "page not found", "sayfa bulunamadı", "profile not found",
            "this page doesn't exist", "bu sayfa mevcut değil",
            "bu profil bulunamadı", "profile not found",
        ],
        "ok_signals": ["connections", "bağlantı", "followers", "takipçi", "experience"],
        "og_type": "profile",
        "blocked_titles": ["linkedin: log in or sign up", "giriş yap", "sign up"],
    },
    "pinterest.com": {
        "login_urls": ["/login"],
        "not_found": [
            "user not found", "kullanıcı bulunamadı", "page not found",
            "sayfa bulunamadı", "sorry! we couldn't find that user",
        ],
        "ok_signals": ["followers", "takipçi", "pins", "following", "boards"],
        "og_type": "profile",
    },
    "tumblr.com": {
        "login_urls": [],
        "not_found": [
            "there's nothing here", "burada hiçbir şey yok",
            "not found", "sayfa bulunamadı", "page not found",
            "whatever you were looking for doesn't exist",
            "blog not found", "there's nothing here yet",
        ],
        "ok_signals": ["posts", "followers", "gönderi", "following", "takipçi", "reblog"],
        "og_type": "profile",
        "blocked_titles": ["tumblr", "untitled"],
    },
    "snapchat.com": {
        "login_urls": ["/login", "/accounts/login"],
        "not_found": [
            "üzgünüz, bu içerik bulunamadı", "bu içerik bulunamadı",
            "üzgünüz", "kullanıcı bulunamadı",
            "this username does not exist", "sorry, we couldn't find that user",
            "user not found", "content not found", "sorry, this content couldn't be found",
        ],
        "ok_signals": ["bitmoji", "snapcode", "hikaye", "story", "arkadaş ekle"],
        "og_type": None,
    },
    "t.me": {
        "login_urls": [],
        "not_found": [
            "sorry, this username is invalid", "kullanıcı adı geçersiz",
        ],
        "ok_signals": ["telegram", "members", "üye", "subscribers", "abone", "preview"],
        "og_type": None,
        "require_og_title_not": ["telegram", "telegram messenger"],
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
            "sorry. unless you've got a time machine",
            "channel not found", "this channel is currently unavailable",
            "bir zaman makinesine sahip değilseniz",
            "bu içerik artık ulaşılamaz", "üzgünüz. bir zaman makinesine",
            "kanal mevcut değil", "bu kanal şu anda kullanılamıyor",
        ],
        "ok_signals": ["followers", "takipçi", "follow", "viewers"],
        "og_type": None,
        "require_og_title_not": ["twitch"],
    },
    "youtube.com": {
        "login_urls": [],
        "not_found": [
            "this channel doesn't exist", "this page isn't available",
            "bu kanal mevcut değil", "bu sayfa kullanılamıyor",
            "404 - youtube", "channel not found",
        ],
        "ok_signals": ["subscriber", "abone", "video", "kanal", "channel"],
        "og_type": None,
    },
    "vk.com": {
        "login_urls": ["/login"],
        "not_found": ["page not found", "sayfa bulunamadı", "страница не найдена"],
        "ok_signals": ["followers", "friends", "arkadaş", "подписчики", "друзья"],
        "og_type": "profile",
    },

    # ═══════════════════════════════════════════════════════
    # VİDEO / FOTOĞRAF / YARATICI
    # ═══════════════════════════════════════════════════════
    "vimeo.com": {
        "login_urls": ["/log_in", "/login", "/join"],
        "not_found": [
            "sorry, we couldn't find that page",
            "we couldn't find that page",
            "make sure you've typed the url correctly",
            "page not found", "sayfa bulunamadı", "bu sayfa bulunamadı",
        ],
        "ok_signals": ["followers", "takipçi", "videos", "following", "videolar", "likes"],
        "og_type": "profile",
        "blocked_titles": ["vimeo"],
    },
    "flickr.com": {
        "login_urls": ["/signin", "/login"],
        "not_found": [
            "this user is not available", "kullanıcı bulunamadı",
            "page not found", "sayfa bulunamadı",
            "sorry, we can't find that page",
        ],
        "ok_signals": ["photos", "followers", "takipçi", "following", "fotolar"],
        "og_type": "profile",
    },
    "deviantart.com": {
        "login_urls": ["/users/login", "/join"],
        "not_found": [
            "page not found", "sayfa bulunamadı",
            "the page you're looking for doesn't exist",
            "sorry, this page isn't available",
        ],
        "ok_signals": ["watchers", "followers", "deviations", "takipçi", "gallery"],
        "og_type": "profile",
    },
    "behance.net": {
        "login_urls": ["/login", "/signup"],
        "not_found": [
            "page not found", "sayfa bulunamadı",
            "we couldn't find that page", "404",
        ],
        "ok_signals": ["followers", "takipçi", "projects", "appreciations", "following"],
        "og_type": "profile",
    },
    "dribbble.com": {
        "login_urls": ["/session/new", "/signup"],
        "not_found": ["page not found", "sayfa bulunamadı", "404", "not found"],
        "ok_signals": ["followers", "takipçi", "shots", "likes", "following"],
        "og_type": "profile",
    },
    "imgur.com": {
        "login_urls": ["/signin", "/register"],
        "not_found": [
            "not found", "user not found", "kullanıcı bulunamadı",
            "this user does not exist", "page not found",
        ],
        "ok_signals": ["posts", "followers", "takipçi", "comments", "gönderi"],
        "og_type": None,
    },
    "giphy.com": {
        "login_urls": ["/login", "/join"],
        "not_found": ["not found", "page not found", "404", "bu sayfa bulunamadı"],
        "ok_signals": ["followers", "takipçi", "gifs", "following", "views"],
        "og_type": None,
    },

    # ═══════════════════════════════════════════════════════
    # GELİŞTİRİCİ / KOD
    # ═══════════════════════════════════════════════════════
    "github.com": {
        "login_urls": [],
        "not_found": ["page not found", "sayfa bulunamadı", "404"],
        "ok_signals": ["repositories", "followers", "following", "depo", "takipçi"],
        "og_type": "profile",
    },
    "gitlab.com": {
        "login_urls": ["/users/sign_in"],
        "not_found": [
            "the page could not be found", "404", "page not found",
            "sayfa bulunamadı",
        ],
        "ok_signals": ["followers", "projects", "activity", "takipçi", "contributions"],
        "og_type": "profile",
    },
    "bitbucket.org": {
        "login_urls": ["/account/signin"],
        "not_found": ["404", "not found", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["repositories", "followers", "workspace", "takipçi"],
        "og_type": "profile",
    },
    "stackoverflow.com": {
        "login_urls": ["/users/login"],
        "not_found": [
            "page not found", "user not found", "kullanıcı bulunamadı",
            "sayfa bulunamadı", "this user doesn't exist",
        ],
        "ok_signals": ["reputation", "badges", "questions", "answers", "itibar"],
        "og_type": None,
    },
    "dev.to": {
        "login_urls": ["/enter", "/users/sign_in"],
        "not_found": ["404", "not found", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["followers", "posts", "articles", "takipçi", "following"],
        "og_type": "profile",
    },
    "hackerrank.com": {
        "login_urls": ["/login", "/auth/login"],
        "not_found": [
            "page not found", "couldn't find", "user not found",
            "sayfa bulunamadı", "kullanıcı bulunamadı",
        ],
        "ok_signals": ["followers", "badges", "score", "takipçi", "submissions"],
        "og_type": None,
    },
    "leetcode.com": {
        "login_urls": ["/accounts/login"],
        "not_found": [
            "page not found", "user doesn't exist", "not found",
            "sayfa bulunamadı", "kullanıcı bulunamadı",
        ],
        "ok_signals": ["submissions", "reputation", "followers", "solved", "takipçi"],
        "og_type": None,
    },
    "codewars.com": {
        "login_urls": ["/users/sign_in"],
        "not_found": [
            "404", "we couldn't find", "page not found", "sayfa bulunamadı",
        ],
        "ok_signals": ["kata", "rank", "honor", "followers", "takipçi"],
        "og_type": None,
    },
    "hub.docker.com": {
        "login_urls": ["/login", "/u/login"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["repositories", "stars", "pulls", "takipçi"],
        "og_type": None,
    },
    "pypi.org": {
        "login_urls": ["/account/login"],
        "not_found": ["404", "not found", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["projects", "packages", "releases"],
        "og_type": None,
    },
    "npmjs.com": {
        "login_urls": ["/login"],
        "not_found": ["404", "not found", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["packages", "followers", "takipçi", "downloads"],
        "og_type": None,
    },
    "rubygems.org": {
        "login_urls": ["/login", "/sign_in"],
        "not_found": [
            "page not found", "couldn't find", "not found",
            "sayfa bulunamadı", "kullanıcı bulunamadı",
        ],
        "ok_signals": ["gems", "downloads", "followers", "takipçi"],
        "og_type": None,
    },
    "codepen.io": {
        "login_urls": ["/login", "/signup"],
        "not_found": ["404", "page not found", "not found", "sayfa bulunamadı"],
        "ok_signals": ["pens", "followers", "hearts", "takipçi", "following"],
        "og_type": "profile",
    },
    "replit.com": {
        "login_urls": ["/login", "/signup"],
        "not_found": [
            "404", "not found", "user not found",
            "kullanıcı bulunamadı", "sayfa bulunamadı",
        ],
        "ok_signals": ["followers", "repls", "takipçi", "following"],
        "og_type": "profile",
    },
    "keybase.io": {
        "login_urls": ["/login"],
        "not_found": ["not found", "user not found", "kullanıcı bulunamadı", "404"],
        "ok_signals": ["proofs", "followers", "bitcoin", "takipçi", "pgp"],
        "og_type": None,
    },
    "gravatar.com": {
        "login_urls": ["/connect"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["profile", "photos", "profile photo"],
        "og_type": None,
    },
    "pastebin.com": {
        "login_urls": ["/login"],
        "not_found": ["not found", "404", "user not found", "kullanıcı bulunamadı"],
        "ok_signals": ["pastes", "followers", "takipçi"],
        "og_type": None,
    },
    "hackerone.com": {
        "login_urls": ["/users/sign_in"],
        "not_found": ["not found", "404", "user not found", "kullanıcı bulunamadı"],
        "ok_signals": ["reputation", "reports", "followers", "itibar", "takipçi"],
        "og_type": "profile",
    },
    "bugcrowd.com": {
        "login_urls": ["/login"],
        "not_found": ["not found", "404", "user not found", "kullanıcı bulunamadı"],
        "ok_signals": ["reputation", "points", "rank", "itibar"],
        "og_type": "profile",
    },
    "angel.co": {
        "login_urls": ["/login", "/signup"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["followers", "investments", "takipçi"],
        "og_type": "profile",
    },
    "crunchbase.com": {
        "login_urls": ["/login", "/register"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["investments", "followers", "takipçi", "experience"],
        "og_type": "profile",
    },
    "xing.com": {
        "login_urls": ["/login", "/signup"],
        "not_found": [
            "not found", "404", "kullanıcı bulunamadı",
            "sayfa bulunamadı", "profil bulunamadı",
        ],
        "ok_signals": ["followers", "contacts", "takipçi", "bağlantı"],
        "og_type": "profile",
    },

    # ═══════════════════════════════════════════════════════
    # OYUN
    # ═══════════════════════════════════════════════════════
    "steamcommunity.com": {
        "login_urls": [],
        "not_found": [
            "the specified profile could not be found",
            "belirtilen profil bulunamadı",
        ],
        "ok_signals": ["games", "oyun", "friends", "arkadaş", "badges"],
        "og_type": "profile",
    },
    "xboxgamertag.com": {
        "login_urls": [],
        "not_found": [
            "not found", "no results", "404",
            "sonuç bulunamadı", "kullanıcı bulunamadı",
        ],
        "ok_signals": ["gamerscore", "achievements", "friends", "arkadaş", "games"],
        "og_type": None,
    },
    "psnprofiles.com": {
        "login_urls": ["/login"],
        "not_found": [
            "not found", "could not find", "404",
            "kullanıcı bulunamadı", "sayfa bulunamadı",
        ],
        "ok_signals": ["trophies", "level", "games", "friends", "arkadaş"],
        "og_type": None,
    },
    "nintendo-master.com": {
        "login_urls": ["/login"],
        "not_found": ["not found", "no profile", "404", "kullanıcı bulunamadı"],
        "ok_signals": ["games", "friends", "arkadaş", "oyun"],
        "og_type": None,
    },
    "epicgames.com": {
        "login_urls": ["/id/login", "/login"],
        "not_found": [
            "page not found", "user not found", "404",
            "kullanıcı bulunamadı", "sayfa bulunamadı",
        ],
        "ok_signals": ["friends", "arkadaş", "games"],
        "og_type": None,
    },
    "roblox.com": {
        "login_urls": ["/login"],
        "not_found": [
            "not found", "user not found", "404",
            "kullanıcı bulunamadı", "sayfa bulunamadı",
        ],
        "ok_signals": ["friends", "arkadaş", "followers", "takipçi"],
        "og_type": None,
    },
    "namemc.com": {
        "login_urls": ["/login"],
        "not_found": [
            "not found", "no player", "404",
            "kullanıcı bulunamadı", "oyuncu bulunamadı",
        ],
        "ok_signals": ["profile", "history", "geçmiş"],
        "og_type": None,
    },

    # ═══════════════════════════════════════════════════════
    # MÜZİK / PODCAST
    # ═══════════════════════════════════════════════════════
    "spotify.com": {
        "login_urls": ["/login"],
        "not_found": ["page not found", "sayfa bulunamadı", "couldn't find"],
        "ok_signals": ["followers", "takipçi", "playlists", "public playlists"],
        "og_type": "profile",
    },
    "soundcloud.com": {
        "login_urls": ["/signin", "/login"],
        "not_found": [
            "we can't find that user", "kullanıcı bulunamadı",
            "404", "page not found",
        ],
        "ok_signals": ["followers", "takipçi", "tracks", "parça", "following"],
        "og_type": "profile",
    },
    "mixcloud.com": {
        "login_urls": ["/login", "/signup"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["followers", "takipçi", "mixes", "following"],
        "og_type": "profile",
    },
    "bandcamp.com": {
        "login_urls": ["/login", "/signup"],
        "not_found": [
            "not found", "404", "page not found",
            "sayfa bulunamadı", "bu sayfa bulunamadı",
        ],
        "ok_signals": ["followers", "takipçi", "tracks", "following", "collection"],
        "og_type": "profile",
    },
    "shazam.com": {
        "login_urls": ["/login", "/signin"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["followers", "takipçi", "songs", "shazams"],
        "og_type": "profile",
    },
    "last.fm": {
        "login_urls": ["/login", "/join"],
        "not_found": [
            "not found", "404", "user not found",
            "kullanıcı bulunamadı", "page not found",
        ],
        "ok_signals": ["scrobbles", "followers", "takipçi", "following", "artists"],
        "og_type": "profile",
    },

    # ═══════════════════════════════════════════════════════
    # BLOG / YAYINCILIK
    # ═══════════════════════════════════════════════════════
    "medium.com": {
        "login_urls": [],
        "not_found": [
            "404", "out of nothing, something",
            "page not found", "sayfa bulunamadı",
        ],
        "ok_signals": ["followers", "takipçi", "following", "stories"],
        "og_type": "profile",
    },
    "wordpress.com": {
        "login_urls": [],
        "not_found": [
            "doesn't exist", "not found", "404",
            "bu site mevcut değil", "sayfa bulunamadı",
            "the site you're looking for doesn't exist",
            "we couldn't find that site",
        ],
        "ok_signals": ["followers", "posts", "takipçi", "gönderi", "following"],
        "og_type": "website",   # WordPress blogu website olarak işaretlenir
        "blocked_titles": ["wordpress.com", "wordpress"],
    },
    "blogspot.com": {
        "login_urls": [],
        "not_found": [
            "not found", "404", "blog not found",
            "bu blog bulunamadı", "sayfa bulunamadı",
        ],
        "ok_signals": ["posts", "followers", "gönderi", "takipçi"],
        "og_type": None,
    },
    "ghost.io": {
        "login_urls": ["/login", "/signin"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["posts", "followers", "gönderi", "takipçi"],
        "og_type": None,
    },
    "write.as": {
        "login_urls": ["/login", "/signin"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["posts", "followers", "gönderi", "takipçi"],
        "og_type": None,
    },
    "substack.com": {
        "login_urls": ["/signin", "/login"],
        "not_found": [
            "not found", "404", "page not found",
            "sayfa bulunamadı", "publication not found",
            "we couldn't find that page",
        ],
        "ok_signals": ["subscribers", "posts", "abone", "gönderi", "following"],
        "og_type": "website",
        "blocked_titles": ["substack"],
    },
    "about.me": {
        "login_urls": ["/login", "/signup"],
        "not_found": [
            "not found", "404", "page not found",
            "sayfa bulunamadı", "this page doesn't exist",
        ],
        "ok_signals": ["followers", "takipçi", "bio", "hakkında"],
        "og_type": "profile",
    },
    "rebelmouse.com": {
        "login_urls": ["/login"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["posts", "followers", "gönderi", "takipçi"],
        "og_type": None,
    },
    "scribd.com": {
        "login_urls": ["/login"],
        "not_found": [
            "not found", "404", "page not found",
            "sayfa bulunamadı", "kullanıcı bulunamadı",
        ],
        "ok_signals": ["followers", "documents", "takipçi", "belge"],
        "og_type": "profile",
    },
    "slideshare.net": {
        "login_urls": ["/login", "/signup"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["followers", "presentations", "takipçi", "sunum"],
        "og_type": "profile",
    },
    "hubpages.com": {
        "login_urls": ["/login"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["followers", "hubs", "takipçi", "articles"],
        "og_type": "profile",
    },
    "quora.com": {
        "login_urls": ["/login"],
        "not_found": ["page not found", "we couldn't find", "sayfa bulunamadı"],
        "ok_signals": ["followers", "answers", "questions", "yanıt", "takipçi"],
        "og_type": "profile",
    },
    "couchsurfing.com": {
        "login_urls": ["/login", "/signup"],
        "not_found": [
            "not found", "404", "profile not found",
            "sayfa bulunamadı", "kullanıcı bulunamadı",
        ],
        "ok_signals": ["friends", "references", "arkadaş", "takipçi"],
        "og_type": None,
    },

    # ═══════════════════════════════════════════════════════
    # NFT / BLOKZİNCİR
    # ═══════════════════════════════════════════════════════
    "opensea.io": {
        "login_urls": ["/login"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["collections", "followers", "items", "takipçi"],
        "og_type": "profile",
    },
    "rarible.com": {
        "login_urls": ["/login"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["items", "followers", "takipçi", "collections"],
        "og_type": "profile",
    },

    # ═══════════════════════════════════════════════════════
    # AKADEMİK
    # ═══════════════════════════════════════════════════════
    "researchgate.net": {
        "login_urls": ["/login", "/signup"],
        "not_found": [
            "not found", "404", "page not found",
            "sayfa bulunamadı", "profile not found",
        ],
        "ok_signals": ["publications", "followers", "takipçi", "citations", "following"],
        "og_type": "profile",
    },
    "academia.edu": {
        "login_urls": ["/login", "/signup"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["papers", "followers", "takipçi", "following"],
        "og_type": "profile",
    },
    "orcid.org": {
        "login_urls": ["/signin", "/signin"],
        "not_found": [
            "not found", "404", "page not found",
            "sayfa bulunamadı", "record not found",
        ],
        "ok_signals": ["works", "employment", "education", "yayın", "eğitim"],
        "og_type": "profile",
    },

    # ═══════════════════════════════════════════════════════
    # TÜRKİYE'YE ÖZEL
    # ═══════════════════════════════════════════════════════
    "eksisozluk.com": {
        "login_urls": ["/giris"],
        "not_found": [
            "böyle bir yazar bulunamadı",
            "sayfa bulunamadı", "404",
            "kullanıcı bulunamadı",
        ],
        "ok_signals": ["entry", "takipçi", "yazar", "favori"],
        "og_type": None,
    },
    "forum.donanimhaber.com": {
        "login_urls": ["/login"],
        "not_found": [
            "kullanıcı bulunamadı", "sayfa bulunamadı",
            "hata", "404", "böyle bir kullanıcı yok",
        ],
        "ok_signals": ["mesaj", "konu", "takipçi", "profil"],
        "og_type": None,
    },
    "kizlarsoruyor.com": {
        "login_urls": ["/giris", "/login"],
        "not_found": [
            "kullanıcı bulunamadı", "sayfa bulunamadı",
            "404", "profil bulunamadı", "böyle bir kullanıcı yok",
            "aradığınız kullanıcı bulunamadı",
        ],
        "ok_signals": ["soru", "cevap", "takipçi", "profil", "beğeni"],
        "og_type": "profile",
        "blocked_titles": ["kizlarsoruyor", "kızlar soruyor"],
    },

    # ═══════════════════════════════════════════════════════
    # KENAR / ESKİ
    # ═══════════════════════════════════════════════════════
    "voat.co": {
        "login_urls": ["/login"],
        "not_found": ["not found", "404", "page not found", "sayfa bulunamadı"],
        "ok_signals": ["submissions", "comments", "karma"],
        "og_type": None,
    },
    "8kun.top": {
        "login_urls": [],
        "not_found": ["not found", "404", "page not found"],
        "ok_signals": ["posts", "threads", "replies"],
        "og_type": None,
    },
    "producthunt.com": {
        "login_urls": ["/login", "/signup"],
        "not_found": [
            "not found", "404", "page not found",
            "sayfa bulunamadı", "we couldn't find that page",
            "user not found", "kullanıcı bulunamadı",
        ],
        "ok_signals": ["followers", "upvotes", "takipçi", "following", "maker"],
        "og_type": "profile",
        "blocked_titles": ["product hunt", "producthunt"],
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
    #{ "name": "Discord", "url": "https://discord.com/users/{user}", "engine": "selenium" },
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

def offer_auto_install():
    system = platform.system()
    
    print(f"\n{BLUE}[?] Firefox otomatik kurulsun mu? (E/H): {RESET}", end="")
    choice = input().strip().lower()
    if choice not in ['e', 'evet', 'y', 'yes']:
        return False
    
    try:
        if system == "Windows":
            print(f"{YELLOW}[!] Firefox kuruluyor (winget)...{RESET}")
            result = subprocess.run(
                ["winget", "install", "-e", "--id", "Mozilla.Firefox"],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                print(f"{GREEN}[+] Firefox kuruldu! Programı yeniden başlat.{RESET}")
                return True
            else:
                print(f"{RED}[!] Kurulum başarısız. Manuel kur: winget install Mozilla.Firefox{RESET}")
        elif system == "Darwin":
            print(f"{YELLOW}[!] Firefox kuruluyor (brew)...{RESET}")
            result = subprocess.run(
                ["brew", "install", "--cask", "firefox"],
                capture_output=True, text=True, timeout=600
            )
            if result.returncode == 0:
                print(f"{GREEN}[+] Firefox kuruldu!{RESET}")
                return True
        time.sleep(2)
    except FileNotFoundError:
        print(f"{RED}[!] Paket yöneticisi bulunamadı (winget/brew){RESET}")
        time.sleep(2)
    except Exception as e:
        print(f"{RED}[!] Kurulum hatası: {e}{RESET}")
        time.sleep(2)
    
    return False

def print_browser_help():
    system = platform.system()
    
    print(f"\n{RED}╔══════════════════════════════════════════════════════╗{RESET}")
    print(f"{RED}║  TARAYICI BULUNAMADI                                 ║{RESET}")
    print(f"{RED}╚══════════════════════════════════════════════════════╝{RESET}")
    print(f"\n{YELLOW}Bu program Chrome veya Firefox tarayıcılarından{RESET}")
    print(f"{YELLOW}en az birine ihtiyaç duyar. Sisteminizde hiçbiri kurulu değil.{RESET}")
    
    print(f"\n{BLUE}━━━ Nasıl kurulur? ━━━{RESET}\n")
    
    if system == "Windows":
        print(f"{GREEN}Windows'ta (PowerShell):{RESET}")
        print(f"  {BLUE}winget install Google.Chrome{RESET}       (Önerilen - hızlı)")
        print(f"  {BLUE}winget install Mozilla.Firefox{RESET}     (ARM uyumlu)")
        print(f"  {BLUE}winget install Microsoft.Edge{RESET}      (Windows'ta genelde hazır)")
    elif system == "Darwin":
        print(f"{GREEN}macOS'ta (Terminal):{RESET}")
        print(f"  {BLUE}brew install --cask firefox{RESET}       (Önerilen - hızlı, hafif)")
        print(f"  {BLUE}brew install --cask google-chrome{RESET}")
    elif system == "Linux":
        print(f"{GREEN}Linux'ta:{RESET}")
        print(f"  {BLUE}sudo apt install chromium-browser{RESET}   (Debian/Ubuntu)")
        print(f"  {BLUE}sudo dnf install chromium{RESET}          (Fedora)")
        print(f"  {BLUE}sudo pacman -S chromium{RESET}            (Arch)")
    else:
        print(f"{GREEN}Tarayıcı kur:{RESET}")
        print(f"  Chrome, Edge veya Firefox'tan birini kur")
    
    print(f"\n{BLUE}━━━ Kurulum sonrası ━━━{RESET}")
    print(f"  Programı yeniden başlat — driver otomatik inecek.\n")
    
    print(f"{YELLOW}[i] Not: Windows ARM için Mozilla Firefox önerilir.{RESET}")
    print(f"{YELLOW}    Edge ARM'da headless mod bazen sorun çıkarır.{RESET}\n")

    if offer_auto_install():
        sys.exit(0)

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
        elif secim == 2:
            target_urls = urls
        else:
            pass
    except NameError:
        return 0

    tasks = []
    for variant in variants:
        for url_item in target_urls:
            engine = url_item.get("engine", "requests")
            if engine == "selenium":
                tasks.append((
                    url_item["name"],
                    variant,
                    url_item["url"].format(user=variant)
                ))
                
    # ─── Tarayıcı kontrolü ───
    ensure_all_drivers()
    
    browser = detect_browser()
    if not browser:
        print_browser_help()
        input(f"\n{BLUE}Ana menüye dönmek için ENTER'a bas...{RESET}")
        return
    
    # ─── Paralel tarama ───
    results = parallel_scan(tasks, workers=get_worker_count())
    # ─── 3) Bulunanları kaydet ───
    for name, variant, url in results:
        found_links.append((f"{name} ({variant})", url))

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
    ciktilar = set()
    username = name
    username_en = tr_to_en(name)

    for base in [username, username_en]:
        no_space = base.replace(' ', '')
        with_dot = base.replace(' ', '.')
        with_us  = base.replace(' ', '_')

        # Düz varyantlar
        ciktilar.add(no_space)
        ciktilar.add(with_dot)
        ciktilar.add(with_us)

        # Baş/son "_" ile
        ciktilar.add(f"_{no_space}_")
        ciktilar.add(f"_{with_dot}_")
        ciktilar.add(f"_{with_us}_")

        # Baş/son "_", orta "_" veya "." (nokta BAŞA/SONA değil, sadece ORTAYA)
        ciktilar.add(f"_{no_space}_")
        ciktilar.add(f"_{with_dot}_")

    return list(ciktilar)

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


if __name__ == "__main__":
    check_requirements()
    Start()