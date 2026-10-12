// The Gurbani engine in the browser: the laptop app's Python engine running in Pyodide
// (see engine-core.js and web_hub.py). Words come from asr-worker.js; commands from the
// page; the messages for the page go back exactly as the laptop app sends them.
"use strict";
let eng = null, latest = null, scheduled = false;
const post = (m) => self.postMessage(m);
const say = (text, extra) => post(Object.assign({ type: "progress", text }, extra || {}));

async function fetchBytes(url, label) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${label} could not be downloaded (HTTP ${r.status})`);
  // the size header is only a guide: a server that compresses (GitHub Pages does) gives the
  // compressed size, while the browser hands over the uncompressed bytes
  const size = +r.headers.get("content-length") || 0;
  if (!r.body) return new Uint8Array(await r.arrayBuffer());
  const reader = r.body.getReader(), parts = [];
  let got = 0, shown = -1;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    parts.push(value); got += value.length;
    const pct = size ? Math.min(99, Math.floor(100 * got / size)) : -1;
    if (pct >= 0 && pct !== shown && pct % 5 === 0) { shown = pct; say(`Downloading ${label}: ${pct}%`); }
  }
  const out = new Uint8Array(got);
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}

async function init(cfg) {
  importScripts(cfg.pyodide + "pyodide.js", "rfjs.js?v=" + cfg.build, "engine-core.js?v=" + cfg.build);
  say("Downloading the Gurbani data");
  const [appZip, rfWasm] = await Promise.all([fetchBytes(cfg.app, "the Gurbani data"), fetchBytes("rf.wasm?v=" + cfg.build, "the word matching")]);
  eng = await self.startEngine({ loadPyodide: self.loadPyodide, indexURL: cfg.pyodide, rfjs: self.rfjs, rfWasm, appZip,
                                 settings: cfg.settings, texts: cfg.texts, say });
  post({ type: "ready", loadS: eng.loadS });
  post({ type: "msgs", msgs: eng.hello() });
}

function run() {                       // only the newest words matter: older ones still waiting are skipped
  scheduled = false;
  const w = latest; latest = null;
  if (!w || !eng) return;
  const t0 = performance.now();
  try {
    const msgs = eng.audio(w.t, w.t20, w.t10, w.t45);
    post({ type: "msgs", msgs, ms: Math.round(performance.now() - t0) });
  } catch (e) {
    post({ type: "error", text: "Following stopped for a moment: " + (e && e.message || e) });
  }
}

self.onmessage = async (ev) => {
  const m = ev.data;
  if (m.type === "init") {
    try { await init(m.cfg); }
    catch (e) { post({ type: "error", text: "The Gurbani engine could not start: " + (e && e.message || e), fatal: true }); }
  } else if (m.type === "words") {
    latest = m;
    if (!scheduled) { scheduled = true; setTimeout(run, 0); }
  } else if (m.type === "cmd") {
    if (!eng) return;
    try { post({ type: "msgs", msgs: eng.command(m.c), cmd: m.c.cmd }); }
    catch (e) { post({ type: "error", text: "That didn't work: " + (e && e.message || e) }); }
  }
};
