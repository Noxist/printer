# sources/weather_bern.py
# Styled weather slip for Bern (Open-Meteo) – symbols + compact layout
import httpx
from datetime import datetime
import zoneinfo

UA = "Leandros-Printer/1.0"
TIMEOUT = 10.0

LAT, LON = 46.948, 7.447   # Bern
PLACE = "Bern"
TZ = zoneinfo.ZoneInfo("Europe/Zurich")

# Simple icon map for WMO weather codes
# (Use characters supported by DejaVu Sans on the printer)
def wx_icon(code: int) -> str:
    if code in (0,): return "☀"   # clear
    if code in (1,2): return "⛅"  # partly cloudy
    if code in (3,):  return "☁"  # overcast
    if code in (45,48): return "🌫"  # fog
    if code in (51,53,55): return "☂"  # drizzle
    if code in (61,63,65,80,81,82): return "🌧"  # rain
    if code in (71,73,75,85,86): return "❄"  # snow
    if code in (95,96,99): return "⛈"  # thunder
    return "·"

def as_local(dt_iso: str) -> datetime:
    # dt_iso: "YYYY-MM-DDTHH:MM"
    return datetime.fromisoformat(dt_iso).replace(tzinfo=zoneinfo.ZoneInfo("UTC")).astimezone(TZ)

def pick_hour(hourly_times: list[str], target_hour_local: int) -> int:
    """Return index of the first hourly entry matching given local hour (08/12/18)."""
    for i, t in enumerate(hourly_times):
        if as_local(t).hour == target_hour_local:
            return i
    # fallback: nearest by absolute hour diff
    diffs = [(i, abs(as_local(t).hour - target_hour_local)) for i, t in enumerate(hourly_times[:24])]
    diffs.sort(key=lambda x: x[1])
    return diffs[0][0] if diffs else 0

class Source:
    async def get_text(self):
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={LAT}&longitude={LON}"
            "&current_weather=true"
            "&hourly=temperature_2m,weathercode,precipitation_probability"
            "&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            "&timezone=Europe%2FZurich"
            "&forecast_days=2"
        )
        async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": UA}) as cx:
            r = await cx.get(url)
            r.raise_for_status()
            data = r.json()

        cw = data.get("current_weather") or {}
        hourly = data.get("hourly") or {}
        daily  = data.get("daily") or {}

        # --- NOW ---
        now_t   = cw.get("temperature")
        now_w   = int(cw.get("weathercode") or 0)
        now_ws  = cw.get("windspeed")
        now_wd  = cw.get("winddirection")
        now_ico = wx_icon(now_w)

        # compact wind dir as cardinal
        def wind_dir(deg: float | int | None) -> str:
            if deg is None: return "–"
            dirs = ["N","NE","E","SE","S","SW","W","NW"]
            return dirs[int((float(deg)%360)/45 + 0.5) % 8]

        # --- Today slices (08 / 12 / 18) ---
        times = hourly.get("time") or []
        t2m   = hourly.get("temperature_2m") or []
        wxc   = hourly.get("weathercode") or []
        pr    = hourly.get("precipitation_probability") or []

        i_morn = pick_hour(times, 8)
        i_noon = pick_hour(times, 12)
        i_eve  = pick_hour(times, 18)

        def slot(i: int) -> tuple[str,str]:
            temp = t2m[i] if i < len(t2m) else None
            code = int(wxc[i]) if i < len(wxc) else 0
            pp   = pr[i] if i < len(pr) else None
            ico  = wx_icon(code)
            # e.g. "08: 15°C ⛅ 30%"
            pp_txt = f" {int(pp)}%" if pp is not None else ""
            hour_local = as_local(times[i]).strftime("%H")
            return hour_local, f"{temp:.0f}°C {ico}{pp_txt}"

        h_morn, s_morn = slot(i_morn)
        h_noon, s_noon = slot(i_noon)
        h_eve,  s_eve  = slot(i_eve)

        # --- Tomorrow mini ---
        tmax = daily.get("temperature_2m_max") or []
        tmin = daily.get("temperature_2m_min") or []
        dcode = daily.get("weathercode") or []
        pmax  = daily.get("precipitation_probability_max") or []
        tomo_ico = wx_icon(int(dcode[1])) if len(dcode) > 1 else "·"
        tomo   = f"Min {tmin[1]:.0f}°C · Max {tmax[1]:.0f}°C" if len(tmin) > 1 and len(tmax) > 1 else ""
        tomo_p = f"{int(pmax[1])}%" if len(pmax) > 1 else "–"

        # --- Header line with date ---
        today = datetime.now(TZ).strftime("%a %d %b").upper()  # e.g. "FRI 29 AUG"

        lines = [
            f"{today} · {PLACE}",
            f"Now {now_t:.0f}°C {now_ico}  {wind_dir(now_wd)} {now_ws:.0f} km/h",
            "",  # spacer
            f"{h_morn}: {s_morn}",
            f"{h_noon}: {s_noon}",
            f"{h_eve}:  {s_eve}",
            "",  # spacer
            f"Tomorrow {tomo_ico}  {tomo}  ({tomo_p})",
        ]

        return {"title": "WEATHER · BERN", "lines": lines}
