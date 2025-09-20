from fastapi.responses import HTMLResponse
from logic import PRINT_WIDTH_PX

HTML_BASE = r"""
<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<style>
  :root{
    --bg:#f5f7fa; --card:#ffffff; --muted:#475467; --text:#0b1220; --line:#e7eaf0;
    --accent:#3b82f6; --accent-2:#8b5cf6; --err:#ef4444; --radius:18px;
    --shadow:0 4px 24px rgba(0,0,0,.12);
  }
  @media (prefers-color-scheme: dark){
    :root{
      --bg:#0b0f14; --card:#121821; --muted:#98a2b3; --text:#e6edf3; --line:#1e2a38;
      --shadow:0 6px 26px rgba(0,0,0,.35);
    }
  }
  *{box-sizing:border-box; -webkit-tap-highlight-color:transparent}
  html,body{height:100%}
  body{
    margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    color:var(--text); line-height:1.4;
    background:
      radial-gradient(1200px 800px at 20% -10%, rgba(59,130,246,.15), transparent 70%),
      radial-gradient(1000px 600px at 120% 10%, rgba(139,92,246,.12), transparent 70%),
      var(--bg);
    min-height:100vh;
    display:flex; flex-direction:column;
  }
  .wrap{max-width:920px; margin:0 auto; padding:clamp(16px,3vw,28px); flex:1; width:100%}
  header.top{position:sticky; top:0; backdrop-filter:saturate(1.2) blur(10px);
    background:color-mix(in srgb, var(--bg) 80%, transparent); border-bottom:1px solid var(--line); z-index:10}
  .top-inner{display:flex; align-items:center; gap:14px; padding:12px clamp(12px,3vw,24px)}
  .title{font-weight:700; font-size:1.1rem; letter-spacing:.2px}
  .spacer{flex:1}
  .link{color:var(--muted); text-decoration:none; font-size:.95rem; margin-left:16px}
  .link:hover{color:var(--text); text-decoration:underline}
  .card{border:1px solid var(--line); background:color-mix(in srgb, var(--card) 95%, transparent);
        border-radius:var(--radius); box-shadow:var(--shadow);
        padding:clamp(16px,2.8vw,22px); margin:14px 0 22px; width:100%}
  .grid{display:grid; grid-template-columns:1fr 1fr; gap:16px}
  @media (max-width:760px){ .grid{grid-template-columns:1fr} }
  .tabs{display:flex; flex-wrap:wrap; gap:10px; padding:18px 0 10px}
  .tab{border:1px solid var(--line); border-radius:999px; padding:9px 18px; cursor:pointer;
       background:var(--card); font-weight:600; font-size:.95rem; user-select:none;
       transition:all .2s ease; box-shadow:0 2px 6px rgba(0,0,0,.04);}
  .tab[aria-selected="true"]{
       background:linear-gradient(135deg,var(--accent),var(--accent-2)); color:#fff;
       border-color:transparent; box-shadow:0 4px 14px rgba(59,130,246,.35);}
  .row{display:flex; flex-wrap:wrap; align-items:center; gap:12px}
  .grow{flex:1 1 auto}
  label{font-weight:600; color:var(--muted); display:block; margin:10px 0 6px}
  textarea, input[type=text], input[type=password], input[type=file], input[type=number], select{
    width:100%; border:1px solid var(--line); background:transparent; color:var(--text);
    padding:12px 14px; border-radius:12px; outline:none; transition:border-color .15s, box-shadow .15s
  }
  textarea{min-height:140px; resize:vertical}
  input:focus, textarea:focus, select:focus{
    border-color:var(--accent);
    box-shadow:0 0 0 4px color-mix(in srgb, var(--accent) 20%, transparent)
  }
  button{
    appearance:none; border:none; cursor:pointer; font-weight:700;
    padding:13px 22px; border-radius:12px;
    background:linear-gradient(135deg, var(--accent), var(--accent-2)); color:#fff;
    box-shadow:0 6px 18px rgba(59,130,246,.25);
    transition:transform .15s ease, box-shadow .15s ease;
  }
  button:hover{transform:translateY(-1px); box-shadow:0 8px 20px rgba(59,130,246,.3);}
  button.secondary{background:transparent; color:var(--text); border:1px solid var(--line); box-shadow:none}
  .hidden{display:none !important}

  /* File upload button */
  .file-btn{display:inline-block; background:linear-gradient(135deg, var(--accent), var(--accent-2));
    color:#fff; padding:11px 18px; border-radius:12px; font-weight:600; cursor:pointer;
    box-shadow:0 6px 14px rgba(59,130,246,.25);}
  #file-chosen{margin-left:10px; color:var(--muted); font-size:.9rem}

  /* Responsive button placement */
  .form-actions{display:flex; justify-content:flex-end; margin-top:18px}
  @media (max-width:760px){
    .form-actions{justify-content:center}
    .form-actions button{width:100%; max-width:320px}
  }
  /* Remove ugly blue focus ring from checkboxes */
  input[type="checkbox"]:focus {
    outline: none;
    box-shadow: none;
  }
</style>
<body>
  <header class="top">
    <div class="top-inner wrap">
      <div class="title">Receipt Printer</div>
      <div class="spacer"></div>
      <nav class="nav" id="main-nav">
        <a class="link" href="/ui" data-nav>Print</a>
        <a class="link guest-hide" href="/ui/guests" data-nav>Guests</a>
        <a class="link guest-hide" href="/ui/settings" data-nav>Settings</a>
        <a class="link guest-hide" href="/ui/logout" title="Logout">Logout</a>
      </nav>
    </div>
  </header>
  <main class="wrap">{content}</main>
</body>
</html>
"""

