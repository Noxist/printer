# ui_html.py
from fastapi.responses import HTMLResponse

from logic import SET_KEYS, cfg_get

def html_page(title: str, content: str, show_logout: bool = False) -> str:
    """Standard HTML wrapper for all pages."""
    nav_links = ""
    if show_logout:
        nav_links = """
        <a href="/ui">Print</a>
        <a href="/ui/settings">Settings</a>
        <a href="/ui/guests">Guests</a>
        <a href="/ui/logout" style="color:#ff7b72">Logout</a>
        """
    
    # CSS Variables & Dark Theme similar to GitHub Dark
    style = """
    :root {
        --bg: #0d1117;
        --card-bg: #161b22;
        --border: #30363d;
        --text: #c9d1d9;
        --text-muted: #8b949e;
        --primary: #238636;
        --primary-hover: #2ea043;
        --danger: #da3633;
        --input-bg: #0d1117;
        --status-bg: #21262d;
        --status-shadow: rgba(63,185,80,0.3);
    }
    @media (prefers-color-scheme: light) {
        :root {
            --bg: #f6f8fa;
            --card-bg: #ffffff;
            --border: #d0d7de;
            --text: #24292f;
            --text-muted: #57606a;
            --primary: #2da44e;
            --primary-hover: #2c974b;
            --danger: #cf222e;
            --input-bg: #ffffff;
            --status-bg: #f0f2f6;
            --status-shadow: rgba(45,164,78,0.25);
        }
    }
    * { box-sizing: border-box; }
    body {
        margin: 0; padding: 20px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        background: var(--bg); color: var(--text);
        display: flex; justify-content: center;
    }
    .container { max-width: 600px; width: 100%; margin-top: 20px; }
    h1, h2, h3 { margin-top: 0; color: #fff; }
    a { color: #58a6ff; text-decoration: none; font-weight: 500; }
    a:hover { text-decoration: underline; }
    
    /* Nav & Header */
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; gap: 12px; }
    .nav { display: flex; gap: 15px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
    
    /* Cards & Forms */
    .card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .row { display: flex; gap: 10px; }
    input, textarea, select {
        width: 100%; padding: 8px 12px; margin-bottom: 10px;
        background: var(--input-bg); border: 1px solid #30363d;
        color: var(--text); border-radius: 6px; font-size: 14px;
        font-family: inherit;
    }
    textarea { min-height: 100px; resize: vertical; }
    button {
        background: var(--primary); color: #fff; border: 1px solid rgba(27,31,35,0.15);
        padding: 6px 16px; border-radius: 6px; font-size: 14px; font-weight: 600;
        cursor: pointer; width: 100%;
    }
    button:hover { background: var(--primary-hover); }
    button.secondary { background: #21262d; border-color: rgba(27,31,35,0.15); color: var(--text); }
    button.danger { background: var(--danger); }
    
    /* Utility */
    .badge {
        display: inline-block; padding: 2px 7px; font-size: 12px; font-weight: 600;
        line-height: 1; border-radius: 20px; background: #238636; color: #fff;
    }
    
    /* Printer Status Indicator */
    .status-indicator {
        font-size: 0.85rem; font-weight: 700; letter-spacing: 0.2px;
        display: inline-flex; align-items: center; gap: 8px;
        padding: 6px 10px; border-radius: 12px; background: var(--status-bg); border: 1px solid var(--border);
        color: var(--text); min-width: 132px; justify-content: center;
    }
    .dot {
        width: 12px; height: 12px; border-radius: 50%;
        background-color: #8b949e; /* default grey */
        box-shadow: 0 0 4px rgba(0,0,0,0.5);
        transition: background-color 0.2s ease, box-shadow 0.2s ease;
    }
    .dot.on { background-color: #2fbf71; box-shadow: 0 0 8px var(--status-shadow); }
    .dot.off { background-color: #e5534b; box-shadow: 0 0 4px rgba(229,83,75,0.35); }
    .dot.unknown { background-color: #8b949e; box-shadow: 0 0 4px rgba(0,0,0,0.2); }

    @media (max-width: 520px) {
        body { padding: 16px; }
        .header { flex-direction: column; align-items: flex-start; }
        .status-indicator { width: 100%; justify-content: flex-start; }
    }
    """

    script = """
    <script>
    // Simple tab switching logic if needed, currently hash-based in main.py
    function updateStatus() {
        fetch('/api/printer/status')
            .then(r => r.json())
            .then(d => {
                const dot = document.getElementById('p-dot');
                const txt = document.getElementById('p-txt');
                const hasIp = Boolean(d.ip && d.ip !== 'Not Configured');
                dot.className = 'dot unknown';
                txt.textContent = hasIp ? 'Checking…' : 'Unknown';

                if (d.online === true) {
                    dot.className = 'dot on';
                    txt.textContent = 'Printer ON';
                } else if (d.online === false && hasIp) {
                    dot.className = 'dot off';
                    txt.textContent = 'Printer OFF';
                }
            })
            .catch(e => {
                console.log('Status poll error', e);
                const dot = document.getElementById('p-dot');
                const txt = document.getElementById('p-txt');
                dot.className = 'dot unknown';
                txt.textContent = 'Status unavailable';
            });
    }
    // Poll every 5 seconds
    setInterval(updateStatus, 5000);
    window.addEventListener('load', updateStatus);
    </script>
    """

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>{style}</style>
        {script}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{title}</h1>
                <div class="status-indicator" title="Printer Connection Status">
                    <div id="p-dot" class="dot"></div>
                    <span id="p-txt">...</span>
                </div>
            </div>
            {f'<div class="nav">{nav_links}</div>' if show_logout else ''}
            {content}
        </div>
    </body>
    </html>
    """)

# --- Components ---

def login_page(error: str = None):
    err_html = f"<div class='card' style='border-color:var(--danger); color:var(--danger)'>{error}</div>" if error else ""
    content = f"""
    <div class="card" style="max-width:400px; margin:auto;">
        <h3>Login</h3>
        {err_html}
        <form method="post" action="/ui/login">
            <input type="password" name="pass" placeholder="Password" required autofocus>
            <label style="display:flex; align-items:center; gap:8px; margin-bottom:15px; font-size:0.9rem;">
                <input type="checkbox" name="remember" value="true" style="width:auto; margin:0"> Remember me
            </label>
            <button type="submit">Unlock</button>
        </form>
    </div>
    """
    return html_page("Login", content, show_logout=False)

def settings_html_form():
    """Generates the settings form based on logic.SET_KEYS."""
    fields = []
    for key, default, typ, opts in SET_KEYS:
        val = cfg_get(key, default)
        
        if typ == "checkbox":
            checked = "checked" if str(val).lower() in ("true", "1", "yes", "on") else ""
            html = f"""
            <div style="margin-bottom:12px; display:flex; align-items:center; justify-content:space-between">
                <label for="{key}">{key}</label>
                <input type="checkbox" id="{key}" name="{key}" {checked} style="width:auto; margin:0">
            </div>"""
        elif typ == "select":
            opts_html = "".join([f"<option value='{o}' {'selected' if str(val)==str(o) else ''}>{o}</option>" for o in opts])
            html = f"""
            <div style="margin-bottom:12px">
                <label style="display:block; font-size:0.85rem; margin-bottom:4px; color:var(--text-muted)">{key}</label>
                <select name="{key}">{opts_html}</select>
            </div>"""
        else:
            # text or number
            html = f"""
            <div style="margin-bottom:12px">
                <label style="display:block; font-size:0.85rem; margin-bottom:4px; color:var(--text-muted)">{key}</label>
                <input type="{typ}" name="{key}" value="{val}">
            </div>"""
        fields.append(html)
    
    return f"""
    <form method="post" action="/ui/settings/save" class="card">
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px">
            {''.join(fields)}
        </div>
        <div style="margin-top:20px; display:flex; gap:10px">
            <button type="submit">Save Changes</button>
            <a href="/ui/settings/test" target="_blank" style="flex:1"><button type="button" class="secondary">Test Print</button></a>
        </div>
    </form>
    """

HTML_UI = """
<div class="card">
    <h3 id="tpl">Template Print</h3>
    <form method="post" action="/ui/print/template">
        <input type="text" name="title" placeholder="Title (optional, e.g. 'To-Do')">
        <textarea name="lines" placeholder="Line 1\nLine 2\n..."></textarea>
        <div class="row" style="align-items:center">
            <label style="display:flex; gap:6px; font-size:0.9rem"><input type="checkbox" name="add_dt" style="width:auto"> Add Date</label>
            <button type="submit" style="width:auto; margin-left:auto">Print</button>
        </div>
    </form>
</div>

<div class="card">
    <h3 id="raw">Raw Print</h3>
    <form method="post" action="/ui/print/raw">
        <textarea name="text" placeholder="Raw text content..." style="font-family:monospace"></textarea>
        <div class="row" style="align-items:center">
             <label style="display:flex; gap:6px; font-size:0.9rem"><input type="checkbox" name="add_dt" style="width:auto"> Add Date</label>
             <button type="submit" style="width:auto; margin-left:auto">Print Raw</button>
        </div>
    </form>
</div>

<div class="card">
    <h3 id="img">Image Print</h3>
    <form method="post" action="/ui/print/image" enctype="multipart/form-data">
        <input type="file" name="file" accept="image/*" required>
        <input type="text" name="img_title" placeholder="Header Title (optional)">
        <input type="text" name="img_subtitle" placeholder="Subtitle (optional)">
        <button type="submit" style="margin-top:10px">Print Image</button>
    </form>
</div>
"""

def guest_ui_html():
    """Returns the simplified UI for guests."""
    return HTML_UI
