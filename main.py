# main.py
import os
import io
import shutil
import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse, RedirectResponse, PlainTextResponse, 
    FileResponse, JSONResponse
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image

# --- Local Modules ---
from queue_print import (
    start_background_flusher, stop_background_flusher, 
    enqueue_base64_png, PRINT_QUEUE_DIR
)
from routes_sources import router as sources_router
from logic import (
    log, now_str, pil_to_base64_png, render_receipt, render_image_with_headers,
    ReceiptCfg, check_api_key, require_ui_auth, issue_cookie, ui_auth_state,
    cfg_get, SETTINGS, SET_KEYS, _save_settings, _reload_settings_if_changed,
    GUESTS, guest_consume_or_error, _guest_check_len_ok, GUEST_MAX_CHARS,
)
from ui_html import html_page, HTML_UI, settings_html_form, guest_ui_html

# --- Lifecycle & Startup ------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[main] 🧩 Starte Printer-App …")
    try:
        stop_background_flusher()
        print("[main] 🛑 Alte Queue-Threads gestoppt.")
    except Exception as e:
        print("[main] ⚠️ Konnte alten Thread nicht stoppen:", e)
    
    start_background_flusher()
    print("[main] ✅ Druck-Queue frisch gestartet.")
    yield
    stop_background_flusher()
    print("[main] 👋 App shutdown.")

