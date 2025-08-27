import os
import ssl
import json
import time
import base64
import uuid
import io
import hmac
import hashlib
import sys
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List
from PIL import Image, ImageDraw, ImageFont
from fastapi import HTTPException, Request, Response
from guest_tokens import GuestDB

APP_API_KEY = os.getenv("API_KEY", "change_me")
MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USER = os.getenv("MQTT_USERNAME")
MQTT_PASS = os.getenv("MQTT_PASSWORD")
MQTT_TLS = os.getenv("MQTT_TLS", "true").lower() == "true"
TOPIC = os.getenv("PRINT_TOPIC", "print/tickets")
PUBLISH_QOS = int(os.getenv("PRINT_QOS", "2"))
UI_PASS = os.getenv("UI_PASS", "set_me")
COOKIE_NAME = "ui_token"
UI_REMEMBER_DAYS = int(os.getenv("UI_REMEMBER_DAYS", "30"))
TZ = ZoneInfo(os.getenv("TIMEZONE", "Europe/Zurich"))
PRINT_WIDTH_PX = int(os.getenv("PRINT_WIDTH_PX", "576"))
SETTINGS_FILE = os.getenv("SETTINGS_FILE", "settings.json")
GUEST_DB_FILE = os.getenv("GUEST_DB_FILE", "guest_tokens.json")
GUESTS = GuestDB(GUEST_DB_FILE)

# MQTT Setup
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

def now_str(fmt="%d.%m.%Y %H:%M") -> str:
    return datetime.now(TZ).strftime(fmt)

def pil_to_base64_png(img: Image.Image) -> str:
    buf = io.BytesIO()
    img = img.convert("L")  # Graustufen (nicht nur schwarz/weiß)
    
    from PIL import ImageOps
    img = ImageOps.invert(img)  # Invertieren (Schwarz-weiß tauschen)

    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")

def mqtt_publish_image_base64(b64_png: str, cut_paper: int = 1, paper_width_mm: int = 0, paper_height_mm: int = 0):
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

# Book of Mormon JSON Loader
BOM_URL = "https://raw.githubusercontent.com/bcbooks/scriptures-json/master/flat/book-of-mormon-flat.json"
_BOM_CACHE: list[dict] = []
_BOM_CACHE_TS = 0
_BOM_CACHE_TTL = 24 * 3600  # 24h Cache

def _get_bom_data(force: bool = False) -> list[dict]:
    global _BOM_CACHE, _BOM_CACHE_TS
    if force or not _BOM_CACHE or (time.time() - _BOM_CACHE_TS) > _BOM_CACHE_TTL:
        try:
            import urllib.request
            with urllib.request.urlopen(BOM_URL, timeout=15) as resp:
                _BOM_CACHE = json.loads(resp.read().decode("utf-8"))
                _BOM_CACHE_TS = time.time()
                log(f"BoM JSON geladen ({len(_BOM_CACHE)} Verse)")
        except Exception as e:
            log("BoM JSON konnte nicht geladen werden:", repr(e))
            _BOM_CACHE = []
    return _BOM_CACHE

# Persistent Settings
def _load_settings() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log("settings.json laden fehlgeschlagen:", repr(e))
        return {}

def _save_settings(data: dict):
    tmp = SETTINGS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SETTINGS_FILE)

SETTINGS = _load_settings()

def cfg_get(name: str, default=None):
    if name in SETTINGS:
        return SETTINGS[name]
    return os.getenv(name, default)

def cfg_get_int(name: str, default: int) -> int:
    try:
        return int(cfg_get(name, default))
    except:
        return default

def cfg_get_float(name: str, default: float) -> float:
    try:
        return float(cfg_get(name, default))
    except:
        return default

def cfg_get_bool(name: str, default: bool) -> bool:
    v = str(cfg_get(name, default)).lower()
    return v in ("1", "true", "yes", "on", "y", "t")

# Helpers for Receipt Rendering
def _safe_font(path_or_name: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path_or_name, size=size)
    except Exception:
        for cand in ("DejaVuSans.ttf", "Arial.ttf"):
            try:
                return ImageFont.truetype(cand, size=size)
            except:
                pass
    return ImageFont.load_default()

