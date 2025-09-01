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

# routes_sources.py

@router.api_route("/api/print/source/{name}", methods=["GET", "POST"])
async def print_from_source(
    name: str,
    request: Request,
    as_png: Optional[bool] = False,
    also_print: Optional[bool] = True,
    title: Optional[str] = None,
    places: Optional[str] = None,   # <— NEU: query param
):
    _check_api_key(request)

    try:
        mod = importlib.import_module(f"sources.{name}")
        Source = getattr(mod, "Source")
        src = Source()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"load '{name}' failed: {e}")

    # --- NEU: kwargs vorbereiten ---
    kwargs = {}
    if places:
        kwargs["places"] = places

    result = None
    if as_png and hasattr(src, "get_png"):
        result = await src.get_png(**kwargs)
    else:
        result = await src.get_text(**kwargs)

    if as_png:
        # result ist PNG-Bytes
        return StreamingResponse(io.BytesIO(result), media_type="image/png")

    default_title = (title or ("" if name == "quote" else name)).upper()
    belegtitel, lines = _normalize_source_result(result, default_title)

    if also_print:
        cfg = ReceiptCfg()
        img = render_receipt(belegtitel, lines, add_time=False, width_px=PRINT_WIDTH_PX, cfg=cfg)
        b64 = pil_to_base64_png(img)
        enqueue_base64_png(b64, cut_paper=1, meta={"source": name, "title": belegtitel})

    return JSONResponse({"ok": True, "source": name, "title": belegtitel, "lines": lines})

