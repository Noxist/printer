# api_bom.py

from fastapi import APIRouter, Request
import random
from logic import (
    check_api_key,
    _get_bom_data,
    render_receipt,
    pil_to_base64_png,
    mqtt_publish_image_base64,
    ReceiptCfg,
    log,
    PRINT_WIDTH_PX
)

router = APIRouter()

@router.post("/api/print/bom/random")
async def api_print_bom_random(request: Request):
    check_api_key(request)
    try:
        data = _get_bom_data()
    except Exception as e:
        log("Fehler beim Laden des BoM JSON:", repr(e))
        data = []

    if not isinstance(data, list) or not data:
        ref = "Book of Mormon"
        text = "Konnte keinen Vers laden (Quelle nicht erreichbar)."
    else:
        try:
            v = random.choice(data)
            ref = v.get("reference") or f"{v.get('book')} {v.get('chapter')}:{v.get('verse')}"
            text = (v.get("text") or "").strip()
            if not text:
                text = "Vers ohne Text (Daten unvollständig)."
        except Exception as e:
            log("Fehler beim Zufallsauswahl:", repr(e))
            ref, text = "Book of Mormon", "Fehler bei der Auswahl eines Verses."

    cfg = ReceiptCfg()
    img = render_receipt(ref, [text], add_time=True, width_px=PRINT_WIDTH_PX, cfg=cfg)
    b64 = pil_to_base64_png(img)
    mqtt_publish_image_base64(b64, cut_paper=1)

    return {"ok": True, "reference": ref, "text": text}
