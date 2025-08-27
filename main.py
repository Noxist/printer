import os
import io
import random
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from pydantic import BaseModel
from PIL import Image

from logic import (
    log,
    now_str,
    pil_to_base64_png,
    mqtt_publish_image_base64,
    render_receipt,
    render_image_with_headers,
    ReceiptCfg,
    check_api_key,
    require_ui_auth,
    issue_cookie,
    ui_auth_state,
    cfg_get,
    SETTINGS,
    SET_KEYS,
    _save_settings,
    GUESTS,
    guest_consume_or_error,
)
from ui_html import html_page, HTML_UI, settings_html_form, guest_ui_html

from api_bom import router as bom_router  # BOM API als separater router einbinden

app = FastAPI(title="Printer API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(bom_router)  # Register BOM APIs

PRINT_WIDTH_PX = int(cfg_get("PRINT_WIDTH_PX", 576))

class PrintPayload(BaseModel):
    title: str = "TASKS"
    lines: list[str] = []
    cut: bool = True
    add_datetime: bool = True

class RawPayload(BaseModel):
    text: str
    add_datetime: bool = False

@app.get("/_health", response_class=PlainTextResponse)
def health():
    return "OK"

@app.get("/")
def ok():
    from logic import TOPIC, PUBLISH_QOS
    return {"ok": True, "topic": TOPIC, "qos": PUBLISH_QOS}

# Print Endpoints
@app.post("/print")
async def print_job(p: PrintPayload, request: Request):
    check_api_key(request)
    cfg = ReceiptCfg()
    img = render_receipt(p.title, p.lines, add_time=p.add_datetime, width_px=PRINT_WIDTH_PX, cfg=cfg)
    b64 = pil_to_base64_png(img)
    mqtt_publish_image_base64(b64, cut_paper=(1 if p.cut else 0))
    return {"ok": True}

@app.post("/api/print/template")
async def api_print_template(p: PrintPayload, request: Request):
    check_api_key(request)
    cfg = ReceiptCfg()
    img = render_receipt(p.title, p.lines, add_time=p.add_datetime, width_px=PRINT_WIDTH_PX, cfg=cfg)
    b64 = pil_to_base64_png(img)
    mqtt_publish_image_base64(b64, cut_paper=(1 if p.cut else 0))
    return {"ok": True}

@app.post("/api/print/raw")
async def api_print_raw(p: RawPayload, request: Request):
    check_api_key(request)
    cfg = ReceiptCfg()
    lines = (p.text + (f"\n{now_str('%Y-%m-%d %H:%M')}" if p.add_datetime else "")).splitlines()
    img = render_receipt("", lines, add_time=False, width_px=PRINT_WIDTH_PX, cfg=cfg)
    b64 = pil_to_base64_png(img)
    mqtt_publish_image_base64(b64, cut_paper=1)
    return {"ok": True}

@app.post("/api/print/image")
async def api_print_image(
    request: Request,
    file: UploadFile = File(...),
    img_title: str | None = Form(None),
    img_subtitle: str | None = Form(None),
):
    check_api_key(request)
    content = await file.read()
    src = render_image_with_headers(
        Image.open(io.BytesIO(content)),
        PRINT_WIDTH_PX,
        ReceiptCfg(),
        title=img_title,
        subtitle=img_subtitle
    )
    b64 = pil_to_base64_png(src)
    mqtt_publish_image_base64(b64, cut_paper=1)
    return {"ok": True}

# UI endpoints
@app.get("/ui", response_class=HTMLResponse)
def ui(request: Request):
    auth_required = "false" if require_ui_auth(request) else ("true" if cfg_get("UI_PASS") else "false")
    html = HTML_UI.replace("{{AUTH_REQUIRED}}", auth_required)
    return html_page("Quittungsdruck", html)

@app.get("/ui/logout")
def ui_logout():
    r = RedirectResponse("/ui", status_code=303)
    r.delete_cookie("ui_token", path="/")
    return r

def ui_handle_auth_and_cookie(request: Request, pass_: str | None, remember: bool) -> tuple[bool, bool]:
    authed, should_set_cookie = ui_auth_state(request, pass_, remember)
    if not authed:
        return False, False
    return True, should_set_cookie

@app.post("/ui/print/template")
async def ui_print_template(
    request: Request,
    title: str = Form("TASKS"),
    lines: str = Form(""),
    add_dt: bool = Form(False),
    pass_: str | None = Form(None, alias="pass"),
    remember: bool = Form(False)
):
    authed, set_cookie = ui_handle_auth_and_cookie(request, pass_, remember)
    if not authed:
        return html_page("Quittungsdruck", "<div class='card'>Falsches Passwort.</div>")
    try:
        cfg = ReceiptCfg()
        img = render_receipt(title.strip(), [ln.rstrip() for ln in lines.splitlines()], add_time=add_dt, width_px=PRINT_WIDTH_PX, cfg=cfg)
        b64 = pil_to_base64_png(img)
        mqtt_publish_image_base64(b64, cut_paper=1)
        resp = RedirectResponse("/ui#tpl", status_code=303)
        if set_cookie:
            issue_cookie(resp)
        return resp
    except Exception as e:
        log("ui_print_template error:", repr(e))
        return html_page("Quittungsdruck", f"<div class='card'>Fehler: {e}</div>")

@app.post("/ui/print/raw")
async def ui_print_raw(
    request: Request,
    text: str = Form(""),
    add_dt: bool = Form(False),
    pass_: str | None = Form(None, alias="pass"),
    remember: bool = Form(False)
):
    authed, set_cookie = ui_handle_auth_and_cookie(request, pass_, remember)
    if not authed:
        return html_page("Quittungsdruck", "<div class='card'>Falsches Passwort.</div>")
    try:
        cfg = ReceiptCfg()
        lines = (text + (f"\n{now_str('%Y-%m-%d %H:%M')}" if add_dt else "")).splitlines()
        img = render_receipt("", lines, add_time=False, width_px=PRINT_WIDTH_PX, cfg=cfg)
        b64 = pil_to_base64_png(img)
        mqtt_publish_image_base64(b64, cut_paper=1)
        resp = RedirectResponse("/ui#raw", status_code=303)
        if set_cookie:
            issue_cookie(resp)
        return resp
    except Exception as e:
        log("ui_print_raw error:", repr(e))
        return html_page("Quittungsdruck", f"<div class='card'>Fehler: {e}</div>")

@app.post("/ui/print/image")
async def ui_print_image(
    request: Request,
    file: UploadFile = File(...),
    img_title: str | None = Form(None),
    img_subtitle: str | None = Form(None),
    pass_: str | None = Form(None, alias="pass"),
    remember: bool = Form(False),
):
    authed, set_cookie = ui_handle_auth_and_cookie(request, pass_, remember)
    if not authed:
        return html_page("Quittungsdruck", "<div class='card'>Falsches Passwort.</div>")
    try:
        content = await file.read()
        src = Image.open(io.BytesIO(content))
        cfg = ReceiptCfg()
        composed = render_image_with_headers(src, PRINT_WIDTH_PX, cfg, title=img_title, subtitle=img_subtitle)
        b64 = pil_to_base64_png(composed)
        mqtt_publish_image_base64(b64, cut_paper=1)
        resp = RedirectResponse("/ui#img", status_code=303)
        if set_cookie:
            issue_cookie(resp)
        return resp
    except Exception as e:
        log("ui_print_image error:", repr(e))
        return html_page("Quittungsdruck", f"<div class='card'>Fehler: {e}</div>")

# Guest UI and print endpoints
@app.get("/guest/{token}", response_class=HTMLResponse)
def guest_ui(token: str, request: Request):
    info = GUESTS.validate(token)
    if not info:
        return html_page("Gast", "<div class='card'>Ungültiger oder deaktivierter Link.</div>")
    remaining = GUESTS.remaining_today(token)
    content = f"<div class='card'>Gast: <b>{info['name']}</b> · heute übrig: {remaining}</div>" + guest_ui_html("false")
    content = content.replace('/ui/print/template', f'/guest/{token}/print/template')
    content = content.replace('/ui/print/raw', f'/guest/{token}/print/raw')
    content = content.replace('/ui/print/image', f'/guest/{token}/print/image')
    return html_page("Gastdruck", content)

@app.post("/guest/{token}/print/template")
async def guest_print_template(
    token: str,
    title: str = Form("TASKS"),
    lines: str = Form(""),
    add_dt: bool = Form(False),
):
    tok = guest_consume_or_error(token)
    if not tok:
        return html_page("Gastdruck", "<div class='card'>Limit erreicht oder Link ungültig.</div>")
    cfg = ReceiptCfg()
    img = render_receipt(title.strip(), [ln.rstrip() for ln in lines.splitlines()], add_time=add_dt,
                         width_px=PRINT_WIDTH_PX, cfg=cfg, sender_name=tok["name"])
    b64 = pil_to_base64_png(img)
    mqtt_publish_image_base64(b64, cut_paper=1)
    return RedirectResponse(f"/guest/{token}#tpl", status_code=303)

@app.post("/guest/{token}/print/raw")
async def guest_print_raw(
    token: str,
    text: str = Form(""),
    add_dt: bool = Form(False),
):
    tok = guest_consume_or_error(token)
    if not tok:
        return html_page("Gastdruck", "<div class='card'>Limit erreicht oder Link ungültig.</div>")
    cfg = ReceiptCfg()
    lines = (text + (f"\n{now_str('%Y-%m-%d %H:%M')}" if add_dt else "")).splitlines()
    img = render_receipt("", lines, add_time=False, width_px=PRINT_WIDTH_PX, cfg=cfg, sender_name=tok["name"])
    b64 = pil_to_base64_png(img)
    mqtt_publish_image_base64(b64, cut_paper=1)
    return RedirectResponse(f"/guest/{token}#raw", status_code=303)

@app.post("/guest/{token}/print/image")
async def guest_print_image(
    token: str,
    file: UploadFile = File(...),
    img_title: str | None = Form(None),
    img_subtitle: str | None = Form(None),
):
    tok = guest_consume_or_error(token)
    if not tok:
        return html_page("Gastdruck", "<div class='card'>Limit erreicht oder Link ungültig.</div>")
    content = await file.read()
    src = Image.open(io.BytesIO(content))
    cfg = ReceiptCfg()
    composed = render_image_with_headers(src, PRINT_WIDTH_PX, cfg, title=img_title, subtitle=img_subtitle,
                                         sender_name=tok["name"])
    b64 = pil_to_base64_png(composed)
    mqtt_publish_image_base64(b64, cut_paper=1)
    return RedirectResponse(f"/guest/{token}#img", status_code=303)

# Settings UI and handling
@app.get("/ui/settings", response_class=HTMLResponse)
def ui_settings(request: Request):
    if not require_ui_auth(request):
        return html_page("Einstellungen", "<div class='card'>Nicht angemeldet.</div>")
    content = "<h3 class='title'>Einstellungen</h3>" + settings_html_form()
    return html_page("Einstellungen", content)

@app.post("/ui/settings/save", response_class=HTMLResponse)
async def ui_settings_save(request: Request):
    if not require_ui_auth(request):
        return html_page("Einstellungen", "<div class='card'>Nicht angemeldet.</div>")
    form = await request.form()
    for key, default, typ, _ in SET_KEYS:
        if typ == "checkbox":
            SETTINGS[key] = True if form.get(key) else False
        else:
            val = form.get(key)
            if val is None:
                SETTINGS[key] = default
            else:
                if typ == "number":
                    try:
                        SETTINGS[key] = int(val) if "." not in val else float(val)
                    except:
                        SETTINGS[key] = default
                else:
                    SETTINGS[key] = val
    _save_settings(SETTINGS)
    return RedirectResponse("/ui/settings", status_code=303)

@app.get("/ui/settings/test", response_class=HTMLResponse)
def ui_settings_test(request: Request):
    if not require_ui_auth(request):
        return html_page("Einstellungen", "<div class='card'>Nicht angemeldet.</div>")
    cfg = ReceiptCfg()
    sample_lines = [
        "Schriftstelle lesen",
        "Wasser trinken",
        "Planung – 10 Min",
        "Sport – 20 Min"
    ]
    img = render_receipt("TEST", sample_lines, add_time=True, width_px=PRINT_WIDTH_PX, cfg=cfg)
    b64 = pil_to_base64_png(img)
    mqtt_publish_image_base64(b64, cut_paper=1)
    return html_page("Einstellungen", "<div class='card'>Testdruck gesendet.</div>")
from fastapi.responses import FileResponse

@app.get("/debug/last")
async def debug_last():
    path = "/tmp/last_print.png"
    if os.path.exists(path):
        return FileResponse(path, media_type="image/png")
    return {"error": "no debug file found"}

def _render_guests_admin() -> str:
    rows = []
    for token, info in GUESTS.list():
        name = info.get("name","Gast")
        created = info.get("created", 0)
        active = "aktiv" if info.get("active") else "inaktiv"
        quota = info.get("quota_per_day",5)
        rows.append(
            f"<tr><td><code style='font-size:.9em'>{token}</code></td>"
            f"<td>{name}</td><td>{active}</td><td>{quota}/Tag</td>"
            f"<td><form method='post' action='/ui/guests/revoke' style='display:inline'>"
            f"<input type='hidden' name='token' value='{token}'><button class='secondary'>Revoke</button></form></td></tr>"
        )
    table = "<table style='width:100%; border-collapse:collapse'>"
    table += "<tr><th style='text-align:left'>Token</th><th>Name</th><th>Status</th><th>Quota</th><th>Aktion</th></tr>"
    table += "".join(rows) if rows else "<tr><td colspan='5'>Keine Tokens vorhanden.</td></tr>"
    table += "</table>"

    form = """
    <div class='card' style='margin-top:14px'>
      <form method='post' action='/ui/guests/create' class='row' style='gap:10px'>
        <input type='text' name='name' placeholder='Name' style='max-width:240px'>
        <input type='number' name='quota' value='5' min='1' step='1' style='max-width:120px'>
        <button type='submit'>Token erstellen</button>
      </form>
    </div>
    """
    return "<section class='card'><h3 class='title'>Gaeste</h3>"+table+"</section>"+form

@app.get("/ui/guests", response_class=HTMLResponse)
def ui_guests(request: Request):
    if not require_ui_auth(request):
        return html_page("Gaeste", "<div class='card'>Nicht angemeldet.</div>")
    return html_page("Gaeste", _render_guests_admin())

@app.post("/ui/guests/create", response_class=HTMLResponse)
async def ui_guests_create(request: Request):
    if not require_ui_auth(request):
        return html_page("Gaeste", "<div class='card'>Nicht angemeldet.</div>")
    form = await request.form()
    name = (form.get("name") or "Gast").strip()
    quota = int((form.get("quota") or 5))
    token = GUESTS.create(name, quota_per_day=quota)
    return html_page("Gaeste", f"<div class='card'>Token erstellt: <code>{token}</code></div>"+_render_guests_admin())

@app.post("/ui/guests/revoke", response_class=HTMLResponse)
async def ui_guests_revoke(request: Request):
    if not require_ui_auth(request):
        return html_page("Gaeste", "<div class='card'>Nicht angemeldet.</div>")
    form = await request.form()
    tok = form.get("token") or ""
    ok = GUESTS.revoke(tok)
    msg = "Token deaktiviert." if ok else "Token nicht gefunden."
    return html_page("Gaeste", f"<div class='card'>{msg}</div>"+_render_guests_admin())
