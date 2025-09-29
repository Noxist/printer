# logic.py — robust print rendering (fonts fallback, no black blocks), Swiss-safe (kein ß)

import os, ssl, json, time, base64, uuid, io, hmac, hashlib, sys, random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

# FastAPI helpers (falls von main.py genutzt)
from fastapi import HTTPException, Request, Response

# Gast-Token DB (wie zuvor)
from guest_tokens import get_guest_db

# ----------------- Konfiguration -----------------

APP_API_KEY = os.getenv("API_KEY", "change_me")
GUEST_MAX_CHARS = int(os.getenv("GUEST_MAX_CHARS", "10000"))

MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USER = os.getenv("MQTT_USERNAME")
MQTT_PASS = os.getenv("MQTT_PASSWORD")
MQTT_TLS  = os.getenv("MQTT_TLS", "true").lower() in ("1","true","yes","on")
TOPIC     = os.getenv("PRINT_TOPIC", "print/tickets")
PUBLISH_QOS = int(os.getenv("PRINT_QOS", "2"))

UI_PASS = os.getenv("UI_PASS", "set_me")
COOKIE_NAME = "ui_token"
UI_REMEMBER_DAYS = int(os.getenv("UI_REMEMBER_DAYS", "30"))

TZ = ZoneInfo(os.getenv("TIMEZONE", "Europe/Zurich"))
PRINT_WIDTH_PX = int(os.getenv("PRINT_WIDTH_PX", "576"))

SETTINGS_FILE = os.getenv("SETTINGS_FILE", "settings.json")
GUESTS = get_guest_db()

# Rendering Tweaks
PRINT_DITHER = os.getenv("PRINT_DITHER", "floyd").lower()
PRINT_THRESHOLD = int(os.getenv("PRINT_THRESHOLD", "128"))
PRINT_GAMMA = float(os.getenv("PRINT_GAMMA", "1.0"))
PRINT_BRIGHTNESS = float(os.getenv("PRINT_BRIGHTNESS", "1.0"))
PRINT_CONTRAST = float(os.getenv("PRINT_CONTRAST", "1.0"))
GRAYSCALE_PNG = os.getenv("GRAYSCALE_PNG", "false").lower() in ("1","true","yes","on")
DEBUG_SAVE_LAST = os.getenv("DEBUG_SAVE_LAST", "0").lower() in ("1","true","yes","on")  # darf env bleiben

# ----------------- MQTT -----------------

client = None
def init_mqtt():
    global client
    import paho.mqtt.client as mqtt
    client = mqtt.Client()
    if MQTT_TLS:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
    if MQTT_USER or MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

init_mqtt()

def log(*a):
    print("[printer]", *a, file=sys.stdout, flush=True)

# ----------------- Zeit/Format -----------------

def now_str(fmt: str = "%d.%m.%Y %H:%M") -> str:
    return datetime.now(TZ).strftime(fmt)

# ----------------- Settings -----------------
from pymongo import MongoClient

def _get_settings_collection():
    # nutzt denselben Mongo-Client wie guest_tokens.py
    try:
        uri = os.getenv("MONGO_URI")
        log("🔍 Verbinde mit MongoDB URI:", uri)
        client = MongoClient(uri)
        db = client.get_database("printer")
        log("✅ Verbindung zu Mongo-DB 'printer' hergestellt.")
        return db["settings"]
    except Exception as e:
        log("❌ MongoDB settings connection error:", repr(e))
        return None
        
def _load_settings() -> dict:
    try:
        coll = _get_settings_collection()
        if coll is None:  # <-- hier geändert!
            log("⚠️ Keine Collection gefunden, gebe leeres Dict zurück.")
            return {}
        log("📥 Lade settings aus Mongo...")
        doc = coll.find_one({"_id": "settings"})
        return doc["data"] if doc and "data" in doc else {}
    except Exception as e:
        log("❌ settings laden fehlgeschlagen:", repr(e))
        return {}
        
