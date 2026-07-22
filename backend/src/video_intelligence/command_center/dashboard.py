# ruff: noqa: E501
from __future__ import annotations

DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Video Intelligence Command Center</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <main>
    <header>
      <div>
        <p class="eyebrow">LOCAL CONTROL PLANE</p>
        <h1>Video Intelligence</h1>
        <p class="subtitle">Command Center</p>
      </div>
      <div id="connection" class="pill waiting">Connecting</div>
    </header>
    <section class="hero panel">
      <div>
        <p class="label">SERVICE STATE</p>
        <strong id="state" class="state">Checking…</strong>
        <p id="message" class="muted">Authenticating with the local service.</p>
      </div>
      <div class="actions">
        <button id="refresh" type="button">Refresh status</button>
        <button id="stop" class="danger" type="button">Stop service</button>
      </div>
    </section>
    <section class="grid">
      <article class="panel metric"><span>Version</span><strong id="version">—</strong></article>
      <article class="panel metric"><span>Process</span><strong id="pid">—</strong></article>
      <article class="panel metric"><span>Loopback</span><strong id="address">—</strong></article>
      <article class="panel metric"><span>Started</span><strong id="started">—</strong></article>
    </section>
    <section class="panel pipeline">
      <div class="section-heading">
        <div><p class="label">PIPELINE</p><h2>Local-first processing boundary</h2></div>
        <span class="local-badge">NO CLOUD CALLS</span>
      </div>
      <ol>
        <li><span>01</span><div><strong>Media validation</strong><p>Container, streams, duration, dimensions, codecs.</p></div></li>
        <li><span>02</span><div><strong>Evidence extraction</strong><p>Future speech, screen text, visual and audio evidence.</p></div></li>
        <li><span>03</span><div><strong>Fusion</strong><p>Timestamped confirmation, supplementation and contradiction.</p></div></li>
        <li><span>04</span><div><strong>Export</strong><p>Schema-valid JSON and evidence-backed Markdown.</p></div></li>
      </ol>
    </section>
    <section class="panel commands">
      <p class="label">OPERATOR COMMANDS</p>
      <div><code>video-intelligence doctor</code><span>Check prerequisites</span></div>
      <div><code>video-intelligence status</code><span>Read service health</span></div>
      <div><code>video-intelligence update</code><span>Check source updates</span></div>
      <div><code>video-intelligence update --apply</code><span>Fast-forward a clean checkout</span></div>
    </section>
    <footer>Bound to 127.0.0.1 · Authenticated per run · No telemetry</footer>
  </main>
  <script src="/app.js" defer></script>
</body>
</html>
"""

DASHBOARD_CSS = """
:root{color-scheme:dark;--bg:#080b0f;--panel:#10161d;--line:#26313d;--text:#edf7f5;--muted:#8ea09f;--cyan:#52f2cf;--amber:#ffc857;--red:#ff6b6b;font-family:Inter,ui-sans-serif,system-ui,sans-serif}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 85% 0,#12362f 0,transparent 32%),var(--bg);color:var(--text);min-height:100vh}main{width:min(1120px,calc(100% - 32px));margin:auto;padding:48px 0}header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:28px}h1{font-size:clamp(2.2rem,7vw,5rem);letter-spacing:-.06em;line-height:.85;margin:10px 0 0}.subtitle{font-size:1.1rem;color:var(--cyan);letter-spacing:.3em;text-transform:uppercase}.eyebrow,.label{font:700 .72rem ui-monospace,monospace;letter-spacing:.2em;color:var(--muted)}.panel{background:linear-gradient(145deg,rgba(19,28,36,.96),rgba(12,17,23,.96));border:1px solid var(--line);border-radius:18px;box-shadow:0 18px 60px rgba(0,0,0,.24)}.hero{display:flex;justify-content:space-between;gap:24px;align-items:end;padding:28px}.state{font-size:2.2rem}.muted{color:var(--muted)}.actions{display:flex;gap:10px;flex-wrap:wrap}button{border:1px solid #3d5362;background:#19242e;color:var(--text);border-radius:10px;padding:11px 16px;font-weight:700;cursor:pointer}button:hover{border-color:var(--cyan)}button.danger{border-color:#6b363b;color:#ffb7b7}button:disabled{opacity:.45;cursor:not-allowed}.pill,.local-badge{font:700 .7rem ui-monospace,monospace;letter-spacing:.12em;padding:9px 12px;border-radius:999px;border:1px solid}.pill.waiting{color:var(--amber);border-color:#67552d}.pill.online,.local-badge{color:var(--cyan);border-color:#27685c;background:#0d2b25}.pill.offline{color:var(--red);border-color:#6b363b}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:14px 0}.metric{padding:20px}.metric span{display:block;color:var(--muted);font-size:.76rem;text-transform:uppercase;letter-spacing:.1em}.metric strong{display:block;margin-top:9px;font:700 1rem ui-monospace,monospace;overflow-wrap:anywhere}.pipeline,.commands{padding:28px;margin-top:14px}.section-heading{display:flex;justify-content:space-between;align-items:center;gap:20px}h2{margin:4px 0 20px;font-size:1.45rem}.pipeline ol{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden}.pipeline li{display:flex;gap:14px;padding:20px;background:#0d1319}.pipeline li>span{color:var(--cyan);font:700 .75rem ui-monospace,monospace}.pipeline p{color:var(--muted);font-size:.86rem;line-height:1.5}.commands>div{display:grid;grid-template-columns:minmax(260px,1fr) 1fr;gap:20px;padding:14px 0;border-top:1px solid var(--line)}code{color:var(--cyan)}.commands span,footer{color:var(--muted)}footer{text-align:center;padding:30px;font-size:.78rem}@media(max-width:760px){main{padding-top:24px}header,.hero,.section-heading{align-items:flex-start;flex-direction:column}.grid,.pipeline ol{grid-template-columns:1fr 1fr}.commands>div{grid-template-columns:1fr;gap:6px}}@media(max-width:480px){.grid,.pipeline ol{grid-template-columns:1fr}}
"""

DASHBOARD_JS = """
const token=location.hash.startsWith('#token=')?decodeURIComponent(location.hash.slice(7)):sessionStorage.getItem('mvi-token');
if(location.hash)history.replaceState(null,'',location.pathname);
if(token)sessionStorage.setItem('mvi-token',token);
const el=id=>document.getElementById(id);
async function api(path,options={}){if(!token)throw new Error('Missing local access token');const response=await fetch(path,{...options,headers:{...(options.headers||{}),Authorization:`Bearer ${token}`}});if(!response.ok)throw new Error(`Local service returned ${response.status}`);return response.json()}
function display(status){el('connection').textContent=status.running?'ONLINE':'OFFLINE';el('connection').className=`pill ${status.running?'online':'offline'}`;el('state').textContent=status.running?'Running':'Stopped';el('message').textContent=status.message;el('version').textContent=status.version;el('pid').textContent=status.pid??'—';el('address').textContent=status.port?`${status.host}:${status.port}`:'—';el('started').textContent=status.started_at?new Date(status.started_at).toLocaleString():'—';el('stop').disabled=!status.running}
async function refresh(){try{display(await api('/api/status'))}catch(error){el('connection').textContent='UNAVAILABLE';el('connection').className='pill offline';el('state').textContent='Unavailable';el('message').textContent=error.message;el('stop').disabled=true}}
el('refresh').addEventListener('click',refresh);el('stop').addEventListener('click',async()=>{el('stop').disabled=true;try{await api('/api/stop',{method:'POST'});setTimeout(refresh,400)}catch(error){el('message').textContent=error.message}});refresh();
"""
