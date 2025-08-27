# sources/bom.py
import os
import httpx

UA = "Leandros-Printer/1.0"
TIMEOUT = 12.0

# Per ENV steuerbar:
#   BOM_API_BASE   (default: https://book-of-mormon-api.vercel.app)
#   BOM_BOOK       (optional, z. B. alma, 1nephi, 3nephi, helaman, moroni)
#   BOM_CHAPTER    (optional, z. B. 32)
BASE = os.getenv("BOM_API_BASE", "https://book-of-mormon-api.vercel.app").rstrip("/")
BOOK = (os.getenv("BOM_BOOK") or "").strip().lower()
CHAP = (os.getenv("BOM_CHAPTER") or "").strip()


def _build_url() -> str:
    # /random | /random/:book | /random/:book/:chapter
    if BOOK and CHAP:
        return f"{BASE}/random/{BOOK}/{CHAP}"
    if BOOK:
        return f"{BASE}/random/{BOOK}"
    return f"{BASE}/random"


class Source:
    async def get_text(self):
        """
        Liefert ein Dict, damit routes_sources den Titel separat drucken kann:
          {"title": <reference>, "lines": [<text>]}
        """
        url = _build_url()
        headers = {"Accept": "application/json", "User-Agent": UA}
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()

        ref = (data.get("reference") or "").strip()
        txt = (data.get("text") or "").strip()
        if not ref or not txt:
            raise ValueError("unexpected response shape from BOM API")

        return {"title": ref, "lines": [txt]}