def _save_settings(data: dict):
    try:
        coll = _get_settings_collection()
        if coll is None:  # <-- hier geändert!
            log("⚠️ MongoDB nicht verfügbar, settings nicht gespeichert.")
            return
        log("💾 Speichere settings in Mongo:", data)
        coll.update_one({"_id": "settings"}, {"$set": {"data": data}}, upsert=True)
        log("✅ settings erfolgreich in MongoDB gespeichert.")
    except Exception as e:
        log("❌ settings speichern fehlgeschlagen:", repr(e))

_last_reload = 0
_reload_interval = 3  # Sekunden (du kannst das anpassen)

def _reload_settings_if_changed():
    global SETTINGS, _last_reload
    now = time.time()
    if now - _last_reload < _reload_interval:
        return  # 👈 zu früh, überspringen
    _last_reload = now
    log("📥 Lade settings aus Mongo...")
    new_data = _load_settings()
    if new_data and new_data != SETTINGS:
        SETTINGS = new_data
        log(f"♻️ Settings neu geladen: {SETTINGS}")

SETTINGS = _load_settings()

def cfg_get(name: str, default=None):
    _reload_settings_if_changed()  # 👈 hier wird bei jedem Zugriff neu geladen
    if name in SETTINGS:
        return SETTINGS[name]
    return default

def cfg_get_int(name: str, default: int) -> int:
    try:
        return int(cfg_get(name, default))
    except Exception:
        return default

def cfg_get_float(name: str, default: float) -> float:
    try:
        return float(cfg_get(name, default))
    except Exception:
        return default

def cfg_get_bool(name: str, default: bool) -> bool:
    v = str(cfg_get(name, default)).lower()
    return v in ("1","true","yes","on","y","t")

# ----------------- Fonts & Text Helpers -----------------

def _safe_font(path_or_name: str, size: int) -> ImageFont.ImageFont:
    # 1) Expliziter Pfad / Name
    try:
        return ImageFont.truetype(path_or_name, size=size)
    except Exception:
        pass
    # 2) System-Alternativen
    candidates = [
        "DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf",
        "Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for cand in candidates:
        try:
            return ImageFont.truetype(cand, size=size)
        except Exception:
            continue
    # 3) Letzter Ausweg
    return ImageFont.load_default()

def _text_length(text: str, font: ImageFont.ImageFont) -> int:
    try:
        return int(font.getlength(text))
    except Exception:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]

def _wrap(text: str, font: ImageFont.ImageFont, max_px: int) -> List[str]:
    words = (text or "").split()
    if not words:
        return [""]
    lines: List[str] = []
    cur = words[0]
    for w in words[1:]:
        t = f"{cur} {w}"
        if _text_length(t, font) <= max_px:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines

def _line_height(font: ImageFont.ImageFont, mult: float) -> int:
    ascent, descent = font.getmetrics()
    return max(1, int((ascent + descent) * mult))