def html_page(title: str, content: str) -> HTMLResponse:
    return HTMLResponse(HTML_BASE.replace("{title}", title).replace("{content}", content))

HTML_UI = r"""
<div class="tabs" role="tablist" aria-label="Mode">
  <div class="tab" role="tab" id="tab-tpl" aria-controls="pane_tpl" aria-selected="true" tabindex="0">Template</div>
  <div class="tab" role="tab" id="tab-raw" aria-controls="pane_raw" aria-selected="false" tabindex="-1">Raw</div>
  <div class="tab" role="tab" id="tab-img" aria-controls="pane_img" aria-selected="false" tabindex="-1">Image</div>
</div>

<!-- Template -->
<section id="pane_tpl" class="card" role="tabpanel" aria-labelledby="tab-tpl">
  <form method="post" action="/ui/print/template">
    <label for="title">Title</label>
    <input id="title" type="text" name="title" placeholder="Tasks">

    <label for="lines">Lines (one per line)</label>
    <textarea id="lines" name="lines" placeholder="Buy milk&#10;Pay bills&#10;Write code"></textarea>

    <label><input type="checkbox" name="add_dt"> Add date/time</label>

    <div id="auth-wrap" class="row" style="margin-top:14px; gap:10px">
      <label for="pass">UI password</label>
      <input id="pass" type="password" name="pass" placeholder="only if required" style="max-width:220px">
      <label id="remember-wrap"><input type="checkbox" name="remember"> Stay signed in</label>
    </div>

    <div class="form-actions">
      <button type="submit">Print</button>
    </div>
  </form>
</section>

<!-- Raw -->
<section id="pane_raw" class="card" role="tabpanel" aria-labelledby="tab-raw" hidden>
  <form method="post" action="/ui/print/raw">
    <label for="text">Raw text</label>
    <textarea id="text" name="text" placeholder="Any text..."></textarea>

    <label><input type="checkbox" name="add_dt"> Add date/time</label>

    <div id="auth-wrap2" class="row" style="margin-top:14px; gap:10px">
      <label for="pass2">UI password</label>
      <input id="pass2" type="password" name="pass" placeholder="only if required" style="max-width:220px">
      <label id="remember-wrap2"><input type="checkbox" name="remember"> Stay signed in</label>
    </div>

    <div class="form-actions">
      <button type="submit">Print</button>
    </div>
  </form>
</section>

<!-- Image -->
<section id="pane_img" class="card" role="tabpanel" aria-labelledby="tab-img" hidden>
  <form method="post" action="/ui/print/image" enctype="multipart/form-data">
    <div class="grid">
      <div>
        <label for="imgfile">Upload Image</label>
        <input id="imgfile" type="file" name="file" accept="image/*" required hidden>
        <label for="imgfile" class="file-btn">Choose File</label>
        <span id="file-chosen">No file selected</span>
      </div>
      <div>
        <label for="img_title" style="margin-top:0">Title (optional)</label>
        <input id="img_title" type="text" name="img_title" placeholder="Title">
        <label for="img_subtitle" style="margin-top:8px">Subtitle (optional)</label>
        <input id="img_subtitle" type="text" name="img_subtitle" placeholder="Subtitle">
      </div>
    </div>
    <div id="auth-wrap3" class="row" style="margin-top:14px; gap:10px">
      <label for="pass3">UI password</label>
      <input id="pass3" type="password" name="pass" placeholder="only if required" style="max-width:220px">
      <label id="remember-wrap3"><input type="checkbox" name="remember"> Stay signed in</label>
    </div>
    <div class="form-actions">
      <button type="submit">Print</button>
    </div>
    <div id="drop-zone" style="margin-top:16px; padding:30px; border:2px dashed var(--line); text-align:center; border-radius:12px; color:var(--muted); cursor:pointer">
      Drag & Drop Image Here
    </div>
    <input id="imgfile" type="file" name="file" accept="image/*" hidden>

  </form>
</section>

<script>
const tabs=[{id:"tpl",btn:"tab-tpl",pane:"pane_tpl"},{id:"raw",btn:"tab-raw",pane:"pane_raw"},{id:"img",btn:"tab-img",pane:"pane_img"}];
function selectTab(id){
  tabs.forEach(t=>{
    const btn=document.getElementById(t.btn),pane=document.getElementById(t.pane),active=(t.id===id);
    btn.setAttribute("aria-selected",active?"true":"false");
    btn.tabIndex=active?0:-1; pane.hidden=!active;
  });
  history.replaceState(null,"","#"+id);
}
function initFromHash(){
  const h=(location.hash||"#tpl").slice(1);
  selectTab(tabs.some(t=>t.id===h)?h:"tpl");
}
tabs.forEach(t=>{
  const el=document.getElementById(t.btn);
  el.addEventListener("click",()=>selectTab(t.id));
  el.addEventListener("keydown",e=>{ if(e.key==="Enter"||e.key===" "){ e.preventDefault(); selectTab(t.id); }});
});
window.addEventListener("hashchange",initFromHash);
initFromHash();

// File chosen text update
document.addEventListener("DOMContentLoaded",()=>{
  const input=document.getElementById("imgfile");
  if(input){
    input.addEventListener("change",function(){
      const fileChosen=document.getElementById("file-chosen");
      fileChosen.textContent=this.files.length?this.files[0].name:"No file selected";
    });
  }
});

// Hide password UI if not required
const AUTH_REQUIRED=String("{{AUTH_REQUIRED}}").toLowerCase().trim()==="true";
["auth-wrap","auth-wrap2","auth-wrap3"].forEach(id=>{
  const el=document.getElementById(id);
  if(el) el.classList.toggle("hidden", !AUTH_REQUIRED);
});
["remember-wrap","remember-wrap2","remember-wrap3"].forEach(id=>{
  const el=document.getElementById(id);
  if(el) el.classList.toggle("hidden", !AUTH_REQUIRED);
});
</script>
""".replace("{w}", str(PRINT_WIDTH_PX))

