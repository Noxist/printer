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
    --bg:#0b0f14; --card:#121821; --muted:#98a2b3; --text:#e6edf3; --line:#1e2a38;
    --accent:#7dd3fc; --accent-2:#a78bfa; --err:#ef4444; --radius:16px; --shadow:0 6px 30px rgba(0,0,0,.35);
  }
  @media (prefers-color-scheme: light){
    :root{ --bg:#f6f7fb; --card:#ffffff; --text:#0b1220; --muted:#475467; --line:#e7eaf0; --shadow:0 6px 18px rgba(0,0,0,.08); }
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{
    margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans";
    color:var(--text);
    background:
      radial-gradient(1200px 600px at 20% -10%, rgba(125,211,252,.15), transparent 60%),
      radial-gradient(800px 400px at 110% 10%, rgba(167,139,250,.12), transparent 60%),
      var(--bg);
    line-height:1.35;
  }
  .wrap{max-width:920px; margin:0 auto; padding:clamp(16px,2.5vw,28px)}
  header.top{position:sticky; top:0; backdrop-filter:saturate(1.2) blur(8px); background:color-mix(in srgb, var(--bg) 75%, transparent); border-bottom:1px solid var(--line); z-index:5}
  .top-inner{display:flex; align-items:center; gap:12px; padding:12px clamp(12px,2vw,20px)}
  .title{font-weight:700; letter-spacing:.2px; font-size:1.1rem}
  .spacer{flex:1}
  .link{color:var(--muted); text-decoration:none; font-size:.95rem}
  .link:hover{color:var(--text); text-decoration:underline}
  .card{border:1px solid var(--line); background:color-mix(in srgb, var(--card) 92%, transparent); border-radius:var(--radius); box-shadow:var(--shadow);
        padding:clamp(14px,2.5vw,20px); margin:12px 0 18px}
  .grid{display:grid; grid-template-columns:1fr 1fr; gap:12px}
  .tabs{display:flex; gap:8px; flex-wrap:wrap; padding:14px 0 8px}
  .tab{border:1px solid var(--line); border-radius:999px; padding:8px 14px; cursor:pointer; user-select:none;
       background:color-mix(in srgb, var(--card) 85%, transparent); font-weight:600; font-size:.95rem;
       transition:transform .08s ease, background .15s ease, border-color .15s ease}
  .tab[aria-selected="true"]{background:linear-gradient(135deg, color-mix(in srgb, var(--card) 88%, transparent), color-mix(in srgb, var(--card) 60%, transparent));
       outline:2px solid color-mix(in srgb, var(--accent) 60%, transparent); border-color:color-mix(in srgb, var(--accent) 40%, var(--line))}
  .row{display:flex; flex-wrap:wrap; align-items:center; gap:10px}
  .grow{flex:1 1 auto}
  label{font-weight:600; color:var(--muted); display:block; margin:8px 0 6px}
  textarea, input[type=text], input[type=password], input[type=file], input[type=number], select{
    width:100%; border:1px solid var(--line); background:transparent; color:var(--text);
    padding:12px; border-radius:12px; outline:none; transition:border-color .15s, box-shadow .15s
  }
  textarea{min-height:140px; resize:vertical}
  input:focus, textarea:focus, select:focus{border-color:color-mix(in srgb, var(--accent) 55%, var(--line)); box-shadow:0 0 0 4px color-mix(in srgb, var(--accent) 18%, transparent)}
  button{
    appearance:none; border:none; cursor:pointer; font-weight:700; padding:12px 16px; border-radius:12px;
    background:linear-gradient(135deg, var(--accent), var(--accent-2)); color:#0b1220;
    box-shadow:0 8px 20px rgba(125,211,252,.25);
  }
  button.secondary{background:transparent; color:var(--text); border:1px solid var(--line); box-shadow:none}
  .hidden{display:none !important}
  .nav a{margin-left:12px}

  /* Custom file upload */
  .file-btn {
    display:inline-block;
    background:linear-gradient(135deg, var(--accent), var(--accent-2));
    color:#0b1220;
    padding:10px 16px;
    border-radius:12px;
    font-weight:600;
    cursor:pointer;
    box-shadow:0 6px 14px rgba(125,211,252,.25);
  }
  #file-chosen {
    margin-left:10px;
    color:var(--muted);
    font-size:.9rem;
  }

  /* Responsive fixes */
  @media (max-width:760px){
    .grid { grid-template-columns:1fr; }
    .top-inner { flex-direction:column; align-items:flex-start; gap:6px; }
    .nav { display:flex; flex-wrap:wrap; gap:10px; }
    .tabs { flex-wrap:wrap; }
    .tab { flex:1 1 auto; text-align:center; }
    button { width:100%; }
  }
</style>
<body>
  <header class="top">
    <div class="top-inner wrap">
      <div class="title">Receipt Printer</div>
      <div class="spacer"></div>
      <nav class="nav">
        <a class="link" href="/ui" data-nav>Print</a>
        <a class="link" href="/ui/guests" data-nav>Guests</a>
        <a class="link" href="/ui/settings" data-nav>Settings</a>
        <a class="link" href="/ui/logout" title="Logout">Logout</a>
      </nav>
    </div>
  </header>

  <main class="wrap">
    {content}
  </main>

  <script>
  // Re-init after partial loads
  function initTabs(){
    const tabs=[{id:"tpl",btn:"tab-tpl",pane:"pane_tpl"},{id:"raw",btn:"tab-raw",pane:"pane_raw"},{id:"img",btn:"tab-img",pane:"pane_img"}];
    function selectTab(id){
      tabs.forEach(t=>{
        const btn=document.getElementById(t.btn), pane=document.getElementById(t.pane), active=(t.id===id);
        if(btn){ btn.setAttribute("aria-selected", active?"true":"false"); btn.tabIndex=active?0:-1; }
        if(pane){ pane.hidden=!active; }
      });
      try{ history.replaceState(null,"","#"+id); }catch{}
    }
    function initFromHash(){
      const h=(location.hash||"#tpl").slice(1);
      const known=["tpl","raw","img"];
      selectTab(known.includes(h)?h:"tpl");
    }
    ["tab-tpl","tab-raw","tab-img"].forEach((id, idx)=>{
      const el=document.getElementById(id);
      if(el){
        const tid=["tpl","raw","img"][idx];
        el.onclick=()=>selectTab(tid);
        el.onkeydown=e=>{ if(e.key==="Enter"||e.key===" "){ e.preventDefault(); selectTab(tid); } };
      }
    });
    initFromHash();
  }

  function initFileUpload(){
    const input=document.getElementById("imgfile");
    if(!input) return;
    input.addEventListener("change", function(){
      const fileChosen=document.getElementById("file-chosen");
      if(fileChosen){ fileChosen.textContent=this.files.length?this.files[0].name:"No file selected"; }
    });
  }

  function initAuthUI(){
    const flagEl=document.getElementById("auth-flag");
    const authRequired = (flagEl?.dataset?.auth || "false").toLowerCase()==="true";
    ["auth-wrap","auth-wrap2","auth-wrap3","remember-wrap","remember-wrap2","remember-wrap3"].forEach(id=>{
      const el=document.getElementById(id);
      if(el){ el.classList.toggle("hidden", !authRequired); }
    });
  }

  function initUI(){
    initTabs();
    initFileUpload();
    initAuthUI();
  }

  function ajaxNavigate(url, addToHistory=true){
    fetch(url, {headers: {"X-Partial":"true"}})
      .then(r=>r.text())
      .then(html=>{
        const main=document.querySelector("main.wrap");
        if(main){ main.innerHTML = html; }
        if(addToHistory){ try{ history.pushState(null,"",url); }catch{} }
        initUI();
      })
      .catch(err=>console.error("Navigation error:", err));
  }

  document.addEventListener("DOMContentLoaded", ()=>{
    initUI();
    document.querySelectorAll("a[data-nav]").forEach(link=>{
      link.addEventListener("click", e=>{
        e.preventDefault();
        ajaxNavigate(link.getAttribute("href"));
      });
    });
    window.addEventListener("popstate", ()=>ajaxNavigate(location.pathname, false));
  });
  </script>
</body>
</html>
"""

def html_page(title: str, content: str) -> HTMLResponse:
    return HTMLResponse(HTML_BASE.replace("{title}", title).replace("{content}", content))

HTML_UI = r"""
<div id="auth-flag" data-auth="{{AUTH_REQUIRED}}" hidden></div>

<div class="tabs" role="tablist" aria-label="Mode">
  <div class="tab" role="tab" id="tab-tpl" aria-controls="pane_tpl" aria-selected="true" tabindex="0">Template</div>
  <div class="tab" role="tab" id="tab-raw" aria-controls="pane_raw" aria-selected="false" tabindex="-1">Raw</div>
  <div class="tab" role="tab" id="tab-img" aria-controls="pane_img" aria-selected="false" tabindex="-1">Image</div>
</div>

<!-- Template -->
<section id="pane_tpl" class="card" role="tabpanel" aria-labelledby="tab-tpl">
  <form method="post" action="/ui/print/template">
    <div class="grid">
      <div>
        <label for="title">Title</label>
        <input id="title" type="text" name="title" placeholder="TASKS" value="TASKS">
        <label for="lines">Lines (one per line)</label>
        <textarea id="lines" name="lines" placeholder="Buy milk&#10;Pay bills&#10;Write code"></textarea>
        <label><input type="checkbox" name="add_dt"> Add date/time</label>
      </div>
      <div>
        <div id="auth-wrap" class="row" style="gap:10px">
          <label for="pass1">UI password</label>
          <input id="pass1" type="password" name="pass" placeholder="only if required" style="max-width:220px">
          <label id="remember-wrap"><input type="checkbox" name="remember"> Stay signed in</label>
        </div>
      </div>
    </div>
    <div class="row" style="margin-top:12px; gap:12px">
      <button type="submit">Print</button>
    </div>
  </form>
</section>

<!-- RAW -->
<section id="pane_raw" class="card" role="tabpanel" aria-labelledby="tab-raw" hidden>
  <form method="post" action="/ui/print/raw">
    <label for="rawtext">Raw text</label>
    <textarea id="rawtext" name="text" placeholder="Any text..."></textarea>
    <label><input type="checkbox" name="add_dt"> Add date/time</label>
    <div class="row" style="margin-top:12px">
      <div class="grow"></div>
      <div id="auth-wrap2" class="row" style="gap:10px">
        <label for="pass2">UI password</label>
        <input id="pass2" type="password" name="pass" placeholder="only if required" style="max-width:220px">
        <label id="remember-wrap2"><input type="checkbox" name="remember"> Stay signed in</label>
      </div>
    </div>
    <div class="row" style="margin-top:12px; gap:12px">
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
    <div class="row" style="margin-top:12px">
      <div class="grow"></div>
      <div id="auth-wrap3" class="row" style="gap:10px">
        <label for="pass3">UI password</label>
        <input id="pass3" type="password" name="pass" placeholder="only if required" style="max-width:220px">
        <label id="remember-wrap3"><input type="checkbox" name="remember"> Stay signed in</label>
      </div>
    </div>
    <div class="row" style="margin-top:12px; gap:12px">
      <button type="submit">Print</button>
    </div>
  </form>
</section>
""".replace("{w}", str(PRINT_WIDTH_PX))


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
        <div class="row" style="margin-top:12px; gap:12px">
          <button type="submit">Save</button>
          <a class="link" href="/ui/settings/test" data-nav>Test print</a>
        </div>
      </form>
    </section>
    """
    return form


def guest_ui_html(auth_required_flag: str) -> str:
    return HTML_UI.replace("{{AUTH_REQUIRED}}", auth_required_flag)
