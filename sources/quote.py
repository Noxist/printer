# sources/quote.py
# API-based random quote source (ZenQuotes only).
# Integrates with routes_sources.py via: /api/print/source/quote

import httpx

UA = "Leandros-Printer/1.0"
TIMEOUT = 8.0

def _fmt(text: str, author: str) -> dict:
    text = (text or "").strip()
    author = (author or "Unknown").strip()
    if not text:
        text = "Keep going. You're doing great."
    return {
      # "title": "",
        "lines": [
            f"“{text}”", 
            "",
            f"— {author}"
        ]
    }

async def _fetch_zenquotes() -> dict | None:
    # Docs: https://zenquotes.io/api/random
    url = "https://zenquotes.io/api/random"
    headers = {"Accept": "application/json", "User-Agent": UA}
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
    if isinstance(data, list) and data:
        item = data[0] or {}
        text = (item.get("q") or "").strip()
        author = (item.get("a") or "Unknown").strip()
        if text:
            return _fmt(text, author)
    return None

class Source:
    async def get_text(self):
        # 1) ZenQuotes API
        try:
            q = await _fetch_zenquotes()
            if q:
                return q
        except Exception:
            pass
        # 2) Last resort fallback
        return _fmt("Fortune favors the prepared mind.", "Louis Pasteur")
