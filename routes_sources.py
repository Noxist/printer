import os, io, importlib
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from logic import render_receipt, pil_to_base64_png, mqtt_publish_image_base64, ReceiptCfg

router = APIRouter()

APP_API_KEY = os.getenv("APP_API_KEY")
PRINT_WIDTH_PX = int(os.getenv("PRINT_WIDTH_PX", "384"))

def _check_api_key(request: Request):
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

@router.post("/api/print/source/{name}")
async def print_from_source(
    name: str,
    request: Request,
    as_png: Optional[bool] = False,
    also_print: Optional[bool] = True,
    title: Optional[str] = None,
):
    """
    Generischer Druck-Endpunkt:
      - name: modul unter sources/, das eine Klasse Source mit async get_text() bereitstellt
      - ?as_png=1     -> PNG Preview
      - ?also_print=0 -> kein MQTT Druck
      - ?title=...    -> optionaler Beleg-Titel (default: NAME upper)
    """
    _check_api_key(request)

    try:
        mod = importlib.import_module(f"sources.{name}")
        Source = getattr(mod, "Source")
        src = Source()
        text = await src.get_text()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"source '{name}' failed: {e}")

    belegtitel = (title or name).upper()
    lines = [text]

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

    return JSONResponse({"ok": True, "printed": printed, "source": name, "text": text})