def _textlength(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    try:
        return int(draw.textlength(text, font=font))
    except Exception:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]

def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_px: int) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    lines, cur = [], words[0]
    for w in words[1:]:
        t = f"{cur} {w}"
        if _textlength(draw, t, font) <= max_px:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines

class ReceiptCfg:
    def __init__(self):
        self.preset = str(cfg_get("RECEIPT_PRESET", "clean")).lower()

        self.title_size = 36
        self.text_size = 28
        self.time_size = 24

        self.title_font_name = cfg_get("RECEIPT_TITLE_FONT", "DejaVuSans.ttf")
        self.text_font_name = cfg_get("RECEIPT_TEXT_FONT", "DejaVuSans.ttf")
        self.time_font_name = cfg_get("RECEIPT_TIME_FONT", "DejaVuSans.ttf")

        self.margin_top = 28
        self.margin_bottom = 18
        self.margin_left = 18
        self.margin_right = 18

        self.gap_title_text = 10
        self.line_height_mult = 1.15

        self.align_title = cfg_get("RECEIPT_ALIGN_TITLE", "left")
        self.align_text = cfg_get("RECEIPT_ALIGN_TEXT", "left")
        self.align_time = cfg_get("RECEIPT_ALIGN_TIME", "left")

        self.time_show_minutes = cfg_get_bool("RECEIPT_TIME_SHOW_MINUTES", True)
        self.time_show_seconds = cfg_get_bool("RECEIPT_TIME_SHOW_SECONDS", False)
        self.time_prefix = cfg_get("RECEIPT_TIME_PREFIX", "")

        self.rule_after_title = cfg_get_bool("RECEIPT_RULE_AFTER_TITLE", False)
        self.rule_px = cfg_get_int("RECEIPT_RULE_PX", 1)
        self.rule_pad = cfg_get_int("RECEIPT_RULE_PAD", 6)

        if self.preset == "compact":
            self.title_size, self.text_size, self.time_size = 30, 24, 22
            self.margin_top, self.margin_bottom = 16, 12
            self.gap_title_text = 6
            self.line_height_mult = 1.05
        elif self.preset == "bigtitle":
            self.title_size = 44
            self.gap_title_text = 14
            self.rule_after_title = True

        # Explicit overrides
        self.title_size = cfg_get_int("RECEIPT_TITLE_SIZE", self.title_size)
        self.text_size = cfg_get_int("RECEIPT_TEXT_SIZE", self.text_size)
        self.time_size = cfg_get_int("RECEIPT_TIME_SIZE", self.time_size)

        self.margin_top = cfg_get_int("RECEIPT_MARGIN_TOP", self.margin_top)
        self.margin_bottom = cfg_get_int("RECEIPT_MARGIN_BOTTOM", self.margin_bottom)
        self.margin_left = cfg_get_int("RECEIPT_MARGIN_LEFT", self.margin_left)
        self.margin_right = cfg_get_int("RECEIPT_MARGIN_RIGHT", self.margin_right)

        self.gap_title_text = cfg_get_int("RECEIPT_GAP_TITLE_TEXT", self.gap_title_text)
        self.line_height_mult = cfg_get_float("RECEIPT_LINE_HEIGHT", self.line_height_mult)

        self.font_title = _safe_font(self.title_font_name, self.title_size)
        self.font_text = _safe_font(self.text_font_name, self.text_size)
        self.font_time = _safe_font(self.time_font_name, self.time_size)

