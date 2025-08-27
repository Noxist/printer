# sources/weather_both.py
import httpx

UA = "Leandros-Printer/1.0"
TIMEOUT = 10.0

LOCS = [
    ("Unterseen", 46.684, 7.847),
    ("Bern",      46.948, 7.447),
]

WCODE = {
    0:"klar", 1:"wolkig", 2:"wolkig", 3:"bedeckt",
    45:"Nebel", 48:"Nebel", 51:"Sprueh", 53:"Sprueh", 55:"Sprueh",
    61:"Regen", 63:"Regen", 65:"Regen", 71:"Schnee", 80:"Schauer", 95:"Gewitter"
}

async def _one(cx, place, lat, lon):
    url = (f"https://api.open-meteo.com/v1/forecast"
           f"?latitude={lat}&longitude={lon}&current_weather=true")
    r = await cx.get(url); r.raise_for_status()
    cw = (r.json().get("current_weather") or {})
    t  = cw.get("temperature"); ws = cw.get("windspeed")
    desc = WCODE.get(cw.get("weathercode"), "—")
    return f"{place}: {t}°C, {desc}, Wind {ws} km/h"

class Source:
    async def get_text(self):
        lines=[]
        async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": UA}) as cx:
            for place, lat, lon in LOCS:
                lines.append(await _one(cx, place, lat, lon))
        return {"title": "WETTER · Unterseen + Bern", "lines": lines}
