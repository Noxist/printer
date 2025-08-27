# sources/news.py
import os, httpx, random

UA = "Leandros-Printer/1.0"
TIMEOUT = 10.0
KEY = os.getenv("NEWSAPI_KEY", "")
COUNTRY = os.getenv("NEWS_COUNTRY", "ch").lower().strip()  # 'ch' default
QUERY = (os.getenv("NEWS_QUERY") or "").strip()

API_URL = "https://newsapi.org/v2/top-headlines" if not QUERY else "https://newsapi.org/v2/everything"

class Source:
    async def get_text(self):
        if not KEY:
            raise RuntimeError("NEWSAPI_KEY fehlt")
        headers = {"User-Agent": UA}
        params = {"pageSize": 5, "apiKey": KEY}
        if QUERY:
            params.update(q=QUERY, language="de")
        else:
            params.update(country=COUNTRY)
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers) as cx:
            r = await cx.get(API_URL, params=params)
            r.raise_for_status()
            data = r.json()
        arts = (data.get("articles") or [])[:5]
        if not arts:
            return {"title": "NEWS", "lines": ["Keine Meldungen gefunden."]}
        pick = random.choice(arts)
        title = "NEWS"
        line = (pick.get("title") or "").strip()[:220]
        return {"title": title, "lines": [line]}
