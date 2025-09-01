# sources/weather_card_multi.py
# Multi-place weather card (PNG) for thermal printers – Bern, Unterseen or both.
import io, os, httpx
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

UA = "Leandros-Printer/1.0"
TIMEOUT = 10.0
PRN_W = int(os.getenv("PRINTER_WIDTH_DOTS", "576"))
TZ    = os.getenv("TIMEZONE", "Europe/Zurich")

# --- places you support ---
PLACES = {
    "bern":      {"name": "Bern",      "lat": 46.948, "lon": 7.447},
    "unterseen": {"name": "Unterseen", "lat": 46.685, "lon": 7.847},
}

ICON_BASE = "https://raw.githubusercontent.com/erikflowers/weather-icons/master/png/256/"
ICON_MAP = {
    0:"wi-day-sunny.png", 1:"wi-day-cloudy.png", 2:"wi-cloudy.png", 3:"wi-cloudy.png",
    45:"wi-fog.png", 48:"wi-fog.png", 51:"wi-sprinkle.png", 53:"wi-sprinkle.png", 55:"wi-sprinkle.png",
    56:"wi-sleet.png", 57:"wi-sleet.png", 61:"wi-day-rain.png", 63:"wi-rain.png", 65:"wi-rain.png",
    66:"wi-sleet.png", 67:"wi-sleet.png", 71:"wi-snow.png", 73:"wi-snow.png", 75:"wi-snow.png",
    77:"wi-snow.png", 80:"wi-day-showers.png", 81:"wi-showers.png", 82:"wi-showers.png",
    85:"wi-day-snow.png", 86:"wi-day-snow.png", 95:"wi-thunderstorm.png", 96:"wi-storm-showers.png", 99:"wi-storm-showers.png",
}
def _icon_url(code:int)->str: return ICON_BASE + ICON_MAP.get(int(code), "wi-na.png")

async def _fetch(lat:float, lon:float):
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={lat}&longitude={lon}"
           "&current=temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,wind_direction_10m,weather_code"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
           f"&timezone={TZ}&forecast_days=1")
    async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": UA}) as cx:
        r = await cx.get(url); r.raise_for_status()
        return r.json()

async def _get_icon(code:int):
    async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": UA}) as cx:
        r = await cx.get(_icon_url(code)); r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("L")
        return im

def _font(size:int):
    try:    return ImageFont.truetype("DejaVuSans.ttf", size)
    except: return ImageFont.load_default()

def _hline(draw, y, w): draw.line((0, y, w, y), fill=0, width=2)

def _block(draw, x, y, w, payload, title_fonts):
    f_title, f_body, f_small = title_fonts
    daily = payload.get("daily") or {}
    cur   = payload.get("current") or {}

    name = payload["_name"]
    code = int(cur.get("weather_code", 0))
    tnow = round(cur.get("temperature_2m", 0))
    wind = cur.get("wind_speed_10m", 0)
    wdir = int(cur.get("wind_direction_10m", 0)) % 360
    tmin = round((daily.get("temperature_2m_min") or [0])[0])
    tmax = round((daily.get("temperature_2m_max") or [0])[0])
    pmax = (daily.get("precipitation_probability_max") or [0])[0]

    # header
    draw.text((x, y), name.upper(), font=f_title, fill=0); y += 44
    _hline(draw, y, w - x); y += 16

    # icon
    icon: Image.Image = payload.get("_icon")
    if icon:
        icon = icon.resize((160, 160), Image.BICUBIC)
        draw.im.paste(icon, (w - 160 - 20, y - 6))

    draw.text((x, y), f"{datetime.now():%a %d %b}", font=f_small, fill=0); y += 34
    draw.text((x, y), f"Now {tnow}°C  ·  Wind {wind:.0f} km/h  ·  {wdir}°", font=f_body, fill=0); y += 46
    draw.text((x, y), f"Min {tmin}°C  ·  Max {tmax}°C  ·  Rain {pmax}%", font=f_body, fill=0); y += 52

    return y

def _compose(payloads:list) -> bytes:
    W, P = PRN_W, 22
    canvas = Image.new("L", (W, 1200), 255)
    d = ImageDraw.Draw(canvas)
    d.im = canvas  # hack so _block can paste

    f_title = _font(40); f_body = _font(34); f_small = _font(26)
    title_fonts = (f_title, f_body, f_small)

    y = P
    d.text((P, y), "WEATHER", font=_font(44), fill=0); y += 50
    _hline(d, y, W-P); y += 18

    for i, payload in enumerate(payloads):
        y = _block(d, P, y, W, payload, title_fonts)
        _hline(d, y, W-P); y += 18
        if i < len(payloads)-1: y += 10  # gap between places

    d.text((P, y), "Source: open-meteo.com", font=f_small, fill=0)
    y += 36

    canvas = canvas.crop((0, 0, W, y))
    buf = io.BytesIO(); canvas.save(buf, "PNG", optimize=True)
    return buf.getvalue()

class Source:
    async def get_png(self, **kwargs):
        # Query aus kwargs ziehen (direkt, nicht nested)
        raw = (kwargs.get("places") or kwargs.get("place") or "bern").lower().replace(" ", "")
        ids = [p for p in raw.split(",") if p in PLACES] or ["bern"]

        payloads = []
        for pid in ids:
            meta = PLACES[pid]
            wx = await _fetch(meta["lat"], meta["lon"])
            wx["_name"] = meta["name"]
            try:
                wx["_icon"] = await _get_icon(int((wx.get("current") or {}).get("weather_code", 0)))
            except Exception:
                wx["_icon"] = None
            payloads.append(wx)

        return _compose(payloads)

    async def get_text(self, **kwargs):
        return {
            "title": "WEATHER",
            "lines": [f"Use ?places=bern,unterseen&as_png=1 (got: {kwargs})"]
        }