// --- Drag & Drop Upload ---
const dropZone = document.getElementById("drop-zone");
if(dropZone){
  const hiddenFile = document.getElementById("hidden-file-input");
  dropZone.addEventListener("click", ()=>hiddenFile.click());
  ["dragenter","dragover"].forEach(ev=>dropZone.addEventListener(ev,e=>{
    e.preventDefault(); dropZone.style.background="rgba(59,130,246,0.08)";
  }));HTML_BASE
  ["dragleave","drop"].forEach(ev=>dropZone.addEventListener(ev,e=>{
    e.preventDefault(); dropZone.style.background="";
  }));
  dropZone.addEventListener("drop",e=>{
    e.preventDefault();
    if(e.dataTransfer.files.length){
      hiddenFile.files = e.dataTransfer.files;
      dropZone.textContent = "Selected: " + e.dataTransfer.files[0].name;
      dropZone.closest("form").submit();
    }
  });
  hiddenFile.addEventListener("change",()=>{
    if(hiddenFile.files.length){
      dropZone.textContent = "Selected: " + hiddenFile.files[0].name;
      dropZone.closest("form").submit();
    }
  });
}
// Hide Guests/Settings if guest UI
if(location.pathname.startsWith("/guest/")){
  document.querySelectorAll(".guest-hide").forEach(el=>el.style.display="none");
}

def settings_html_form() -> str:
    from logic import settings_effective, SET_KEYS
    eff = settings_effective()
    rows = []
    for key, default, typ, opts in SET_KEYS:
        val = eff.get(key, default)
        label = key.replace("RECEIPT_", "").replace("_", " ").title()
        if typ == "select":
            options = "".join([f'<option value="{o}"{" selected" if str(val)==str(o) else ""}>{o}</option>' for o in opts])
            field = f'<select name="{key}">{options}</select>'
        elif typ == "checkbox":
            checked = " checked" if str(val).lower() in ("1","true","yes","on","y","t") else ""
            field = f'<input type="checkbox" name="{key}" value="1"{checked}>'
        elif typ == "number":
            field = f'<input type="number" step="any" name="{key}" value="{val}">'
        else:
            field = f'<input type="text" name="{key}" value="{val}">'
        rows.append(f"<div><label>{label}</label>{field}</div>")

    form = f"""
    <section class="card">
      <form method="post" action="/ui/settings/save">
        <div class="grid">
          {''.join(rows)}
        </div>
        <div class="row" style="margin-top:16px; gap:12px; justify-content:flex-end">
          <button type="submit">Save</button>
          <a class="link" href="/ui/settings/test">Test print</a>
        </div>
      </form>
    </section>
    """
    return form


def guest_ui_html(auth_required_flag: str) -> str:
    return HTML_UI.replace("{{AUTH_REQUIRED}}", auth_required_flag)
