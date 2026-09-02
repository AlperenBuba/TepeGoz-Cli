
import subprocess
import platform
import sys
import importlib.util

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[94m"
RESET = "\033[0m"

def check_requirements():
    required_packages = ["requests", "selenium"]
    missing_packages = []

    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            missing_packages.append(package)

    if missing_packages:
        print(f"{RED}[!] Eksik paketler tespit edildi: {', '.join(missing_packages)}\n")
        print(f"{YELLOW}[!] Bağımlılıklar kuruluyor...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--break-system-packages"] + missing_packages)
    else:
        print(f"{GREEN}[+] Tüm bağımlılıklar eksiksiz.")
check_requirements()


import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def check_selenium_profile(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        driver.implicitly_wait(3)
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        
        # Genel hata kalıpları (farklı sitelerde ortak geçen yokluk ibareleri)
        error_phrases = [
            "tıkladığın bağlantı bozuk olabilir",
            "üzgünüz, bu sayfaya ulaşılamıyor",
            "page not found",
            "sorry, this page isn't available",
            "bulunamadı",
            "hesap bulunamadı",
            "üzgünüz, aradığın sayfa bulunamadı",
            "bu sayfa kullanılamıyor",
            "Başka bir şey aramayı deneyin",
            "özür dileriz",
            "bu sayfayı bulamıyoruz",
            "hay aksi",
            "we looked everywhere but couldn't find this page",
            "the page you're looking for doesn't exist."
            "not found", 
            "bulunamadı", 
            "doesn't exist", 
            "does not exist", 
            "hesap bulunamadı", 
            "bu sayfa mevcut değil", 
            "page not found",
            "user not found",
            "kullanıcı bulunamadı",
            "profile not found",
            "404",
            "tıkladığın bağlantı bozuk olabilir veya sayfa kaldırılmış olabilir.",
            "üzgünüz",
            "bu sayfaya ulaşılamıyor",
            "We can’t find that user.",
            "looks like this page evaded detection",
            "The requested page was not found",
            "Page no longer exists",
            "This account doesn’t exist",
            "ne yazık ki reddit’teki kimse bu adı kullanmıyor",
            "mesajlaşmada yeni bir çağ",
            "a new era of messaging",
            "the page you're looking for doesn't exist.",
            "Page no longer exists",
            "oops",
            "oops.",
            "bu hesap bulunamadı",
            "Bu sayfa kullanılamıyor. Özür dileriz. Başka bir şey aramayı deneyin.",
        ]
        
        for phrase in error_phrases:
            if phrase.lower() in body_text:
                driver.quit()
                return False
                
        driver.quit()
        return True
    except Exception:
        driver.quit()
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
    { "name": "Tumblr", "url": "https://{user}.tumblr.com", "engine": "requests" },
    { "name": "Snapchat", "url": "https://www.snapchat.com/add/{user}", "engine": "selenium" },
    { "name": "Telegram", "url": "https://t.me/{user}", "engine": "requests" },
    { "name": "Discord", "url": "https://discord.com/users/{user}", "engine": "selenium" },
    { "name": "Reddit", "url": "https://www.reddit.com/user/{user}", "engine": "selenium" },
    { "name": "Twitch", "url": "https://www.twitch.tv/{user}", "engine": "selenium" },
    { "name": "YouTube", "url": "https://www.youtube.com/@{user}", "engine": "selenium" },
    { "name": "Vimeo", "url": "https://vimeo.com/{user}", "engine": "requests" },
    { "name": "Flickr", "url": "https://www.flickr.com/people/{user}/", "engine": "requests" },
    { "name": "DeviantArt", "url": "https://www.deviantart.com/{user}", "engine": "requests" },
    { "name": "Behance", "url": "https://www.behance.net/{user}", "engine": "selenium" },
    { "name": "Dribbble", "url": "https://dribbble.com/{user}", "engine": "selenium" }, 
    { "name": "Medium", "url": "https://medium.com/@{user}", "engine": "selenium" },
    { "name": "VK", "url": "https://vk.com/{user}", "engine": "selenium" },
    { "name": "GitHub", "url": "https://github.com/{user}", "engine": "requests" },
    { "name": "GitLab", "url": "https://gitlab.com/{user}", "engine": "requests" },
    { "name": "Bitbucket", "url": "https://bitbucket.org/{user}/", "engine": "requests" },
    { "name": "Stack Overflow", "url": "https://stackoverflow.com/users/{user}", "engine": "requests" },
    { "name": "Dev.to", "url": "https://dev.to/{user}", "engine": "requests" },
    { "name": "HackerRank", "url": "https://www.hackerrank.com/{user}", "engine": "selenium" }, 
    { "name": "LeetCode", "url": "https://leetcode.com/{user}/", "engine": "selenium" },
    { "name": "CodeWars", "url": "https://www.codewars.com/users/{user}", "engine": "requests" },
    { "name": "Docker Hub", "url": "https://hub.docker.com/u/{user}", "engine": "selenium" }, 
    { "name": "PyPI", "url": "https://pypi.org/user/{user}/", "engine": "requests" },
    { "name": "NPM", "url": "https://www.npmjs.com/~{user}", "engine": "requests" },
    { "name": "RubyGems", "url": "https://rubygems.org/profiles/{user}", "engine": "requests" },
    { "name": "CodePen", "url": "https://codepen.io/{user}", "engine": "selenium" }, 
    { "name": "Replit", "url": "https://replit.com/@{user}", "engine": "selenium" },
    { "name": "Steam", "url": "https://steamcommunity.com/id/{user}", "engine": "selenium" },
    { "name": "Xbox", "url": "https://xboxgamertag.com/search/{user}", "engine": "requests" },
    { "name": "PlayStation", "url": "https://psnprofiles.com/{user}", "engine": "selenium" }, 
    { "name": "Nintendo", "url": "https://nintendo-master.com/profile/{user}", "engine": "requests" },
    { "name": "Epic Games", "url": "https://www.epicgames.com/id/{user}", "engine": "selenium" },
    { "name": "Roblox", "url": "https://www.roblox.com/user.aspx?username={user}", "engine": "selenium" },
    { "name": "Minecraft", "url": "https://namemc.com/profile/{user}", "engine": "selenium" }, 
    { "name": "Patreon", "url": "https://www.patreon.com/{user}", "engine": "selenium" },
    { "name": "Gumroad", "url": "https://gumroad.com/{user}", "engine": "selenium" }, 
    { "name": "Product Hunt", "url": "https://www.producthunt.com/@{user}", "engine": "selenium" },
    { "name": "Keybase", "url": "https://keybase.io/{user}", "engine": "requests" },
    { "name": "Gravatar", "url": "https://en.gravatar.com/{user}", "engine": "requests" },
    { "name": "Pastebin", "url": "https://pastebin.com/u/{user}", "engine": "selenium" }, 
    { "name": "HackerOne", "url": "https://hackerone.com/{user}", "engine": "selenium" },
    { "name": "Bugcrowd", "url": "https://bugcrowd.com/{user}", "engine": "selenium" },
    { "name": "AngelList", "url": "https://angel.co/u/{user}", "engine": "selenium" }, 
    { "name": "Crunchbase", "url": "https://www.crunchbase.com/person/{user}", "engine": "selenium" },
    { "name": "Xing", "url": "https://www.xing.com/profile/{user}", "engine": "selenium" }, 
    { "name": "WordPress", "url": "https://{user}.wordpress.com", "engine": "requests" },
    { "name": "Blogger", "url": "https://{user}.blogspot.com", "engine": "requests" },
    { "name": "Ghost", "url": "https://{user}.ghost.io", "engine": "requests" },
    { "name": "Write.as", "url": "https://write.as/{user}", "engine": "requests" },
    { "name": "Substack", "url": "https://{user}.substack.com", "engine": "requests" },
    { "name": "SoundCloud", "url": "https://soundcloud.com/{user}", "engine": "selenium" },
    { "name": "Mixcloud", "url": "https://www.mixcloud.com/{user}/", "engine": "selenium" }, 
    { "name": "Bandcamp", "url": "https://bandcamp.com/{user}", "engine": "requests" },
    { "name": "Spotify", "url": "https://open.spotify.com/user/{user}", "engine": "selenium" }, 
    { "name": "Shazam", "url": "https://www.shazam.com/artist/{user}", "engine": "selenium" }, 
    { "name": "Last.fm", "url": "https://www.last.fm/user/{user}", "engine": "requests" },
    { "name": "About.me", "url": "https://about.me/{user}", "engine": "requests" },
    { "name": "RebelMouse", "url": "https://www.rebelmouse.com/{user}", "engine": "requests" },
    { "name": "Scribd", "url": "https://www.scribd.com/{user}", "engine": "selenium" }, 
    { "name": "Slideshare", "url": "https://www.slideshare.net/{user}", "engine": "selenium" }, 
    { "name": "Imgur", "url": "https://imgur.com/user/{user}", "engine": "selenium" },
    { "name": "Giphy", "url": "https://giphy.com/{user}", "engine": "selenium" }, 
    { "name": "Couchsurfing", "url": "https://www.couchsurfing.com/people/{user}", "engine": "selenium" }, 
    { "name": "HubPages", "url": "https://hubpages.com/@{user}", "engine": "requests" },
    { "name": "Quora", "url": "https://www.quora.com/profile/{user}", "engine": "selenium" },
    { "name": "Voat", "url": "https://voat.co/user/{user}", "engine": "requests" },
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
    { "name": "Tumblr", "url": "https://{user}.tumblr.com", "engine": "requests" },
    { "name": "Snapchat", "url": "https://www.snapchat.com/add/{user}", "engine": "selenium" },
    { "name": "Telegram", "url": "https://t.me/{user}", "engine": "requests" },
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

def is_valid_profile(response):
    if response.status_code != 200:
        return False

    error_keywords = [
        "tıkladığın bağlantı bozuk olabilir",
        "üzgünüz, bu sayfaya ulaşılamıyor",
        "page not found",
        "sorry, this page isn't available",
        "bulunamadı",
        "hesap bulunamadı",
        "üzgünüz, aradığın sayfa bulunamadı",
        "bu sayfa kullanılamıyor",
        "Başka bir şey aramayı deneyin",
        "özür dileriz",
        "bu sayfayı bulamıyoruz",
        "hay aksi",
        "we looked everywhere but couldn't find this page",
        "the page you're looking for doesn't exist."
        "not found", 
        "bulunamadı", 
        "doesn't exist", 
        "does not exist", 
        "hesap bulunamadı", 
        "bu sayfa mevcut değil", 
        "page not found",
        "user not found",
        "kullanıcı bulunamadı",
        "profile not found",
        "404",
        "tıkladığın bağlantı bozuk olabilir veya sayfa kaldırılmış olabilir.",
        "üzgünüz",
        "bu sayfaya ulaşılamıyor",
        "We can’t find that user.",
        "looks like this page evaded detection",
        "the requested page was not found",
        "page no longer exists",
        "this account doesn’t exist",
        "ne yazık ki reddit’teki kimse bu adı kullanmıyor",
        "mesajlaşmada yeni bir çağ",
        "a new era of messaging",
        "the page you're looking for doesn't exist.",
        "Page no longer exists",
        "oops",
        "oops.",
        "bu hesap bulunamadı",
        "Bu sayfa kullanılamıyor. Özür dileriz. Başka bir şey aramayı deneyin."
    ]
    
    page_content = response.text.lower()
    
    for keyword in error_keywords:
        if keyword in page_content:
            return False
            
    return True



def Start():
    clear()
    print(menu_header)
    print(" 1. Social Media Scan\n 2. Scan all sites\n")
    try:
        secim = int(input(f" >{GREEN}"))
        if secim == 1:
            pass
        elif secim == 2:
            pass
        else:
            return 0
    except ValueError:
        return 0
    clear()
    print(menu_header)
    username = input(f" Enter the person's username:{GREEN} ")
    if username.strip() == "":
        return 0
    else:
        variants = versionCreator(username)
        for variant in variants:
            if secim == 1:
                easyFinder(variant)
            elif secim == 2:
                finder(variant)
            else:
                pass
        fileCreator(username)


def versionCreator(name):
    ciktilar = []
    username = name
    for characters in Extra_characters:
        cikti = f"{username.replace(' ', characters)}"
        ciktilar.append(cikti)

    for characters in Extra_characters:
        cikti = f"{characters}{username.replace(' ', '')}{characters}"
        ciktilar.append(cikti)

    for characters in Extra_characters:
        cikti = f"{characters}{username.replace(' ', characters)}{characters}"
        ciktilar.append(cikti)

    return ciktilar


def finder(user):
    for url in urls:
        name = url["name"]
        adress = url["url"].format(user=user)
        engine = url.get("engine", "requests")
        if engine == "requests":
            try:
                response = requests.get(adress, headers=headers, timeout=7, allow_redirects=True)
                if is_valid_profile(response):
                    print(f"{BLUE}[+] {GREEN}{name}: Link Found! --> {adress}")
                    found_links.append((name, adress))
                else:
                    pass 
            except requests.exceptions.Timeout:
                print(f"{RED}[!] {name}: Timeout (Site did not respond)")
            except requests.exceptions.ConnectionError:
                print(f"{YELLOW}[!] {name}: Connection error")
            except Exception as e:
                print(f"{RED}[!] {name}: An error occurred -> {e}")

        if engine == "selenium":
            if check_selenium_profile(adress):
                print(f"{BLUE}[+] {GREEN}{name}: Link Found! --> {adress}")
                found_links.append((name, adress))

def easyFinder(user):
    for url in popular_urls:
        name = url["name"]
        adress = url["url"].format(user=user)
        engine = url.get("engine", "requests")
        if engine == "requests":
            try:
                response = requests.get(adress, headers=headers, timeout=7, allow_redirects=True)
                if response.status_code == 200:
                    print(f"{BLUE}[+] {GREEN}{name}: Link Found! --> {adress}")
                    found_links.append((name, adress))
                else:
                    pass 
            except requests.exceptions.Timeout:
                print(f"{RED}[!] {name}: Timeout (Site did not respond)")
            except requests.exceptions.ConnectionError:
                print(f"{YELLOW}[!] {name}: Connection error")
            except Exception as e:
                print(f"{RED}[!] {name}: An error occurred -> {e}")

        if engine == "selenium":
            if check_selenium_profile(adress):
                print(f"{BLUE}[+] {GREEN}{name}: Link Found! --> {adress}")
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
        subprocess.call("cls")
    else:
        subprocess.call("clear")


Start()