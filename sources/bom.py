# sources/bom.py
import os, time, random, httpx

UA = "Leandros-Printer/1.0"
TIMEOUT = 15.0
BOM_JSON_URL = os.getenv(
    "BOM_JSON_URL",
    "https://raw.githubusercontent.com/bcbooks/scriptures-json/master/flat/book-of-mormon-flat.json",
)

# 24h In-Memory Cache
_TTL = 24*3600
_cache_ts = 0.0
_cache = None

async def _fetch_json():
    global _cache_ts, _cache
    now = time.time()
    if _cache and (now - _cache_ts < _TTL):
        return _cache
    async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": UA}) as client:
        r = await client.get(BOM_JSON_URL)
        r.raise_for_status()
        data = r.json()
    _cache, _cache_ts = data, now
    return data

def _pick_from_hier(data: dict) -> tuple[str, str]:
    # erwartet: {"books":[{"name":..,"chapters":[{"chapter":..,"verses":[{"verse":..,"text":..},..]}]}]}
    books = data.get("books", [])
    if not books: raise ValueError("hier: no books")
    b = random.choice(books)
    chs = b.get("chapters", [])
    if not chs: raise ValueError("hier: no chapters")
    ch = random.choice(chs)
    vs = ch.get("verses", [])
    if not vs: raise ValueError("hier: no verses")
    v  = random.choice(vs)
    ref = f"{b['name']} {ch['chapter']}:{v['verse']}"
    txt = (v.get("text") or "").strip()
    return ref, txt

def _pick_from_flat(data) -> tuple[str, str]:
    # erwartet: Liste von Objekten mit Feldern wie: book, chapter, verse, text
    if not isinstance(data, list) or not data:
        raise ValueError("flat: not a non-empty list")
    rec = random.choice(data)
    book = rec.get("book") or rec.get("volume") or "Book"
    ch   = rec.get("chapter") or rec.get("chap") or "?"
    vs   = rec.get("verse") or rec.get("vers") or "?"
    txt  = (rec.get("text") or rec.get("verse_text") or "").strip()
    ref  = f"{book} {ch}:{vs}"
    if not txt:
        raise ValueError("flat: empty verse text")
    return ref, txt

def _pick_ref_text(data) -> tuple[str, str]:
    # Versuche flat zuerst (da dein Default-Link flat ist), fallback hierarchisch
    try:
        return _pick_from_flat(data)
    except Exception:
        return _pick_from_hier(data)

class Source:
    async def get_text(self) -> str:
        try:
            data = await _fetch_json()
            ref, txt = _pick_ref_text(data)
            return f"{ref} — {txt}"
        except Exception as e:
            # Fallback, damit nie 502 zurückkommt
            samples = [
                ("1 Nephi 3:7", "I will go and do the things which the Lord hath commanded..."),
                ("Alma 32:21", "Faith is not to have a perfect knowledge of things..."),
                ("Moroni 10:4", "Ask God, the Eternal Father, in the name of Christ...")
            ]
            ref, txt = random.choice(samples)
            return f"{ref} — {txt}  (fallback: {e})"
