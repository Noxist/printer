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
    ReceiptCfg,
)
from queue_print import enqueue_base64_png  # <— OBEN importieren

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
    # ohne Zeitstempel
    img = render_receipt(title, lines, add_time=False, width_px=PRINT_WIDTH_PX, cfg=cfg)
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
      - str  -> eine Zeile, Titel = default_title
      - dict -> {"title": "...", "lines": ["..."]}  (title optional)
    """
    if isinstance(value, dict):
        title = (value.get("title") or default_title).strip()
        lines = value.get("lines")
        if not isinstance(lines, list) or not all(isinstance(x, str) for x in lines):
            txt = value.get("text")
            lines = [str(txt)] if txt is not None else []
        return title, [ln.strip() for ln in lines if str(ln).strip()]
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
    Generischer Druck-Endpunkt fuer sources/{name}.py

    Quelle exportiert:
        class Source:
            async def get_text(self) -> str | dict
    Rueckgabe:
        - str  -> Zeile
        - dict -> {"title": "...", "lines": ["..."]}
    """
    _check_api_key(request)

    # Modul laden und Daten holen
    try:
        mod = importlib.import_module(f"sources.{name}")
        Source = getattr(mod, "Source")
        src = Source()
        result = await src.get_text()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"source '{name}' failed: {e}")

    default_title = (title or ("" if name == "quote" else name)).upper()
    belegtitel, lines = _normalize_source_result(result, default_title)

    # PNG-Preview
    if as_png:
        png = _render_png_bytes(belegtitel, lines)
        return StreamingResponse(io.BytesIO(png), media_type="image/png")

    # Drucken (über Queue, ohne Zeitstempel)
    printed = False
    if also_print:
        cfg = ReceiptCfg()
        img = render_receipt(belegtitel, lines, add_time=False, width_px=PRINT_WIDTH_PX, cfg=cfg)
        b64 = pil_to_base64_png(img)
        enqueue_base64_png(b64, cut_paper=1, meta={"source": name, "title": belegtitel})
        printed = True  # angenommen (wird nachgedruckt, wenn der Drucker wieder online ist)

    return JSONResponse({"ok": True, "printed": printed, "source": name, "title": belegtitel, "lines": lines})