def _x_for_align(text: str, font: ImageFont.ImageFont,
                 width: int, align: str, ml: int, mr: int) -> int:
    usable = width - ml - mr
    tl = _text_length(text, font)
    if align == "center":
        return ml + max(0, (usable - tl) // 2)
    if align == "right":
        return width - mr - tl
    return ml

from PIL import ImageOps

def _apply_tone(imgL: Image.Image) -> Image.Image:
    if imgL.mode != "L":
        imgL = imgL.convert("L")

    gamma = float(cfg_get("PRINT_GAMMA", 1.0))
    brightness = float(cfg_get("PRINT_BRIGHTNESS", 1.0))
    contrast = float(cfg_get("PRINT_CONTRAST", 1.0))
    invert = str(cfg_get("PRINT_INVERT", False)).lower() in ("1","true","yes","on")

    if invert:
        imgL = ImageOps.invert(imgL)

    if abs(gamma - 1.0) > 1e-3:
        inv_g = 1.0 / max(1e-6, gamma)
        lut = [int(pow(i/255.0, inv_g)*255 + 0.5) for i in range(256)]
        imgL = imgL.point(lut, mode="L")

    if abs(brightness - 1.0) > 1e-3:
        lut = [max(0, min(255, int(i*brightness))) for i in range(256)]
        imgL = imgL.point(lut, mode="L")

    if abs(contrast - 1.0) > 1e-3:
        mid = 127.5
        lut = [max(0, min(255, int((i - mid)*contrast + mid))) for i in range(256)]
        imgL = imgL.point(lut, mode="L")

    return imgL

def _ordered_bayer_dither(imgL: Image.Image) -> Image.Image:
    bayer4 = [
        [ 0,  8,  2, 10],
        [12,  4, 14,  6],
        [ 3, 11,  1,  9],
        [15,  7, 13,  5]
    ]
    w,h = imgL.size
    px = imgL.load()
    out = Image.new("1", (w,h), 255)
    outpx = out.load()
    for y in range(h):
        for x in range(w):
            thr = (bayer4[y & 3][x & 3] + 0.5) * (255.0/16.0)
            outpx[x,y] = 0 if px[x,y] < thr else 255
    return out

def _to_1bit(img: Image.Image) -> Image.Image:
    imgL = img.convert("L") if img.mode != "L" else img
    imgL = _apply_tone(imgL)

    dither = str(cfg_get("PRINT_DITHER", "floyd")).lower()
    threshold = int(cfg_get("PRINT_THRESHOLD", 128))

    if dither == "none":
        return imgL.point(lambda x: 0 if x < threshold else 255, mode="1")
    if dither == "threshold":
        return imgL.point(lambda x: 0 if x < threshold else 255, mode="1")
    if dither == "floyd":
        return imgL.convert("1", dither=Image.FLOYDSTEINBERG)
    if dither == "bayer":
        return _ordered_bayer_dither(imgL)
    return imgL.convert("1", dither=Image.FLOYDSTEINBERG)

def pil_to_base64_png(img: Image.Image) -> str:
    # Graustufen-PNG optional
    grayscale_png = str(cfg_get("GRAYSCALE_PNG", False)).lower() in ("1","true","yes","on")
    if grayscale_png:
        imgL = img.convert("L")
        imgL = _apply_tone(imgL)
        if DEBUG_SAVE_LAST:
            try: imgL.save("/tmp/last_print.png", format="PNG", optimize=True)
            except: pass
        buf = io.BytesIO()
        imgL.save(buf, format="PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode("ascii")

    # Standard: 1-Bit mit Dither
    img1 = _to_1bit(img)
    if DEBUG_SAVE_LAST:
        try: img1.save("/tmp/last_print.png", format="PNG", optimize=True)
        except: pass
    buf = io.BytesIO()
    img1.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")

def mqtt_publish_image_base64(b64_png: str, cut_paper: int = 1,
                              paper_width_mm: int = 0, paper_height_mm: int = 0):
    payload = {
        "ticket_id": f"web-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}",
        "data_type": "png",
        "data_base64": b64_png,
        "paper_type": 0,
        "paper_width_mm": paper_width_mm,
        "paper_height_mm": paper_height_mm,
        "cut_paper": cut_paper
    }
    log(f"MQTT publish → topic={TOPIC} qos={PUBLISH_QOS} bytes={len(b64_png)}")
    client.publish(TOPIC, json.dumps(payload), qos=PUBLISH_QOS, retain=False)

# ----------------- Receipt Config -----------------

class ReceiptCfg:
    def __init__(self):
        self.preset = str(cfg_get("RECEIPT_PRESET", "clean")).lower()

        self.title_size = cfg_get_int("RECEIPT_TITLE_SIZE", 36)
        self.text_size  = cfg_get_int("RECEIPT_TEXT_SIZE", 28)
        self.time_size  = cfg_get_int("RECEIPT_TIME_SIZE", 24)

        self.title_font_name = cfg_get("RECEIPT_TITLE_FONT", "DejaVuSans.ttf")
        self.text_font_name  = cfg_get("RECEIPT_TEXT_FONT",  "DejaVuSans.ttf")
        self.time_font_name  = cfg_get("RECEIPT_TIME_FONT",  "DejaVuSans.ttf")

        self.margin_top = cfg_get_int("RECEIPT_MARGIN_TOP", 60)
        self.margin_bottom = cfg_get_int("RECEIPT_MARGIN_BOTTOM", 18)
        self.margin_left   = cfg_get_int("RECEIPT_MARGIN_LEFT", 18)
        self.margin_right  = cfg_get_int("RECEIPT_MARGIN_RIGHT", 18)

        self.gap_title_text   = cfg_get_int("RECEIPT_GAP_TITLE_TEXT", 10)
        self.line_height_mult = cfg_get_float("RECEIPT_LINE_HEIGHT", 1.15)

        self.align_title = cfg_get("RECEIPT_ALIGN_TITLE", "left")
        self.align_text  = cfg_get("RECEIPT_ALIGN_TEXT",  "left")
        self.align_time  = cfg_get("RECEIPT_ALIGN_TIME",  "left")

        self.time_show_minutes = cfg_get_bool("RECEIPT_TIME_SHOW_MINUTES", True)
        self.time_show_seconds = cfg_get_bool("RECEIPT_TIME_SHOW_SECONDS", False)
        self.time_prefix = cfg_get("RECEIPT_TIME_PREFIX", "")

        self.rule_after_title = cfg_get_bool("RECEIPT_RULE_AFTER_TITLE", False)
        self.rule_px  = cfg_get_int("RECEIPT_RULE_PX", 1)
        self.rule_pad = cfg_get_int("RECEIPT_RULE_PAD", 6)

        if self.preset == "compact":
            self.title_size, self.text_size, self.time_size = 30, 24, 22
            self.margin_top, self.margin_bottom = 16, 12
            self.gap_title_text = 6
            self.line_height_mult = 1.05
        elif self.preset == "bigtitle":
            self.title_size = max(self.title_size, 44)
            self.gap_title_text = max(self.gap_title_text, 14)
            self.rule_after_title = True

        self.font_title = _safe_font(self.title_font_name, self.title_size)
        self.font_text  = _safe_font(self.text_font_name,  self.text_size)
        self.font_time  = _safe_font(self.time_font_name,  self.time_size)

def _time_str(cfg: ReceiptCfg) -> str:
    fmt = "%Y-%m-%d %H"
    if cfg.time_show_minutes or cfg.time_show_seconds:
        fmt += ":%M"
    if cfg.time_show_seconds:
        fmt += ":%S"
    s = datetime.now(TZ).strftime(fmt)
    s = (cfg.time_prefix + s).strip()
    return s

# ----------------- Zwei-Pass-Render (Fix) -----------------

def render_receipt(
    title: str,
    lines: List[str],
    add_time: bool,
    width_px: int,
    cfg: ReceiptCfg,
    sender_name: Optional[str] = None
) -> Image.Image:
    max_w = width_px - cfg.margin_left - cfg.margin_right

    title_lines = _wrap(title.strip(), cfg.font_title, max_w) if (title and title.strip()) else []
    time_line = _time_str(cfg) if add_time else None
    sender_line = f"From: {sender_name}" if sender_name else None

    lh_title = _line_height(cfg.font_title, cfg.line_height_mult)
    lh_text  = _line_height(cfg.font_text,  cfg.line_height_mult)
    lh_time  = _line_height(cfg.font_time,  cfg.line_height_mult)

    # Pass 1: Hoehe schaetzen
    cur_y = cfg.margin_top
    if title_lines:
        cur_y += lh_title * len(title_lines)
        if cfg.rule_after_title:
            cur_y += cfg.rule_pad + cfg.rule_px + cfg.rule_pad
        else:
            cur_y += cfg.gap_title_text
    if sender_line:
        cur_y += lh_time
    if time_line:
        cur_y += lh_time

    wrapped_body: List[str] = []
    for raw in lines:
        txt = (raw or "").strip()
        if not txt:
            wrapped_body.append("")
        else:
            wrapped_body.extend(_wrap(txt, cfg.font_text, max_w))
    cur_y += lh_text * max(1, len(wrapped_body))
    cur_y += cfg.margin_bottom
    total_h = max(120, cur_y)

    # Pass 2: Zeichnen auf endgueltiger Hoehe (Graustufen-L)
    img = Image.new("L", (width_px, total_h), color=255)
    draw = ImageDraw.Draw(img)

    y = cfg.margin_top
    for ln in title_lines:
        x = _x_for_align(ln, cfg.font_title, width_px, cfg.align_title, cfg.margin_left, cfg.margin_right)
        draw.text((x, y), ln, fill=0, font=cfg.font_title)
        y += lh_title

    if title_lines:
        if cfg.rule_after_title:
            y += cfg.rule_pad
            draw.rectangle((cfg.margin_left, y, width_px - cfg.margin_right, y + cfg.rule_px), fill=0)
            y += cfg.rule_px + cfg.rule_pad
        else:
            y += cfg.gap_title_text

    if sender_line:
        x = _x_for_align(sender_line, cfg.font_time, width_px, cfg.align_time, cfg.margin_left, cfg.margin_right)
        draw.text((x, y), sender_line, fill=0, font=cfg.font_time)
        y += lh_time

    if time_line:
        x = _x_for_align(time_line, cfg.font_time, width_px, cfg.align_time, cfg.margin_left, cfg.margin_right)
        draw.text((x, y), time_line, fill=0, font=cfg.font_time)
        y += lh_time

    for ln in wrapped_body:
        x = _x_for_align(ln, cfg.font_text, width_px, cfg.align_text, cfg.margin_left, cfg.margin_right)
        draw.text((x, y), ln, fill=0, font=cfg.font_text)
        y += lh_text

    return img

# ----------------- Bild + Header kombinieren -----------------

def render_image_with_headers(
    image: Image.Image,
    width_px: int,
    cfg: ReceiptCfg,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    sender_name: Optional[str] = None
) -> Image.Image:
    if image.mode != "L":
        image = image.convert("L")
    w, h = image.size
    if w != width_px and w > 0:
        image = image.resize((width_px, int(h * (width_px / w))))
    header_title = (title or "").strip()
    header_lines = [ (subtitle or "").strip() ] if subtitle and subtitle.strip() else []
    head = render_receipt(header_title, header_lines, add_time=False, width_px=width_px, cfg=cfg, sender_name=sender_name)
    out = Image.new("L", (width_px, head.height + image.height), color=255)
    out.paste(head, (0, 0))
    out.paste(image, (0, head.height))
    return out

# ----------------- Security -----------------

def check_api_key(req: Request):
    key = req.headers.get("x-api-key") or req.query_params.get("key")
    if key != APP_API_KEY:
        raise HTTPException(401, "invalid api key")

def sign_token(ts: str) -> str:
    sig = hmac.new(APP_API_KEY.encode(), ts.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{ts}.{sig}"

def verify_token(token: str) -> bool:
    try:
        ts, _sig = token.split(".")
        if sign_token(ts) != token:
            return False
        created = datetime.fromtimestamp(int(ts), tz=TZ)
        return (datetime.now(TZ) - created) < timedelta(days=UI_REMEMBER_DAYS)
    except Exception:
        return False

def require_ui_auth(request: Request) -> bool:
    if (request.headers.get("x-api-key") or request.query_params.get("key")) == APP_API_KEY:
        return True
    tok = request.cookies.get(COOKIE_NAME)
    return bool(tok and verify_token(tok))

def issue_cookie(resp: Response):
    ts = str(int(time.time()))
    token = sign_token(ts)
    resp.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=UI_REMEMBER_DAYS * 24 * 3600,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/"
    )

def ui_auth_state(request: Request, pass_: Optional[str], remember: bool) -> tuple[bool, bool]:
    if require_ui_auth(request):
        return True, False
    if pass_ is not None and pass_ == UI_PASS:
        return True, bool(remember)
    return False, False

# ----------------- Guest Tokens -----------------
def _guest_check_len_ok(total_chars: int) -> tuple[bool, str]:
    if total_chars <= GUEST_MAX_CHARS:
        return True, ""
    return False, f"<div class='card'>Too long: {total_chars} characters. Max allowed: {GUEST_MAX_CHARS}.</div>"

def guest_consume_or_error(token: str) -> Optional[dict]:
    return GUESTS.consume(token)

# ----------------- Settings Export -----------------

SET_KEYS = [
    ("RECEIPT_PRESET", "clean", "select", ["clean", "compact", "bigtitle"]),
    ("RECEIPT_MARGIN_TOP", 28, "number", None),
    ("RECEIPT_MARGIN_BOTTOM", 18, "number", None),
    ("RECEIPT_MARGIN_LEFT", 18, "number", None),
    ("RECEIPT_MARGIN_RIGHT", 18, "number", None),
    ("RECEIPT_GAP_TITLE_TEXT", 10, "number", None),
    ("RECEIPT_LINE_HEIGHT", 1.15, "number", None),
    ("RECEIPT_RULE_AFTER_TITLE", False, "checkbox", None),
    ("RECEIPT_RULE_PX", 1, "number", None),
    ("RECEIPT_RULE_PAD", 6, "number", None),
    ("RECEIPT_ALIGN_TITLE", "left", "select", ["left", "center", "right"]),
    ("RECEIPT_ALIGN_TEXT", "left", "select", ["left", "center", "right"]),
    ("RECEIPT_ALIGN_TIME", "left", "select", ["left", "center", "right"]),
    ("RECEIPT_TITLE_SIZE", 36, "number", None),
    ("RECEIPT_TEXT_SIZE", 28, "number", None),
    ("RECEIPT_TIME_SIZE", 24, "number", None),
    ("RECEIPT_TITLE_FONT", "DejaVuSans.ttf", "text", None),
    ("RECEIPT_TEXT_FONT", "DejaVuSans.ttf", "text", None),
    ("RECEIPT_TIME_FONT", "DejaVuSans.ttf", "text", None),
    ("RECEIPT_TIME_SHOW_MINUTES", True, "checkbox", None),
    ("RECEIPT_TIME_SHOW_SECONDS", False, "checkbox", None),
    ("RECEIPT_TIME_PREFIX", "", "text", None),
    ("PRINT_DITHER", "floyd", "select", ["none", "threshold", "floyd", "bayer"]),
    ("PRINT_THRESHOLD", 128, "number", None),
    ("PRINT_GAMMA", 1.0, "number", None),
    ("PRINT_BRIGHTNESS", 1.0, "number", None),
    ("PRINT_CONTRAST", 1.0, "number", None),
    ("GRAYSCALE_PNG", False, "checkbox", None),
    ("PRINT_INVERT", False, "checkbox", None),

]

def settings_effective() -> dict:
    eff = {}
    for key, default, _, _ in SET_KEYS:
        eff[key] = cfg_get(key, default)
    return eff

# ----------------- Beispiel-Helfer zum Drucken -----------------

def render_and_publish_text(title: str, body_lines: List[str], add_time: bool = True,
                            sender_name: Optional[str] = None, cut_paper: int = 1):
    cfg = ReceiptCfg()
    img = render_receipt(title, body_lines, add_time, PRINT_WIDTH_PX, cfg, sender_name=sender_name)
    b64 = pil_to_base64_png(img)
    mqtt_publish_image_base64(b64, cut_paper=cut_paper)
