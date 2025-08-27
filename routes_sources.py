# routes_sources.py
import os
import io
import importlib
from typing import Optional, Union, Dict, Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from logic import (
    render_receipt,
    pil_to_base64_png,
    mqtt_publish_image_base64,
    ReceiptCfg,
)

router = APIRouter()

APP_API_KEY = os.getenv("APP_API_KEY")
PRINT_WIDTH_PX = int(os.getenv("PRINT_WIDTH_PX", "384"))


def _check_api_key(request: Request) -> None:
    if not APP_API_KEY:
        return
    token = request.headers.get("x-api-key", "")
    if token != APP_API_KEY:
        raise HTTPException(status_code=401, detail="invalid x-api-key")


def _render_png_bytes(title: str, lines: list[str]) -> bytes:
    cfg = ReceiptCfg()
    img = render_receipt(title, lines, add_time=True, width_px=PRINT_WIDTH_PX, cfg=cfg)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def _normalize_source_result(
    value: Union[str, Dict[str, Any]],
    default_title: str,
) -> tuple[str, list[str]]:
    """
    Akzeptiert:
      - str  -> wird als eine Zeile gedruckt, Titel = default_title
      - dict -> erwartet {"title": "...", "lines": ["...","..."]} (Titel optional)
    """
    if isinstance(value, dict):
        title = (value.get("title") or default_title).strip()
        lines = value.get("lines")
        if not isinstance(lines, list) or not all(isinstance(x, str) for x in lines):
            # Fallback: wenn eine "text" Eigenschaft vorhanden ist, nutze diese
            txt = value.get("text")
            lines = [str(txt)] if txt is not None else []
        return title, [ln.strip() for ln in lines if str(ln).strip()]
    # string fallback
    return default_title, [str(value).strip()]


@router.api_route("/api/print/source/{name}", methods=["GET", "POST"])
async def print_from_source(
    name: str,
    request: Request,
    as_png: Optional[bool] = False,
    also_print: Optional[bool] = True,
    title: Optional[str] = None,
):
    """
    Generischer Druck-Endpunkt fuer modulare Quellen unter sources/{name}.py

    Jede Quelle exportiert eine Klasse `Source` mit:
        async def get_text(self) -> str | dict
    Rueckgabe:
        - str: eine Zeile; Titel = name.upper() oder ?title
        - dict: {"title": "...", "lines": ["..."]}  (title optional)

    Query:
      - as_png=1       -> gibt image/png statt JSON (Preview)
      - also_print=0   -> kein MQTT-Druck
      - title=...      -> optional Titel ueberschreiben
    """
    _check_api_key(request)

    # Modul dynamisch laden
    try:
        mod = importlib.import_module(f"sources.{name}")
        Source = getattr(mod, "Source")
        src = Source()
        result = await src.get_text()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"source '{name}' failed: {e}")

    # Titel/Zeilen normalisieren
    default_title = (title or name).upper()
    belegtitel, lines = _normalize_source_result(result, default_title)

    if as_png:
        png = _render_png_bytes(belegtitel, lines)
        return StreamingResponse(io.BytesIO(png), media_type="image/png")

    printed = False
    if also_print:
        cfg = ReceiptCfg()
        img = render_receipt(belegtitel, lines, add_time=True, width_px=PRINT_WIDTH_PX, cfg=cfg)
        b64 = pil_to_base64_png(img)
        mqtt_publish_image_base64(b64, cut_paper=1)
        printed = True

    return JSONResponse({"ok": True, "printed": printed, "source": name, "title": belegtitel, "lines": lines})
