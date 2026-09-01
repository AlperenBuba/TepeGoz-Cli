import subprocess
import platform
import requests

if platform.system() == "Windows":
    subprocess.call("cls")
else:
    subprocess.call("clear")

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[94m"
RESET = "\033[0m"

Extra_characters = ["_", "!", ""]

urls = [
            { "name": "Facebook", "url": "https://www.facebook.com/{user}" },
            { "name": "Instagram", "url": "https://www.instagram.com/{user}/" },
            { "name": "Twitter", "url": "https://twitter.com/{user}" },
            { "name": "TikTok", "url": "https://www.tiktok.com/@{user}" },
            { "name": "LinkedIn", "url": "https://www.linkedin.com/in/{user}" },
            { "name": "Pinterest", "url": "https://www.pinterest.com/{user}/" },
            { "name": "Tumblr", "url": "https://{user}.tumblr.com" },
            { "name": "Snapchat", "url": "https://www.snapchat.com/add/{user}" },
            { "name": "Telegram", "url": "https://t.me/{user}" },
            { "name": "Discord", "url": "https://discord.com/users/{user}" },
            { "name": "Reddit", "url": "https://www.reddit.com/user/{user}" },
            { "name": "Twitch", "url": "https://www.twitch.tv/{user}" },
            { "name": "YouTube", "url": "https://www.youtube.com/@{user}" },
            { "name": "Vimeo", "url": "https://vimeo.com/{user}" },
            { "name": "Flickr", "url": "https://www.flickr.com/people/{user}/" },
            { "name": "DeviantArt", "url": "https://www.deviantart.com/{user}" },
            { "name": "Behance", "url": "https://www.behance.net/{user}" },
            { "name": "Dribbble", "url": "https://dribbble.com/{user}" },
            { "name": "Medium", "url": "https://medium.com/@{user}" },
            { "name": "VK", "url": "https://vk.com/{user}" },
            { "name": "GitHub", "url": "https://github.com/{user}" },
            { "name": "GitLab", "url": "https://gitlab.com/{user}" },
            { "name": "Bitbucket", "url": "https://bitbucket.org/{user}/" },
            { "name": "Stack Overflow", "url": "https://stackoverflow.com/users/{user}" },
            { "name": "Dev.to", "url": "https://dev.to/{user}" },
            { "name": "HackerRank", "url": "https://www.hackerrank.com/{user}" },
            { "name": "LeetCode", "url": "https://leetcode.com/{user}/" },
            { "name": "CodeWars", "url": "https://www.codewars.com/users/{user}" },
            { "name": "Docker Hub", "url": "https://hub.docker.com/u/{user}" },
            { "name": "PyPI", "url": "https://pypi.org/user/{user}/" },
            { "name": "NPM", "url": "https://www.npmjs.com/~{user}" },
            { "name": "RubyGems", "url": "https://rubygems.org/profiles/{user}" },
            { "name": "CodePen", "url": "https://codepen.io/{user}" },
            { "name": "Replit", "url": "https://replit.com/@{user}" },
            { "name": "Steam", "url": "https://steamcommunity.com/id/{user}" },
            { "name": "Xbox", "url": "https://xboxgamertag.com/search/{user}" },
            { "name": "PlayStation", "url": "https://psnprofiles.com/{user}" },
            { "name": "Nintendo", "url": "https://nintendo-master.com/profile/{user}" },
            { "name": "Epic Games", "url": "https://www.epicgames.com/id/{user}" },
            { "name": "Roblox", "url": "https://www.roblox.com/user.aspx?username={user}" },
            { "name": "Minecraft", "url": "https://namemc.com/profile/{user}" },
            { "name": "Patreon", "url": "https://www.patreon.com/{user}" },
            { "name": "Gumroad", "url": "https://gumroad.com/{user}" },
            { "name": "Product Hunt", "url": "https://www.producthunt.com/@{user}" },
            { "name": "Keybase", "url": "https://keybase.io/{user}" },
            { "name": "Gravatar", "url": "https://en.gravatar.com/{user}" },
            { "name": "Pastebin", "url": "https://pastebin.com/u/{user}" },
            { "name": "HackerOne", "url": "https://hackerone.com/{user}" },
            { "name": "Bugcrowd", "url": "https://bugcrowd.com/{user}" },
            { "name": "AngelList", "url": "https://angel.co/u/{user}" },
            { "name": "Crunchbase", "url": "https://www.crunchbase.com/person/{user}" },
            { "name": "Xing", "url": "https://www.xing.com/profile/{user}" },
            { "name": "WordPress", "url": "https://{user}.wordpress.com" },
            { "name": "Blogger", "url": "https://{user}.blogspot.com" },
            { "name": "Ghost", "url": "https://{user}.ghost.io" },
            { "name": "Write.as", "url": "https://write.as/{user}" },
            { "name": "Substack", "url": "https://{user}.substack.com" },
            { "name": "SoundCloud", "url": "https://soundcloud.com/{user}" },
            { "name": "Mixcloud", "url": "https://www.mixcloud.com/{user}/" },
            { "name": "Bandcamp", "url": "https://bandcamp.com/{user}" },
            { "name": "Spotify", "url": "https://open.spotify.com/user/{user}" },
            { "name": "Shazam", "url": "https://www.shazam.com/artist/{user}" },
            { "name": "Last.fm", "url": "https://www.last.fm/user/{user}" },
            { "name": "About.me", "url": "https://about.me/{user}" },
            { "name": "RebelMouse", "url": "https://www.rebelmouse.com/{user}" },
            { "name": "Scribd", "url": "https://www.scribd.com/{user}" },
            { "name": "Slideshare", "url": "https://www.slideshare.net/{user}" },
            { "name": "Imgur", "url": "https://imgur.com/user/{user}" },
            { "name": "Giphy", "url": "https://giphy.com/{user}" },
            { "name": "Couchsurfing", "url": "https://www.couchsurfing.com/people/{user}" },
            { "name": "HubPages", "url": "https://hubpages.com/@{user}" },
            { "name": "Quora", "url": "https://www.quora.com/profile/{user}" },
            { "name": "Voat", "url": "https://voat.co/user/{user}" },
            { "name": "8kun", "url": "https://8kun.top/{user}" },
            { "name": "Ekşi Sözlük", "url": "https://eksisozluk.com/biri/{user}" },
            { "name": "DonanımHaber", "url": "https://forum.donanimhaber.com/m_anasayfa?user={user}" },
            { "name": "KizlarSoruyor", "url": "https://www.kizlarsoruyor.com/kisi/{user}" },
            { "name": "OpenSea", "url": "https://opensea.io/{user}" },
            { "name": "Rarible", "url": "https://rarible.com/{user}" },
            { "name": "ResearchGate", "url": "https://www.researchgate.net/profile/{user}" },
            { "name": "Academia", "url": "https://independent.academia.edu/{user}" },
            { "name": "ORCID", "url": "https://orcid.org/{user}" },
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

def finder(user):
    found_links = []
    for url in urls:
        name = url["name"]
        adress = url["url"].format(user=user)
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

def Start():
    print(menu_header)
    username = input(f" Enter the person's username:{GREEN} ")
    finder(username)
    
Start()