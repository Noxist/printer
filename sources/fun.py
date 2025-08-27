# sources/fun.py
import os, httpx, random

UA = "Leandros-Printer/1.0"
TIMEOUT = 10.0
FUN_SOURCE = os.getenv("FUN_SOURCE", "").lower().strip()  # "chuck" | "facts" | ""

async def _chuck(cx):
    r = await cx.get("https://api.chucknorris.io/jokes/random")
    r.raise_for_status()
    return (r.json().get("value") or "").strip()

async def _facts(cx):
    r = await cx.get("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en")
    r.raise_for_status()
    return (r.json().get("text") or "").strip()

class Source:
    async def get_text(self):
        headers = {"User-Agent": UA}
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers) as cx:
            choice = FUN_SOURCE or random.choice(["chuck", "facts"])
            text = await (_chuck(cx) if choice=="chuck" else _facts(cx))
        text = text.replace("\n", " ").strip()
        return {"title": "FUN", "lines": [text[:300]]}
