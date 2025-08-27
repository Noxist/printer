# sources/weather_bern.py
import httpx

UA = "Leandros-Printer/1.0"
TIMEOUT = 10.0

LAT, LON = 46.948, 7.447   # Bern
PLACE = "Bern"

WCODE = {
    0:"klar", 1:"wolkig", 2:"wolkig", 3:"bedeckt",
    45:"Nebel", 48:"Nebel", 51:"Sprueh", 53:"Sprueh", 55:"Sprueh",
    61:"Regen", 63:"Regen", 65:"Regen", 71:"Schnee", 80:"Schauer", 95:"Gewitter"
}

class Source:
    async def get_text(self):
        url = (f"https://api.open-meteo.com/v1/forecast"
               f"?latitude={LAT}&longitude={LON}&current_weather=true")
        async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": UA}) as cx:
            r = await cx.get(url)
            r.raise_for_status()
            cw = (r.json().get("current_weather") or {})
        t  = cw.get("temperature")
        ws = cw.get("windspeed")
        desc = WCODE.get(cw.get("weathercode"), "—")
        return {"title": f"WETTER · {PLACE}", "lines": [f"{t}°C, {desc}, Wind {ws} km/h"]}
