import os, random, time, httpx

UA = "Leandros-Printer/1.0"
TIMEOUT = 15.0
# Standard-Quelle (kannst du via ENV überschreiben)
BOM_JSON_URL = os.getenv(
    "BOM_JSON_URL",
    "https://raw.githubusercontent.com/bcbooks/scriptures-json/master/flat/book-of-mormon-flat.json",
)

# simpler In-Memory Cache (24h)
_cache = {"ts": 0.0, "data": None}
TTL = 24 * 3600

async def _load_bom_json():
    now = time.time()
    if _cache["data"] and (now - _cache["ts"] < TTL):
        return _cache["data"]
    async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": UA}) as client:
        r = await client.get(BOM_JSON_URL)
        r.raise_for_status()
        data = r.json()
    _cache["data"] = data
    _cache["ts"] = now
    return data

def _pick_random_ref_text(data: dict) -> tuple[str, str]:
    books = data.get("books", [])
    if not books:
        raise ValueError("BOM data: no books")
    b = random.choice(books)
    chs = b.get("chapters", [])
    if not chs:
        raise ValueError("BOM data: no chapters")
    ch = random.choice(chs)
    verses = ch.get("verses", [])
    if not verses:
        raise ValueError("BOM data: no verses")
    v = random.choice(verses)
    ref = f"{b['name']} {ch['chapter']}:{v['verse']}"
    txt = (v.get("text") or "").strip()
    return ref, txt

class Source:
    async def get_text(self) -> str:
        data = await _load_bom_json()
        ref, txt = _pick_random_ref_text(data)
        return f"{ref} — {txt}"