app = FastAPI(title="Printer API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources_router)

# --- Globals & Constants ------------------------------------------------------

PRINT_WIDTH_PX = int(cfg_get("PRINT_WIDTH_PX", 576))

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- Helpers ------------------------------------------------------------------

def _print_text_content(title: str, lines: list[str], add_dt: bool, 
                        cut: bool, source: str, sender: str = None):
    """Helper: Renders text to image and enqueues it."""
    cfg = ReceiptCfg()
    img = render_receipt(
        title, lines, add_time=add_dt, width_px=PRINT_WIDTH_PX, 
        cfg=cfg, sender_name=sender
    )
    b64 = pil_to_base64_png(img)
    enqueue_base64_png(b64, cut_paper=(1 if cut else 0), meta={"source": source})

def _print_image_content(img_obj: Image.Image, title: str, subtitle: str, 
                         cut: bool, source: str, sender: str = None):
    """Helper: Renders headers + image and enqueues it."""
    cfg = ReceiptCfg()
    img = render_image_with_headers(
        img_obj, PRINT_WIDTH_PX, cfg, 
        title=title, subtitle=subtitle, sender_name=sender
    )
    b64 = pil_to_base64_png(img)
    enqueue_base64_png(b64, cut_paper=(1 if cut else 0), meta={"source": source})

# --- Models -------------------------------------------------------------------
class PrintPayload(BaseModel):
    title: str = ""
    lines: list[str] = []
    cut: bool = True
    add_datetime: bool = True

class RawPayload(BaseModel):
    text: str
    add_datetime: bool = False

# --- Routes: Health / Root ----------------------------------------------------
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    path = os.path.join(static_dir, "favicon.ico")
    if os.path.exists(path):
        return FileResponse(path)
    return FileResponse(os.path.join(static_dir, "favicon.png"))

@app.get("/_health", response_class=PlainTextResponse)
def health():
    return "OK"

@app.get("/")
def ok():
    from logic import TOPIC, PUBLISH_QOS
    return {"ok": True, "topic": TOPIC, "qos": PUBLISH_QOS}

# --- Routes: API (JSON) -------------------------------------------------------
@app.post("/print")
async def print_job(p: PrintPayload, request: Request):
    check_api_key(request)
    if (not p.title.strip()) and (not any(line.strip() for line in p.lines)):
        log("⚠️ Leerer PrintJob – wird übersprungen.")
        return {"ok": False, "msg": "Empty print job ignored."}

    _print_text_content(p.title, p.lines, p.add_datetime, p.cut, "api")
    return {"ok": True}

@app.post("/api/print/template")
async def api_print_template(p: PrintPayload, request: Request):
    check_api_key(request)
    if (not p.title.strip() or p.title.strip().lower() == "tasks") and not any(line.strip() for line in p.lines):
        log("⚠️ Leeres Template oder Defaulttitel – wird nicht gedruckt.")
        return {"ok": False, "msg": "Empty or default template ignored."}

    _print_text_content(p.title, p.lines, p.add_datetime, p.cut, "api")
    return {"ok": True}

@app.post("/api/print/raw")
async def api_print_raw(p: RawPayload, request: Request):
    check_api_key(request)
    if not p.text.strip():
        log("⚠️ Leerer Raw-Text – Druck übersprungen.")
        return {"ok": False, "msg": "Empty raw print ignored."}

    lines = (p.text + (f"\n{now_str('%Y-%m-%d %H:%M')}" if p.add_datetime else "")).splitlines()
    _print_text_content("", lines, False, True, "api") 
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
    if not content:
        return {"ok": False, "msg": "Empty image ignored."}

    src = Image.open(io.BytesIO(content))
    _print_image_content(src, img_title, img_subtitle, True, "api")
    return {"ok": True}

# --- Routes: UI (HTML) --------------------------------------------------------
@app.get("/ui", response_class=HTMLResponse)
def ui(request: Request):
    # Determine Auth State
    pass_configured = bool(cfg_get("UI_PASS"))
    is_authed = require_ui_auth(request)
    
    # Force login reload (e.g. after logout)
    if request.query_params.get("force_reload") == "1":
        is_authed = False

    # Logic: Show auth fields if password is set AND user is NOT authed
    auth_required_bool = (pass_configured and not is_authed)
    
    # Logic: Show logout only if password is set AND user IS authed
    show_logout = is_authed and pass_configured

    # No-Cache headers
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    if request.headers.get("X-Partial") == "true":
        # For partial updates, we still need to handle replacement if we were doing it on HTML_UI
        # But HTML_UI no longer has placeholder. Partial updates usually just reload the body.
        # This might be slightly redundant but keeps logic simple.
        return HTMLResponse(HTML_UI, headers=headers)

    # Pass flags to html_page
    page = html_page("Receipt Printer", HTML_UI, show_logout=show_logout, auth_required=auth_required_bool)
    page.headers.update(headers)
    return page

@app.get("/ui/logout")
def ui_logout():
    r = RedirectResponse("/ui?force_reload=1", status_code=303)
    r.delete_cookie("ui_token", path="/")
    return r

# Shared Auth Helper
def ui_handle_auth_and_cookie(request: Request, pass_: str | None, remember: bool):
    authed, should_set_cookie = ui_auth_state(request, pass_, remember)
    return authed, should_set_cookie

@app.post("/ui/print/template")
async def ui_print_template(
    request: Request,
    title: str = Form(""),
    lines: str = Form(""),
    add_dt: bool = Form(False),
    pass_: str | None = Form(None, alias="pass"),
    remember: bool = Form(False)
):
    authed, set_cookie = ui_handle_auth_and_cookie(request, pass_, remember)
    if not authed:
        return html_page("Receipt Printer", "<div class='card'>Wrong password.</div>")

    title_s = (title or "").strip()
    body_lines = [ln.rstrip() for ln in (lines or "").splitlines()]
    has_body = any(ln.strip() for ln in body_lines)
    is_default_title = (title_s.lower() == "tasks" or title_s == "")

    resp = RedirectResponse("/ui#tpl", status_code=303)
    if set_cookie: issue_cookie(resp)

    if is_default_title and not has_body:
        return resp

    try:
        _print_text_content(title_s, body_lines, add_dt, True, "ui")
        return resp
    except Exception as e:
        log("ui_print_template error:", repr(e))
        return html_page("Receipt Printer", f"<div class='card'>Error: {e}</div>")

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
        return html_page("Receipt Printer", "<div class='card'>Wrong password.</div>")

    resp = RedirectResponse("/ui#raw", status_code=303)
    if set_cookie: issue_cookie(resp)

    if not (text or "").strip() and not add_dt:
        return resp

    try:
        lines = (text + (f"\n{now_str('%Y-%m-%d %H:%M')}" if add_dt else "")).splitlines()
        _print_text_content("", lines, False, True, "ui")
        return resp
    except Exception as e:
        log("ui_print_raw error:", repr(e))
        return html_page("Receipt Printer", f"<div class='card'>Error: {e}</div>")

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
        return html_page("Receipt Printer", "<div class='card'>Wrong password.</div>")
    
    try:
        content = await file.read()
        src = Image.open(io.BytesIO(content))
        _print_image_content(src, img_title, img_subtitle, True, "ui")
        
        resp = RedirectResponse("/ui#img", status_code=303)
        if set_cookie: issue_cookie(resp)
        return resp
    except Exception as e:
        log("ui_print_image error:", repr(e))
        return html_page("Receipt Printer", f"<div class='card'>Error: {e}</div>")

# --- Routes: Guest (HTML) -----------------------------------------------------
@app.get("/guest/{token}", response_class=HTMLResponse)
def guest_ui(token: str, request: Request):
    info = GUESTS.validate(token)
    if not info:
        return html_page("Gast", "<div class='card'>Invalid or disabled link.</div>")
    
    remaining = GUESTS.remaining_today(token)
    limit_hint = f"<div class='card'>Maximum text length: {GUEST_MAX_CHARS} characters per print.</div>"
    
    content = (
        f"<div class='card'>Guest: <b>{info['name']}</b> · left today: {remaining}</div>"
        + limit_hint
        + guest_ui_html() # Use raw tabs without replace
    )
    content = content.replace('/ui/print/template', f'/guest/{token}/print/template')
    content = content.replace('/ui/print/raw', f'/guest/{token}/print/raw')
    content = content.replace('/ui/print/image', f'/guest/{token}/print/image')

    if request.headers.get("X-Partial") == "true":
        return HTMLResponse(content)
    
    # Guests don't need logout, and never need auth fields
    return html_page("Guest print", content, show_logout=False, auth_required=False)

@app.post("/guest/{token}/print/template")
async def guest_print_template(
    token: str,
    title: str = Form("TASKS"),
    lines: str = Form(""),
    add_dt: bool = Form(False),
):
    txt_full = (title or "").strip() + "\n" + (lines or "")
    if add_dt: txt_full += f"\n{now_str('%Y-%m-%d %H:%M')}"
    
    ok, msg = _guest_check_len_ok(len(txt_full))
    if not ok: return html_page("Guest print", msg)

    tok = guest_consume_or_error(token)
    if not tok: return html_page("Guest print", "<div class='card'>Limit reached or invalid link.</div>")

    _print_text_content(
        title.strip(), 
        [ln.rstrip() for ln in (lines or "").splitlines()], 
        add_dt, True, "guest", sender=tok["name"]
    )
    return RedirectResponse(f"/guest/{token}#tpl", status_code=303)

@app.post("/guest/{token}/print/raw")
async def guest_print_raw(
    token: str,
    text: str = Form(""),
    add_dt: bool = Form(False),
):
    full = (text or "")
    if add_dt: full += f"\n{now_str('%Y-%m-%d %H:%M')}"
    
    ok, msg = _guest_check_len_ok(len(full))
    if not ok: return html_page("Guest print", msg)

    tok = guest_consume_or_error(token)
    if not tok: return html_page("Guest print", "<div class='card'>Limit reached or invalid link.</div>")

    lines = full.splitlines()
    _print_text_content("", lines, False, True, "guest", sender=tok["name"])
    return RedirectResponse(f"/guest/{token}#raw", status_code=303)

@app.post("/guest/{token}/print/image")
async def guest_print_image(
    token: str,
    file: UploadFile = File(...),
    img_title: str | None = Form(None),
    img_subtitle: str | None = Form(None),
):
    tok = guest_consume_or_error(token)
    if not tok: return html_page("Guest print", "<div class='card'>Limit reached or invalid link.</div>")
    
    content = await file.read()
    src = Image.open(io.BytesIO(content))
    _print_image_content(src, img_title, img_subtitle, True, "guest", sender=tok["name"])
    
    return RedirectResponse(f"/guest/{token}#img", status_code=303)

# --- Routes: Settings & Admin -------------------------------------------------
@app.get("/ui/settings", response_class=HTMLResponse)
def ui_settings(request: Request):
    if not require_ui_auth(request):
        content = "<div class='card'>Not signed in.</div>"
    else:
        content = "<h3 class='title'>Settings</h3>" + settings_html_form()

    if request.headers.get("X-Partial") == "true":
        return HTMLResponse(content)
    
    return html_page("Settings", content, show_logout=True, auth_required=False)

@app.post("/ui/settings/save", response_class=HTMLResponse)
async def ui_settings_save(request: Request):
    if not require_ui_auth(request):
        return html_page("Settings", "<div class='card'>Not signed in.</div>")
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
                    try: SETTINGS[key] = int(val) if "." not in val else float(val)
                    except: SETTINGS[key] = default
                else:
                    SETTINGS[key] = val
    _save_settings(SETTINGS)
    _reload_settings_if_changed()
    return RedirectResponse("/ui/settings", status_code=303)

@app.get("/ui/settings/test", response_class=HTMLResponse)
def ui_settings_test(request: Request):
    if not require_ui_auth(request):
        return html_page("Settings", "<div class='card'>Not signed in.</div>")
    
    sample_lines = ["Read - 10 Min", "Drink water", "Plan – 10 Min", "Exercise – 20 Min"]
    _print_text_content("TEST", sample_lines, True, True, "ui")
    return html_page("Settings", "<div class='card'>Testdruck gesendet.</div>", show_logout=True)

# --- Routes: Guests Admin -----------------------------------------------------
def _base_url(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host  = request.headers.get("x-forwarded-host")  or request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}".rstrip("/")

def _guest_link(token: str, request: Request) -> str:
    return f"{_base_url(request)}/guest/{token}"

def _render_guests_admin(request: Request) -> str:
    rows = []
    for token, info in GUESTS.list():
        link = _guest_link(token, request)
        rid = f"lnk_{token[:8]}"
        row = f"""
        <tr>
          <td style="max-width:0">
            <div class="row" style="gap:8px; align-items:center">
              <input id="{rid}" type="text" value="{link}" readonly
                     style="width: 36ch; max-width:100%; background:#0d1117; border:1px solid #263043; color:#dfe7ff; padding:6px 8px; border-radius:10px; font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:.9rem;">
              <button type="button" class="secondary" onclick="copyToClipboard('{rid}')" style="padding:6px 10px;">Copy</button>
            </div>
          </td>
          <td>{info.get("name", "Guest")}</td>
          <td><span class="badge">{"active" if info.get("active") else "inactive"}</span></td>
          <td>{info.get("quota_per_day", 5)}/Tag</td>
          <td>
            <form method="post" action="/ui/guests/revoke" style="display:inline">
              <input type="hidden" name="token" value="{token}">
              <button class="danger">Revoke</button>
            </form>
          </td>
        </tr>
        """
        rows.append(row)

    # JS for Copy button
    copy_js = """
    <script>
    function copyToClipboard(id){
      const el=document.getElementById(id); if(!el) return;
      el.select(); el.setSelectionRange(0, 99999);
      navigator.clipboard.writeText(el.value).then(()=>{
        const b=el.nextElementSibling; 
        if(b){ b.textContent="Copied ✓"; setTimeout(()=>b.textContent="Copy",1200); }
      });
    }
    </script>
    """
    
    table = f"""
    <section class="card">
      <h3 class="title">Guests</h3>
      <div style="overflow:auto">
      <table style="width:100%; border-collapse:collapse">
        <thead>
          <tr>
            <th style="text-align:left; padding:10px 8px;">Link</th>
            <th style="text-align:left; padding:10px 8px;">Name</th>
            <th style="text-align:left; padding:10px 8px;">Status</th>
            <th style="text-align:left; padding:10px 8px;">Quota</th>
            <th style="text-align:left; padding:10px 8px;">Action</th>
          </tr>
        </thead>
        <tbody>
          {("".join(rows) if rows else '<tr><td colspan="5" style="padding:10px 8px">No tokens yet.</td></tr>')}
        </tbody>
      </table>
      </div>
    </section>
    """

    form = """
    <section class='card' style='margin-top:14px'>
      <h3 class="title">Create new guest link</h3>
      <form method='post' action='/ui/guests/create' class='row' style='gap:10px; flex-wrap:wrap'>
        <input type='text' name='name' placeholder='Name' style='min-width:220px; max-width:320px'>
        <input type='number' name='quota' value='5' min='1' step='1' style='width:120px'>
        <button type='submit'>Create token</button>
      </form>
    </section>
    """
    return copy_js + table + form

@app.get("/ui/guests", response_class=HTMLResponse)
def ui_guests(request: Request):
    if not require_ui_auth(request):
        content = "<div class='card'>Not signed in.</div>"
    else:
        content = _render_guests_admin(request)

    if request.headers.get("X-Partial") == "true":
        return HTMLResponse(content)
    return html_page("Guest", content, show_logout=True, auth_required=False)

@app.post("/ui/guests/create", response_class=HTMLResponse)
async def ui_guests_create(request: Request):
    if not require_ui_auth(request):
        return html_page("Guest", "<div class='card'>Not signed in.</div>")
    form  = await request.form()
    name  = (form.get("name") or "Gast").strip()
    quota = int((form.get("quota") or 5))
    token = GUESTS.create(name, quota_per_day=quota)
    link  = _guest_link(token, request)
    msg   = f"<div class='card'>New link: <a href='{link}' target='_blank'>{link}</a></div>"
    return html_page("Guest", msg + _render_guests_admin(request), show_logout=True)

@app.post("/ui/guests/revoke", response_class=HTMLResponse)
async def ui_guests_revoke(request: Request):
    if not require_ui_auth(request):
        return html_page("Guest", "<div class='card'>Not signed in.</div>")
    form = await request.form()
    tok  = form.get("token") or ""
    ok   = GUESTS.revoke(tok)
    msg  = "<div class='card'>Token deactivated.</div>" if ok else "<div class='card'>Token not found.</div>"
    return html_page("Guest", msg + _render_guests_admin(request), show_logout=True)

# --- Routes: Debug / Queue ----------------------------------------------------
@app.get("/debug/last")
async def debug_last():
    path = "/tmp/last_print.png"
    if os.path.exists(path):
        return FileResponse(path, media_type="image/png")
    return {"error": "no debug file found"}

@app.get("/queue/list")
async def list_queue():
    try:
        files = sorted([f for f in os.listdir(PRINT_QUEUE_DIR) if f.endswith(".json")])
        result = []
        for f in files:
            path = os.path.join(PRINT_QUEUE_DIR, f)
            size = os.path.getsize(path)
            ts = os.path.getmtime(path)
            with open(path, "r", encoding="utf-8") as fh:
                try:
                    data = json.load(fh)
                    meta = data.get("meta", {})
                except Exception: meta = {}
            result.append({
                "file": f,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
                "size_bytes": size,
                "meta": meta
            })
        return JSONResponse({"count": len(result), "jobs": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/queue/clear")
async def clear_queue():
    try:
        shutil.rmtree(PRINT_QUEUE_DIR, ignore_errors=True)
        os.makedirs(PRINT_QUEUE_DIR, exist_ok=True)
        return {"status": "cleared"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/queue/status")
async def queue_status():
    try:
        from queue_print import _running
        files = [f for f in os.listdir(PRINT_QUEUE_DIR) if f.endswith(".json")]
        return {"running": _running, "job_count": len(files), "files": files}
    except Exception as e:
        return {"error": str(e)}

@app.post("/queue/reset")
async def queue_reset():
    try:
        stop_background_flusher()
        shutil.rmtree(PRINT_QUEUE_DIR, ignore_errors=True)
        os.makedirs(PRINT_QUEUE_DIR, exist_ok=True)
        start_background_flusher()
        return {"status": "reset"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
