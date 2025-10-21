# main.py
import os
import io
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, FileResponse
from pydantic import BaseModel
from PIL import Image
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from queue_print import start_background_flusher
from routes_sources import router as sources_router

from logic import (
    log, now_str, pil_to_base64_png, mqtt_publish_image_base64,
    render_receipt, render_image_with_headers, ReceiptCfg,
    check_api_key, require_ui_auth, issue_cookie, ui_auth_state,
    cfg_get, SETTINGS, SET_KEYS, _save_settings,
    GUESTS, guest_consume_or_error, _guest_check_len_ok, GUEST_MAX_CHARS,
)
from ui_html import html_page, HTML_UI, settings_html_form, guest_ui_html
# --- Queue-Thread-Initialisierung --------------------------------------------
from queue_print import start_background_flusher, stop_background_flusher, PRINT_QUEUE_DIR
import shutil, os, json, time
from fastapi.responses import JSONResponse

print("[main] 🧩 Starte Printer-App …")

try:
    stop_background_flusher()
    print("[main] 🛑 Alte Queue-Threads gestoppt.")
except Exception as e:
    print("[main] ⚠️ Konnte alten Thread nicht stoppen:", e)

start_background_flusher()
print("[main] ✅ Druck-Queue frisch gestartet (nur eine Instanz aktiv).")