def _x_for_align(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
                 width: int, align: str, ml: int, mr: int) -> int:
    usable = width - ml - mr
    tl = _textlength(draw, text, font)
    if align == "center":
        return ml + max(0, (usable - tl) // 2)
    if align == "right":
        return width - mr - tl
    return ml

def _time_str(cfg: ReceiptCfg) -> str:
    fmt = "%Y-%m-%d %H"
    if cfg.time_show_minutes or cfg.time_show_seconds:
        fmt += ":%M"
    if cfg.time_show_seconds:
        fmt += ":%S"
    s = datetime.now(TZ).strftime(fmt)
    return (cfg.time_prefix + s).strip()

def render_receipt(
    title: str,
    lines: List[str],
    add_time: bool,
    width_px: int,
    cfg: ReceiptCfg,
    sender_name: str | None = None
) -> Image.Image:
    bg = 255
    img = Image.new("L", (width_px, 10), color=bg)
    draw = ImageDraw.Draw(img)
    cur_y = cfg.margin_top
    max_w = width_px - cfg.margin_left - cfg.margin_right

    title_lines = _wrap(draw, title.strip(), cfg.font_title, max_w) if title else []
    for ln in title_lines:
        x = _x_for_align(draw, ln, cfg.font_title, width_px, cfg.align_title, cfg.margin_left, cfg.margin_right)
        draw.text((x, cur_y), ln, fill=0, font=cfg.font_title)
        ascent, descent = cfg.font_title.getmetrics()
        cur_y += int((ascent + descent) * cfg.line_height_mult)

    if title_lines:
        if cfg.rule_after_title:
            cur_y += cfg.rule_pad
            draw.rectangle((cfg.margin_left, cur_y, width_px - cfg.margin_right, cur_y + cfg.rule_px), fill=0)
            cur_y += cfg.rule_px + cfg.rule_pad
        else:
            cur_y += cfg.gap_title_text

    if sender_name:
        tag = f"Von: {sender_name}"
        x = _x_for_align(draw, tag, cfg.font_time, width_px, cfg.align_time, cfg.margin_left, cfg.margin_right)
        draw.text((x, cur_y), tag, fill=0, font=cfg.font_time)
        ascent, descent = cfg.font_time.getmetrics()
        cur_y += int((ascent + descent) * cfg.line_height_mult)

    if add_time:
        t = _time_str(cfg)
        x = _x_for_align(draw, t, cfg.font_time, width_px, cfg.align_time, cfg.margin_left, cfg.margin_right)
        draw.text((x, cur_y), t, fill=0, font=cfg.font_time)
        ascent, descent = cfg.font_time.getmetrics()
        cur_y += int((ascent + descent) * cfg.line_height_mult)

    for raw in lines:
        if not raw.strip():
            ascent, descent = cfg.font_text.getmetrics()
            cur_y += int((ascent + descent) * cfg.line_height_mult)
            continue
        for ln in _wrap(draw, raw.strip(), cfg.font_text, max_w):
            x = _x_for_align(draw, ln, cfg.font_text, width_px, cfg.align_text, cfg.margin_left, cfg.margin_right)
            draw.text((x, cur_y), ln, fill=0, font=cfg.font_text)
            ascent, descent = cfg.font_text.getmetrics()
            cur_y += int((ascent + descent) * cfg.line_height_mult)

    cur_y += cfg.margin_bottom
    out = Image.new("L", (width_px, cur_y), color=bg)
    out.paste(img, (0, 0))
    return out

def render_image_with_headers(
    image: Image.Image,
    width_px: int,
    cfg: ReceiptCfg,
    title: str | None = None,
    subtitle: str | None = None,
    sender_name: str | None = None
) -> Image.Image:
    if image.mode != "L":
        image = image.convert("L")
    w, h = image.size
    if w != width_px:
        image = image.resize((width_px, int(h * (width_px / w))))
    header_title = title.strip() if title else ""
    header_lines = [subtitle.strip()] if (subtitle and subtitle.strip()) else []
    head = render_receipt(header_title, header_lines, add_time=False, width_px=width_px, cfg=cfg, sender_name=sender_name)
    out = Image.new("L", (width_px, head.height + image.height), color=255)
    out.paste(head, (0, 0))
    out.paste(image, (0, head.height))
    return out

# Security functions
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

def ui_auth_state(request: Request, pass_: str | None, remember: bool) -> tuple[bool, bool]:
    if require_ui_auth(request):
        return True, False
    if pass_ is not None and pass_ == UI_PASS:
        return True, bool(remember)
    return False, False

# Helper to consume Guest token (ensures imported and callable)
def guest_consume_or_error(token: str) -> dict | None:
    return GUESTS.consume(token)

# Settings helpers
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
]

def settings_effective() -> dict:
    eff = {}
    for key, default, _, _ in SET_KEYS:
        eff[key] = cfg_get(key, default)
    return eff
