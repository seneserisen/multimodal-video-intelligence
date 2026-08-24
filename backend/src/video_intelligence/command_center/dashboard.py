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
    <section class="panel upload-panel">
      <div class="section-heading">
        <div><p class="label">NEW LOCAL JOB</p><h2>Import an authorized video</h2></div>
        <span class="local-badge">DURABLE LOCAL MEDIA</span>
      </div>
      <div class="upload-grid">
        <label class="file-picker">
          <span>Choose video</span>
          <input id="media-file" type="file" accept=".avi,.m4v,.mkv,.mov,.mp4,.webm">
        </label>
        <label class="authorization">
          <input id="authorized" type="checkbox">
          <span>I own or am authorized to process this media.</span>
        </label>
        <label class="authorization">
          <input id="transcribe" type="checkbox">
          <span id="transcription-option">Transcribe speech with the configured local model.</span>
        </label>
        <button id="upload" type="button">Import video</button>
      </div>
      <p id="upload-message" class="muted">Source media and results remain in the local data folder until you delete the job.</p>
    </section>
    <section class="grid">
      <article class="panel metric"><span>Version</span><strong id="version">—</strong></article>
      <article class="panel metric"><span>Process</span><strong id="pid">—</strong></article>
      <article class="panel metric"><span>Loopback</span><strong id="address">—</strong></article>
      <article class="panel metric"><span>Started</span><strong id="started">—</strong></article>
    </section>
    <section class="grid" aria-label="Job diagnostics">
      <article class="panel metric"><span>Active jobs</span><strong id="active-jobs">0</strong></article>
      <article class="panel metric"><span>Completed</span><strong id="completed-jobs">0</strong></article>
      <article class="panel metric"><span>Failed / cancelled</span><strong id="failed-jobs">0</strong></article>
      <article class="panel metric"><span>Upload limit</span><strong id="upload-limit">—</strong></article>
    </section>
    <section class="panel jobs-panel">
      <div class="section-heading">
        <div><p class="label">PROCESSING JOBS</p><h2>Durable local queue and transcripts</h2></div>
        <span id="job-count" class="pill waiting">0 JOBS</span>
      </div>
      <div id="job-list" class="job-list"><p class="muted">No jobs yet.</p></div>
    </section>
    <section class="panel pipeline">
      <div class="section-heading">
        <div><p class="label">PIPELINE</p><h2>Local-first processing boundary</h2></div>
        <span class="local-badge">NO CLOUD CALLS</span>
      </div>
      <ol>
        <li><span>01</span><div><strong>Media validation</strong><p>Container, streams, duration, dimensions, codecs.</p></div></li>
        <li><span>02</span><div><strong>Speech evidence</strong><p>Local audio extraction, transcription, language and confidence.</p></div></li>
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
.upload-panel,.jobs-panel{padding:28px;margin-top:14px}.upload-grid{display:grid;grid-template-columns:minmax(220px,1fr) minmax(240px,1.1fr) minmax(240px,1.1fr) auto;gap:14px;align-items:center}.file-picker{position:relative;display:flex;align-items:center;min-height:46px;padding:10px 14px;border:1px dashed #496170;border-radius:10px;color:var(--cyan);font-weight:700;cursor:pointer;overflow:hidden}.file-picker:hover,.file-picker:focus-within{border-color:var(--cyan)}.file-picker input{position:absolute;inset:0;opacity:0;cursor:pointer}.authorization{display:flex;gap:10px;align-items:flex-start;color:var(--muted);font-size:.88rem;line-height:1.45}.authorization input{margin-top:3px;accent-color:var(--cyan)}.job-list{display:grid;gap:12px}.job-card{padding:18px;border:1px solid var(--line);border-radius:12px;background:#0d1319}.job-heading{display:flex;justify-content:space-between;gap:18px;align-items:flex-start}.job-heading p{margin:.45rem 0}.job-status{font:700 .68rem ui-monospace,monospace;letter-spacing:.1em;padding:7px 9px;border:1px solid;border-radius:999px;white-space:nowrap}.job-status.uploading,.job-status.queued{color:var(--amber);border-color:#67552d}.job-status.running,.job-status.succeeded{color:var(--cyan);border-color:#27685c}.job-status.failed,.job-status.cancelled{color:var(--red);border-color:#6b363b}.job-card progress{width:100%;height:8px;margin:8px 0 12px;border:0;border-radius:999px;overflow:hidden;background:#26313d}.job-card progress::-webkit-progress-bar{background:#26313d}.job-card progress::-webkit-progress-value{background:var(--cyan)}.job-card progress::-moz-progress-bar{background:var(--cyan)}.job-facts{display:flex;flex-wrap:wrap;gap:8px}.job-facts span{padding:6px 9px;border-radius:8px;background:#152029;color:var(--muted);font:600 .75rem ui-monospace,monospace}.job-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-top:14px}.transcript{margin-top:16px;border-top:1px solid var(--line);padding-top:14px}.transcript h3{font-size:1rem}.segment{display:grid;grid-template-columns:110px 1fr auto;gap:12px;align-items:start;padding:10px 0;border-top:1px solid #1d2831}.segment time{color:var(--cyan);font:600 .75rem ui-monospace,monospace}.segment p{margin:0;line-height:1.45}.segment button{padding:6px 9px}.error-text{color:#ffb7b7}.jobs-panel h2,.upload-panel h2{margin-bottom:14px}@media(max-width:1000px){.upload-grid{grid-template-columns:1fr 1fr}.upload-grid button{justify-self:start}}@media(max-width:600px){.upload-grid{grid-template-columns:1fr}.segment{grid-template-columns:1fr}.upload-panel,.jobs-panel{padding:20px}.job-heading{flex-direction:column}.job-actions{justify-content:flex-start}}
"""

DASHBOARD_JS = """
const fragmentToken = location.hash.startsWith('#token=')
  ? decodeURIComponent(location.hash.slice(7))
  : null;
const token = fragmentToken || sessionStorage.getItem('mvi-token');
if (location.hash) history.replaceState(null, '', location.pathname);
if (token) sessionStorage.setItem('mvi-token', token);
const el = id => document.getElementById(id);
const terminal = new Set(['succeeded', 'failed', 'cancelled']);

async function api(path, options = {}) {
  if (!token) throw new Error('Missing local access token');
  const response = await fetch(path, {
    ...options,
    headers: { ...(options.headers || {}), Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    let detail = `Local service returned ${response.status}`;
    try { detail = (await response.json()).error || detail; } catch (_) {}
    throw new Error(detail.replaceAll('_', ' '));
  }
  return response.status === 204 ? null : response.json();
}

function display(status) {
  el('connection').textContent = status.running ? 'ONLINE' : 'OFFLINE';
  el('connection').className = `pill ${status.running ? 'online' : 'offline'}`;
  el('state').textContent = status.running ? 'Running' : 'Stopped';
  el('message').textContent = status.message;
  el('version').textContent = status.version;
  el('pid').textContent = status.pid ?? '—';
  el('address').textContent = status.port ? `${status.host}:${status.port}` : '—';
  el('started').textContent = status.started_at ? new Date(status.started_at).toLocaleString() : '—';
  el('active-jobs').textContent = status.max_active_jobs
    ? `${status.active_jobs} / ${status.max_active_jobs}`
    : status.active_jobs;
  el('completed-jobs').textContent = status.completed_jobs;
  el('failed-jobs').textContent = status.failed_jobs;
  el('upload-limit').textContent = status.max_upload_bytes
    ? `${Math.round(status.max_upload_bytes / 1048576)} MiB`
    : '—';
  el('transcribe').disabled = !status.transcription_available;
  el('transcription-option').textContent = status.transcription_available
    ? `${status.transcription_provider} is ready. Transcribe speech locally.`
    : status.transcription_status;
  el('stop').disabled = !status.running;
}

async function refresh() {
  try {
    display(await api('/api/status'));
  } catch (error) {
    el('connection').textContent = 'UNAVAILABLE';
    el('connection').className = 'pill offline';
    el('state').textContent = 'Unavailable';
    el('message').textContent = error.message;
    el('stop').disabled = true;
  }
}

function text(tag, value, className) {
  const node = document.createElement(tag);
  node.textContent = value;
  if (className) node.className = className;
  return node;
}

function jobCard(job) {
  const card = document.createElement('article');
  card.className = 'job-card';
  const heading = document.createElement('div');
  heading.className = 'job-heading';
  const title = document.createElement('div');
  title.append(text('strong', job.filename));
  title.append(text('p', job.message, 'muted'));
  heading.append(title, text('span', job.status.toUpperCase(), `job-status ${job.status}`));
  card.append(heading);

  const progress = document.createElement('progress');
  progress.max = 1;
  progress.value = job.progress;
  progress.setAttribute('aria-label', `${job.filename} progress`);
  card.append(progress);

  if (job.report) {
    const video = job.report.streams.find(stream => stream.stream_type === 'video');
    const audio = job.report.streams.find(stream => stream.stream_type === 'audio');
    const facts = document.createElement('div');
    facts.className = 'job-facts';
    facts.append(
      text('span', `${job.report.duration_ms ?? 'Unknown'} ms`),
      text('span', video ? `${video.width}x${video.height} · ${video.codec_name}` : 'No video'),
      text('span', audio ? `Audio · ${audio.codec_name}` : 'No audio'),
      text('span', job.report.valid ? 'Valid media' : `${job.report.errors.length} error(s)`),
      text('span', job.media_retained ? 'Source retained locally' : 'No retained source'),
      text('span', `Stage · ${job.stage.replaceAll('_', ' ')}`),
    );
    card.append(facts);
  }
  if (job.transcription) {
    const transcript = document.createElement('section');
    transcript.className = 'transcript';
    transcript.append(text('h3', `Transcript · ${job.transcription.language || 'unknown language'}`));
    job.transcription.evidence_items.forEach(item => {
      const segment = document.createElement('div');
      segment.className = 'segment';
      const timestamp = `${Math.floor(item.start_ms / 60000)}:${String(Math.floor((item.start_ms % 60000) / 1000)).padStart(2, '0')}`;
      segment.append(text('time', timestamp), text('p', item.text));
      const edit = document.createElement('button');
      edit.type = 'button';
      edit.textContent = 'Edit';
      edit.setAttribute('aria-label', `Edit transcript at ${timestamp}`);
      edit.addEventListener('click', async () => {
        const replacement = window.prompt('Edit transcript text. Timestamps and provenance are preserved.', item.text);
        if (replacement === null || replacement.trim() === item.text) return;
        await api(`/api/jobs/${job.job_id}/transcript/${item.evidence_id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: replacement }),
        });
        await loadJobs();
      });
      segment.append(edit);
      transcript.append(segment);
    });
    card.append(transcript);
  }
  if (job.error) card.append(text('p', job.error.message, 'error-text'));

  const actions = document.createElement('div');
  actions.className = 'job-actions';
  const button = document.createElement('button');
  if (terminal.has(job.status)) {
    if (job.media_retained) {
      const retry = document.createElement('button');
      retry.textContent = 'Retry';
      retry.addEventListener('click', async () => {
        await api(`/api/jobs/${job.job_id}/retry`, { method: 'POST' });
        await loadJobs();
      });
      actions.append(retry);
    }
    button.textContent = 'Delete job + media';
    button.addEventListener('click', async () => {
      await api(`/api/jobs/${job.job_id}`, { method: 'DELETE' });
      await loadJobs();
    });
  } else {
    button.textContent = job.cancellation_requested ? 'Cancelling…' : 'Cancel job';
    button.disabled = job.cancellation_requested;
    button.addEventListener('click', async () => {
      await api(`/api/jobs/${job.job_id}/cancel`, { method: 'POST' });
      await loadJobs();
    });
  }
  actions.append(button);
  card.append(actions);
  return card;
}

async function loadJobs() {
  try {
    const payload = await api('/api/jobs');
    el('job-count').textContent = `${payload.jobs.length} JOB${payload.jobs.length === 1 ? '' : 'S'}`;
    const list = el('job-list');
    list.replaceChildren();
    if (!payload.jobs.length) list.append(text('p', 'No jobs yet.', 'muted'));
    else payload.jobs.forEach(job => list.append(jobCard(job)));
  } catch (error) {
    el('upload-message').textContent = error.message;
  }
}

async function upload() {
  const file = el('media-file').files[0];
  if (!file) { el('upload-message').textContent = 'Choose a supported video first.'; return; }
  if (!el('authorized').checked) { el('upload-message').textContent = 'Confirm authorization first.'; return; }
  el('upload').disabled = true;
  el('upload-message').textContent = `Uploading ${file.name}…`;
  try {
    await api('/api/jobs', {
      method: 'POST',
      headers: {
        'X-Filename': encodeURIComponent(file.name),
        'X-MVI-Authorized': 'true',
        'X-MVI-Transcribe': String(el('transcribe').checked),
      },
      body: file,
    });
    el('upload-message').textContent = 'Import complete. Durable local processing is running.';
    el('media-file').value = '';
    el('authorized').checked = false;
    await loadJobs();
  } catch (error) {
    el('upload-message').textContent = error.message;
  } finally {
    el('upload').disabled = false;
  }
}

el('refresh').addEventListener('click', async () => { await refresh(); await loadJobs(); });
el('upload').addEventListener('click', upload);
el('stop').addEventListener('click', async () => {
  el('stop').disabled = true;
  try { await api('/api/stop', { method: 'POST' }); setTimeout(refresh, 400); }
  catch (error) { el('message').textContent = error.message; }
});
refresh();
loadJobs();
setInterval(loadJobs, 1000);
"""