# --- App & Middleware ---------------------------------------------------------
app = FastAPI(title="Printer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modularer Quellen-Router
app.include_router(sources_router)


PRINT_WIDTH_PX = int(cfg_get("PRINT_WIDTH_PX", 576))

# --- Static files & favicon -----------------------------------------
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve favicon.ico from /static directory if it exists."""
    path = os.path.join(static_dir, "favicon.ico")
    if os.path.exists(path):
        return FileResponse(path)
    return FileResponse(os.path.join(static_dir, "favicon.png"))  # Fallback

# ------------------------------- Models ---------------------------------------
class PrintPayload(BaseModel):
    title: str = ""
    lines: list[str] = []
    cut: bool = True
    add_datetime: bool = True

class RawPayload(BaseModel):
    text: str
    add_datetime: bool = False

# ------------------------------- Health / Root --------------------------------
@app.get("/_health", response_class=PlainTextResponse)
def health():
    return "OK"

@app.get("/")
def ok():
    from logic import TOPIC, PUBLISH_QOS
    return {"ok": True, "topic": TOPIC, "qos": PUBLISH_QOS}

# ------------------------------- API: Print -----------------------------------
@app.post("/print")
async def print_job(p: PrintPayload, request: Request):
    check_api_key(request)

    # 🛑 Keine leeren Titel oder Zeilen drucken
    if (not p.title.strip()) and (not any(line.strip() for line in p.lines)):
        log("⚠️ Leerer PrintJob – wird übersprungen.")
        return {"ok": False, "msg": "Empty print job ignored."}

    cfg = ReceiptCfg()
    img = render_receipt(p.title, p.lines, add_time=p.add_datetime, width_px=PRINT_WIDTH_PX, cfg=cfg)
    b64 = pil_to_base64_png(img)
    from queue_print import enqueue_base64_png
    enqueue_base64_png(b64, cut_paper=(1 if p.cut else 0), meta={"source": "api"})
    return {"ok": True}


@app.post("/api/print/template")
async def api_print_template(p: PrintPayload, request: Request):
    check_api_key(request)

    # 🛑 Blockiere leere Templates
    if (not p.title.strip() or p.title.strip().lower() == "tasks") and not any(line.strip() for line in p.lines):
        log("⚠️ Leeres Template oder Defaulttitel – wird nicht gedruckt.")
        return {"ok": False, "msg": "Empty or default template ignored."}


    cfg = ReceiptCfg()
    img = render_receipt(p.title, p.lines, add_time=p.add_datetime, width_px=PRINT_WIDTH_PX, cfg=cfg)
    b64 = pil_to_base64_png(img)
    from queue_print import enqueue_base64_png
    enqueue_base64_png(b64, cut_paper=(1 if p.cut else 0), meta={"source": "api"})
    return {"ok": True}


@app.post("/api/print/raw")
async def api_print_raw(p: RawPayload, request: Request):
    check_api_key(request)

    # 🛑 Keine leeren Texte drucken
    if not p.text.strip():
        log("⚠️ Leerer Raw-Text – Druck übersprungen.")
        return {"ok": False, "msg": "Empty raw print ignored."}

    cfg = ReceiptCfg()
    lines = (p.text + (f"\n{now_str('%Y-%m-%d %H:%M')}" if p.add_datetime else "")).splitlines()
    img = render_receipt("", lines, add_time=False, width_px=PRINT_WIDTH_PX, cfg=cfg)
    b64 = pil_to_base64_png(img)
    from queue_print import enqueue_base64_png
    enqueue_base64_png(b64, cut_paper=1, meta={"source": "ui"})  # oder "api"/"guest"
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

    # 🛑 Prüfe, ob die Datei überhaupt Bilddaten enthält
    if not content:
        log("⚠️ Leeres Bild – wird nicht gedruckt.")
        return {"ok": False, "msg": "Empty image ignored."}

    src = render_image_with_headers(
        Image.open(io.BytesIO(content)),
        PRINT_WIDTH_PX,
        ReceiptCfg(),
        title=img_title,
        subtitle=img_subtitle
    )
    b64 = pil_to_base64_png(src)
    from queue_print import enqueue_base64_png
    enqueue_base64_png(b64, cut_paper=1, meta={"source": "ui"})  # oder "api"/"guest"
    return {"ok": True}

# ------------------------------- UI: Simple Frontend --------------------------
@app.get("/ui", response_class=HTMLResponse)
def ui(request: Request):
    # Nach Logout erzwingen wir die Passworteingabe
    force_auth = request.query_params.get("force_reload") == "1"

    if force_auth:
        auth_required = "true"
    else:
        auth_required = "false" if require_ui_auth(request) else ("true" if cfg_get("UI_PASS") else "false")

    html = HTML_UI.replace("{{AUTH_REQUIRED}}", auth_required)

    # Caching hart ausschalten, damit das Login-UI nach Logout nicht aus dem Cache kommt
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    if request.headers.get("X-Partial") == "true":
        return HTMLResponse(html, headers=headers)

    # ✅ Fix: html_page() gibt bereits eine Response zurück
    page = html_page("Receipt Printer", html)
    page.headers.update(headers)
    return page

@app.get("/ui/logout")
def ui_logout():
    # Cookie löschen und ein hartes Reload des Login-UI erzwingen,
    # damit das Passwortfeld sicher wieder sichtbar ist (kein Cache).
    r = RedirectResponse("/ui?force_reload=1", status_code=303)
    r.delete_cookie("ui_token", path="/")
    return r


def ui_handle_auth_and_cookie(
    request: Request,
    pass_: str | None,
    remember: bool
) -> tuple[bool, bool]:
    """
    Zentraler Helper: prüft Login und sagt, ob ein 'Remember me' Cookie
    gesetzt werden soll.
    """
    authed, should_set_cookie = ui_auth_state(request, pass_, remember)
    if not authed:
        return False, False
    return True, should_set_cookie

# ------------------------------- UI: Print Template ---------------------------
@app.post("/ui/print/template")
async def ui_print_template(
    request: Request,
    title: str = Form(""),   # <- vorher "TASKS"
    lines: str = Form(""),
    add_dt: bool = Form(False),
    pass_: str | None = Form(None, alias="pass"),
    remember: bool = Form(False)
):
    authed, set_cookie = ui_handle_auth_and_cookie(request, pass_, remember)
    if not authed:
        return html_page("Receipt Printer", "<div class='card'>Wrong password.</div>")

    # Inhalt prüfen (Login-Only oder „leeres / Default-Template“ → NICHT drucken)
    title_s = (title or "").strip()
    body_lines = [ln.rstrip() for ln in (lines or "").splitlines()]
    has_body = any(ln.strip() for ln in body_lines)
    is_default_title = (title_s.lower() == "tasks" or title_s == "")

    if is_default_title and not has_body:
        log("⚠️ Leeres oder Default-Template – kein Druck (nur Auth/Cookie).")
        resp = RedirectResponse("/ui#tpl", status_code=303)
        if set_cookie:
            issue_cookie(resp)
        return resp

    try:
        cfg = ReceiptCfg()
        img = render_receipt(title_s, body_lines, add_time=add_dt, width_px=PRINT_WIDTH_PX, cfg=cfg)
        b64 = pil_to_base64_png(img)
        from queue_print import enqueue_base64_png
        enqueue_base64_png(b64, cut_paper=1, meta={"source": "ui"})  # oder "api"/"guest"

        resp = RedirectResponse("/ui#tpl", status_code=303)
        if set_cookie:
            issue_cookie(resp)
        return resp
    except Exception as e:
        log("ui_print_template error:", repr(e))
        return html_page("Receipt Printer", f"<div class='card'>Error: {e}</div>")

# ------------------------------- UI: Print Raw --------------------------------
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

    # Login-Only/leer verhindern: kein Druck, nur Cookie setzen und zurück
    if not (text or "").strip() and not add_dt:
        log("⚠️ Leerer RAW-Print – kein Druck (nur Auth/Cookie).")
        resp = RedirectResponse("/ui#raw", status_code=303)
        if set_cookie:
            issue_cookie(resp)
        return resp

    try:
        cfg = ReceiptCfg()
        lines = (text + (f"\n{now_str('%Y-%m-%d %H:%M')}" if add_dt else "")).splitlines()
        img = render_receipt("", lines, add_time=False, width_px=PRINT_WIDTH_PX, cfg=cfg)
        b64 = pil_to_base64_png(img)
        from queue_print import enqueue_base64_png
        enqueue_base64_png(b64, cut_paper=1, meta={"source": "ui"})  # oder "api"/"guest"
        resp = RedirectResponse("/ui#raw", status_code=303)
        if set_cookie:
            issue_cookie(resp)
        return resp
    except Exception as e:
        log("ui_print_raw error:", repr(e))
        return html_page("Receipt Printer", f"<div class='card'>Error: {e}</div>")

# ------------------------------- UI: Print Image ------------------------------
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
        cfg = ReceiptCfg()
        composed = render_image_with_headers(src, PRINT_WIDTH_PX, cfg, title=img_title, subtitle=img_subtitle)
        b64 = pil_to_base64_png(composed)
        from queue_print import enqueue_base64_png
        enqueue_base64_png(b64, cut_paper=1, meta={"source": "ui"})  # oder "api"/"guest"
        resp = RedirectResponse("/ui#img", status_code=303)
        if set_cookie:
            issue_cookie(resp)
        return resp
    except Exception as e:
        log("ui_print_image error:", repr(e))
        return html_page("Receipt Printer", f"<div class='card'>Error: {e}</div>")

# ------------------------------- Guest: UI & Print ----------------------------
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
        + guest_ui_html("false")
    )
    content = content.replace('/ui/print/template', f'/guest/{token}/print/template')
    content = content.replace('/ui/print/raw', f'/guest/{token}/print/raw')
    content = content.replace('/ui/print/image', f'/guest/{token}/print/image')

    if request.headers.get("X-Partial") == "true":
        return HTMLResponse(content)
    return html_page("Guest print", content)

@app.post("/guest/{token}/print/template")
async def guest_print_template(
    token: str,
    title: str = Form("TASKS"),
    lines: str = Form(""),
    add_dt: bool = Form(False),
):
    txt_full = (title or "").strip() + "\n" + (lines or "")
    if add_dt:
        txt_full += f"\n{now_str('%Y-%m-%d %H:%M')}"
    ok, msg = _guest_check_len_ok(len(txt_full))
    if not ok:
        return html_page("Guest print", msg)

    tok = guest_consume_or_error(token)
    if not tok:
        return html_page("Guest print", "<div class='card'>Limit reached or invalid link.</div>")

    cfg = ReceiptCfg()
    img = render_receipt(
        title.strip(),
        [ln.rstrip() for ln in (lines or "").splitlines()],
        add_time=add_dt,
        width_px=PRINT_WIDTH_PX,
        cfg=cfg,
        sender_name=tok["name"]
    )
    b64 = pil_to_base64_png(img)
    from queue_print import enqueue_base64_png
    enqueue_base64_png(b64, cut_paper=1, meta={"source": "ui"})  # oder "api"/"guest"
    return RedirectResponse(f"/guest/{token}#tpl", status_code=303)

@app.post("/guest/{token}/print/raw")
async def guest_print_raw(
    token: str,
    text: str = Form(""),
    add_dt: bool = Form(False),
):
    full = (text or "")
    if add_dt:
        full += f"\n{now_str('%Y-%m-%d %H:%M')}"
    ok, msg = _guest_check_len_ok(len(full))
    if not ok:
        return html_page("Guest print", msg)

    tok = guest_consume_or_error(token)
    if not tok:
        return html_page("Guest print", "<div class='card'>Limit reached or invalid link.</div>")

    cfg = ReceiptCfg()
    lines = full.splitlines()
    img = render_receipt("", lines, add_time=False, width_px=PRINT_WIDTH_PX, cfg=cfg, sender_name=tok["name"])
    b64 = pil_to_base64_png(img)
    from queue_print import enqueue_base64_png
    enqueue_base64_png(b64, cut_paper=1, meta={"source": "ui"})  # oder "api"/"guest"
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
        return html_page("Guest print", "<div class='card'>Limit reached or invalid link.</div>")
    content = await file.read()
    src = Image.open(io.BytesIO(content))
    cfg = ReceiptCfg()
    composed = render_image_with_headers(
        src,
        PRINT_WIDTH_PX,
        cfg,
        title=img_title,
        subtitle=img_subtitle,
        sender_name=tok["name"]
    )
    b64 = pil_to_base64_png(composed)
    from queue_print import enqueue_base64_png
    enqueue_base64_png(b64, cut_paper=1, meta={"source": "ui"})  # oder "api"/"guest"
    return RedirectResponse(f"/guest/{token}#img", status_code=303)

# ------------------------------- Settings UI ----------------------------------
@app.get("/ui/settings", response_class=HTMLResponse)
def ui_settings(request: Request):
    if not require_ui_auth(request):
        content = "<div class='card'>Not signed in.</div>"
    else:
        content = "<h3 class='title'>Settings</h3>" + settings_html_form()

    if request.headers.get("X-Partial") == "true":
        return HTMLResponse(content)
    return html_page("Settings", content)

from logic import _reload_settings_if_changed

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
                    try:
                        SETTINGS[key] = int(val) if "." not in val else float(val)
                    except:
                        SETTINGS[key] = default
                else:
                    SETTINGS[key] = val
    _save_settings(SETTINGS)
    _reload_settings_if_changed()  # 👈 HIER neu einfügen!
    return RedirectResponse("/ui/settings", status_code=303)
    
@app.get("/ui/settings/test", response_class=HTMLResponse)
def ui_settings_test(request: Request):
    if not require_ui_auth(request):
        return html_page("Settings", "<div class='card'>Not signed in.</div>")
    cfg = ReceiptCfg()
    sample_lines = ["Read - 10 Min", "Drink water", "Plan – 10 Min", "Exercise – 20 Min"]
    img = render_receipt("TEST", sample_lines, add_time=True, width_px=PRINT_WIDTH_PX, cfg=cfg)
    b64 = pil_to_base64_png(img)
    from queue_print import enqueue_base64_png
    enqueue_base64_png(b64, cut_paper=1, meta={"source": "ui"})  # oder "api"/"guest"
    return html_page("Settings", "<div class='card'>Testdruck gesendet.</div>")

# ------------------------------- Guest Admin UI -------------------------------
def _base_url(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host  = request.headers.get("x-forwarded-host")  or request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}".rstrip("/")

def _guest_link(token: str, request: Request) -> str:
    return f"{_base_url(request)}/guest/{token}"

def _copy_btn_js() -> str:
    return """
<script>
function copyToClipboard(id){
  const el=document.getElementById(id);
  if(!el) return;
  el.select(); el.setSelectionRange(0, 99999);
  navigator.clipboard.writeText(el.value).then(()=>{
    const b=el.nextElementSibling; if(b){ b.textContent="Kopiert ✓"; setTimeout(()=>b.textContent="Kopieren",1200); }
  });
}
</script>
"""

def _render_guests_admin(request: Request) -> str:
    rows = []
    for token, info in GUESTS.list():
        name   = info.get("name", "Guest")
        active = "active" if info.get("active") else "inactive"
        quota  = info.get("quota_per_day", 5)
        link   = _guest_link(token, request)
        rid    = f"lnk_{token[:8]}"
        row = f"""
        <tr>
          <td style="max-width:0">
            <div class="row" style="gap:8px; align-items:center">
              <input id="{rid}" type="text" value="{link}" readonly
                     style="width: 36ch; max-width:100%; background:#0d1117; border:1px solid #263043; color:#dfe7ff; padding:6px 8px; border-radius:10px; font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:.9rem;">
              <button type="button" class="secondary" onclick="copyToClipboard('{rid}')" style="padding:6px 10px;">Kopieren</button>
            </div>
          </td>
          <td>{name}</td>
          <td><span class="badge">{active}</span></td>
          <td>{quota}/Tag</td>
          <td>
            <form method="post" action="/ui/guests/revoke" style="display:inline">
              <input type="hidden" name="token" value="{token}">
              <button class="danger">Revoke</button>
            </form>
          </td>
        </tr>
        """
        rows.append(row)

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
    return _copy_btn_js() + table + form

@app.get("/ui/guests", response_class=HTMLResponse)
def ui_guests(request: Request):
    if not require_ui_auth(request):
        content = "<div class='card'>Not signed in.</div>"
    else:
        content = _render_guests_admin(request)

    if request.headers.get("X-Partial") == "true":
        return HTMLResponse(content)
    return html_page("Guest", content)

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
    return html_page("Guest", msg + _render_guests_admin(request))

@app.post("/ui/guests/revoke", response_class=HTMLResponse)
async def ui_guests_revoke(request: Request):
    if not require_ui_auth(request):
        return html_page("Guest", "<div class='card'>Not signed in.</div>")
    form = await request.form()
    tok  = form.get("token") or ""
    ok   = GUESTS.revoke(tok)
    msg  = "<div class='card'>Token deactivated.</div>" if ok else "<div class='card'>Token nicht gefunden.</div>"
    return html_page("Guest", msg + _render_guests_admin(request))

# ------------------------------- Debug ----------------------------------------
@app.get("/debug/last")
async def debug_last():
    path = "/tmp/last_print.png"
    if os.path.exists(path):
        return FileResponse(path, media_type="image/png")
    return {"error": "no debug file found"}
from fastapi.responses import JSONResponse
import os, json, time
from queue_print import PRINT_QUEUE_DIR
# ------------------------------- Que ----------------------------------------
@app.get("/queue/list")
async def list_queue():
    """Listet alle gespeicherten Druck-Jobs auf."""
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
                except Exception:
                    meta = {}
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
    """Löscht alle gespeicherten Druck-Jobs."""
    import shutil
    try:
        shutil.rmtree(PRINT_QUEUE_DIR, ignore_errors=True)
        os.makedirs(PRINT_QUEUE_DIR, exist_ok=True)
        print("[queue] 🧹 Queue manuell geleert.")
        return {"status": "cleared"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/queue/status")
async def queue_status():
    """Zeigt, ob der Hintergrund-Thread läuft und wie viele Jobs es gibt."""
    try:
        from queue_print import _running
        files = [f for f in os.listdir(PRINT_QUEUE_DIR) if f.endswith(".json")]
        return {"running": _running, "job_count": len(files), "files": files}
    except Exception as e:
        return {"error": str(e)}

@app.post("/queue/reset")
async def queue_reset():
    """Stoppt Thread + leert Queue komplett + startet frisch."""
    try:
        stop_background_flusher()
        shutil.rmtree(PRINT_QUEUE_DIR, ignore_errors=True)
        os.makedirs(PRINT_QUEUE_DIR, exist_ok=True)
        start_background_flusher()
        print("[queue] ♻️ Queue komplett zurückgesetzt.")
        return {"status": "reset"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
