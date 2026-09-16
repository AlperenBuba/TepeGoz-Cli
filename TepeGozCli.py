import subprocess
import platform
import sys
import importlib.util

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[94m"
RESET = "\033[0m"

gecikme = 3

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

def check_selenium_profile(url):
    driver = None
    try:
        driver = get_smart_driver()
        if not driver:
            return False

        driver.get(url)
        
        # Sayfanın yüklenmesini bekle
        try:
            WebDriverWait(driver, gecikme).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception:
            pass 

        title = driver.title.lower()
        current_url = driver.current_url.lower()
        page_text = driver.page_source.lower()

        # 1. Eğer URL 404 sayfasına yönlendirildiyse veya ana sayfaya fırlattıysa kesinlikle yoktur
        if "404" in title or "not found" in title or "bulunamadı" in title:
            driver.quit()
            return False

        # 2. Bazı siteler (Instagram, Twitter vb.) olmayan kullanıcıyı login sayfasına veya ana sayfaya atar
        if "instagram.com" in url.lower() and ("accounts/login" in current_url or "giriş yap" in title):
            driver.quit()
            return False

        if "instagram.com" in url.lower():
            if "üzgünüz, bu sayfaya ulaşılamıyor" in page_text or "tıklandığın bağlantı bozuk olabilir" in page_text or "page not found" in page_text:
                driver.quit()
                return False

        if "instagram.com" in url.lower():
            try:
                # Hata mesajının DOM'a düşmesi için kısa bir süre (örn: 2 saniye) max bekle
                WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'ulaşılamıyor') or contains(text(), 'bozuk olabilir')]"))
                )
                # Eğer bu hata elementi bulunursa, hesap kesinlikle yoktur!
                driver.quit()
                return False
            except Exception:
                pass

        if "linkedin.com" in url.lower():
            if "linkedin.com/login" in current_url or "sign in" in title or "giriş yap" in title or "join linkedin" in page_text:
                driver.quit()
                return False

        if "reddit.com" in url.lower():
            if "kimse bu adı kullanmıyor" in page_text or "bu hesap yasaklanmış" in page_text or "not found" in page_text:
                driver.quit()
                return False

        if "github.com" in url.lower() and "sign in" in title:
            # GitHub profil varsa sign in olsa bile başlıkta kullanıcı adı görünür
            pass

        # Genel hata başlığı kontrolü
        error_titles = ["bulunamadı", "not found", "sayfa bulunamadı", "page not found", "error", "404"]
        for err in error_titles:
            if err in title and len(title) < 50: # Sadece başlık hata mesajından ibaretse
                driver.quit()
                return False

        driver.quit()
        return True
    except Exception:
        if driver:
            try:
                driver.quit()
            except:
                pass
        return False
    
found_links = []

Extra_characters = ["_", "."]

urls = [
    { "name": "Facebook", "url": "https://www.facebook.com/{user}", "engine": "selenium" },
    { "name": "Instagram", "url": "https://www.instagram.com/{user}/", "engine": "selenium" },
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
    { "name": "YouTube", "url": "https://www.youtube.com/@{user}", "engine": "selenium" },
    { "name": "TikTok", "url": "https://www.tiktok.com/@{user}", "engine": "selenium" },
    { "name": "GitHub", "url": "https://github.com/{user}", "engine": "requests" },
    { "name": "Spotify", "url": "https://open.spotify.com/user/{user}", "engine": "selenium" },
    { "name": "Twitter", "url": "https://twitter.com/{user}", "engine": "selenium" },
    { "name": "LinkedIn", "url": "https://www.linkedin.com/in/{user}", "engine": "selenium" },
    { "name": "Pinterest", "url": "https://www.pinterest.com/{user}/", "engine": "selenium" },
    { "name": "Tumblr", "url": "https://{user}.tumblr.com", "engine": "selenium" },
    { "name": "Snapchat", "url": "https://www.snapchat.com/add/{user}", "engine": "selenium" },
    { "name": "Telegram", "url": "https://t.me/{user}", "engine": "selenium" },
    { "name": "Discord", "url": "https://discord.com/users/{user}", "engine": "selenium" },
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
    if secim == 1:
        target_urls = popular_urls
        desc_text = "[+] Sosyal Medya Taranıyor"
    else:
        target_urls = urls
        desc_text = "[+] Tüm Siteler Taranıyor"

    total_steps = len(variants) * len(target_urls)
    with tqdm(total=total_steps, desc=desc_text, colour="green") as pbar:
        for variant in variants:
            for url_item in target_urls:
                name = url_item["name"]
                adress = url_item["url"].format(user=variant)
                engine = url_item.get("engine", "requests")
                if engine == "selenium":
                    if check_selenium_profile(adress):
                        tqdm.write(f"{BLUE}[+] {GREEN}{name} ({variant}): Link Found! --> {adress}")
                        found_links.append((name, adress))
                else:
                    pass
                pbar.update(1)
    fileCreator(username)


def versionCreator(name):
    ciktilar = []
    username = name

    for characters in Extra_characters:
        cikti = f"{username.replace(' ', '')}"
        ciktilar.append(cikti)

    for characters in Extra_characters:
        cikti = f"{username.replace(' ', characters)}"
        ciktilar.append(cikti)

    for characters in Extra_characters:
        cikti = f"{characters}{username.replace(' ', '')}{characters}"
        ciktilar.append(cikti)

    for characters in Extra_characters:
        cikti = f"{characters}{username.replace(' ', characters)}{characters}"
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