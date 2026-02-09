import requests
from bs4 import BeautifulSoup

urls = [
    "https://google.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://youtube.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://facebook.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://twitter.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://instagram.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://baidu.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://wikipedia.org,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://yandex.ru,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://yahoo.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://xvideos.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://whatsapp.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://pornhub.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://xnxx.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://amazon.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://yahoo.co.jp,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://live.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://netflix.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://reddit.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://tiktok.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://docomo.ne.jp,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://linkedin.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://office.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://samsung.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://turbopages.org,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://vk.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://xhamster.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://weather.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://twitch.tv,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://mail.ru,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://naver.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://discord.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://bing.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://roblox.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://bilibili.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://microsoftonline.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://pinterest.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://zoom.us,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://qq.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://duckduckgo.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://microsoft.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://fandom.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://quora.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://news.yahoo.co.jp,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://realsrv.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://ebay.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://msn.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://globo.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://stripchat.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://booking.com,TEXTGOESHERE,BODYGOESHERE,bad",
    "https://ok.ru,TEXTGOESHERE,BODYGOESHERE,bad",
]

for line in urls:
    try:
        url = line.split(",")[0]
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract title and body text
            title = soup.title.string if soup.title else ""
            body = soup.get_text(separator=" ", strip=True)

            # Clean up whitespace and newlines
            title = " ".join(str(title).split())
            body = " ".join(body.split())[:500]

            # Perform replacement
            output = line.replace("TEXTGOESHERE", title).replace("BODYGOESHERE", body)
            print(output)
    except Exception:
        continue
