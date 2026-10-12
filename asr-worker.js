// The speech model in the browser: Karanbir Singh's IndicConformer CTC model (the same
// v4.int8.onnx the laptop app uses, loaded from its Hugging Face page), run with
// onnxruntime-web (WebAssembly).
//
// Sound arrives at 16 kHz. Every HOP seconds (longer on a slow phone) the model hears
// the last WIN seconds; its choice for each 40 ms frame is kept on one timeline (the
// newest hearing wins, except at its first LEFT seconds, which it heard with little
// before them), and the last 20, 10 and 4.5 seconds are read off that timeline as words,
// as the laptop app reads its 20, 10 and 4.5 second windows.
// onnxruntime-web 1.18, the last with a build that does not use shared memory: on iPhone,
// Safari cannot set aside the shared memory the newer builds ask for ("Out of memory").
"use strict";
const SR = 16000, FR = 640, BLANK = 256;
const WIN = 8.0, HOP_MIN = 1.5, LEFT = 1.0, KEEP_S = 40;
let ORT = null, session = null, pieces = null, kind = null;
let buf = new Float32Array(KEEP_S * SR), bufStart = 0, total = 0;     // samples [bufStart, total) are kept
let frames = new Int16Array((KEEP_S + 20) * SR / FR).fill(-1), frameBase = 0;   // frame k at frames[k - frameBase]
let busy = false, lastEnd = 0, hop = HOP_MIN, runs = 0, runMs = 0;

const post = (m, t) => self.postMessage(m, t || []);
const say = (text, extra) => post(Object.assign({ type: "progress", text }, extra || {}));

async function getModel(url) {
  let cache = null;
  try {
    cache = await caches.open("gurbani-speech-model-v4");
    const hit = await cache.match(url);
    if (hit) {
      say("Loading the speech model (saved on this phone)");
      return new Uint8Array(await hit.arrayBuffer());
    }
  } catch (e) { cache = null; }
  const r = await fetch(url);
  if (!r.ok) throw new Error(`the speech model could not be downloaded (HTTP ${r.status})`);
  const size = +r.headers.get("content-length") || 184311219;
  const reader = r.body.getReader(), chunks = [];
  let got = 0, shown = -1;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value); got += value.length;
    const pct = Math.min(99, Math.floor(100 * got / size));
    if (pct !== shown) { shown = pct; say(`Downloading the speech model (first time only): ${pct}%`, { pct }); }
  }
  let blob = new Blob(chunks); chunks.length = 0;
  if (cache) {
    try { await cache.put(url, new Response(blob, { headers: { "content-type": "application/octet-stream" } })); }
    catch (e) { post({ type: "note", text: "The speech model could not be saved on this phone (not enough space?), so it will download again next time." }); }
  }
  const bytes = new Uint8Array(await blob.arrayBuffer()); blob = null;
  return bytes;
}

async function init(cfg) {
  importScripts(cfg.ort + "ort.wasm.min.js");
  ORT = self.ort;
  ORT.env.wasm.wasmPaths = cfg.ort;
  ORT.env.wasm.numThreads = 1;                 // ort-wasm-simd.wasm: no threads, no shared memory
  ORT.env.wasm.proxy = false;
  const v = await (await fetch(cfg.vocab)).json();
  pieces = v.pieces; kind = v.kind;
  let bytes = await getModel(cfg.model);
  say("Starting the speech model");
  // no memory arena or memory patterns: a little slower, but much less memory at the peak
  session = await ORT.InferenceSession.create(bytes, { executionProviders: ["wasm"], graphOptimizationLevel: "all",
                                                        enableCpuMemArena: false, enableMemPattern: false });
  bytes = null;
  // one short hearing to warm it up (and time it)
  const t0 = performance.now();
  await hear(new Float32Array(2 * SR));
  post({ type: "ready", warmMs: Math.round(performance.now() - t0) });
}

async function hear(x) {
  let peak = 0;
  for (let i = 0; i < x.length; i++) { const a = Math.abs(x[i]); if (a > peak) peak = a; }
  if (peak > 0.001 && peak < 0.5) {               // quiet sound is raised, as the laptop app does
    const k = 0.8 / peak, y = new Float32Array(x.length);
    for (let i = 0; i < x.length; i++) y[i] = x[i] * k;
    x = y;
  }
  const out = await session.run({
    audio: new ORT.Tensor("float32", x, [1, x.length]),
    audio_len: new ORT.Tensor("int64", BigInt64Array.from([BigInt(x.length)]), [1]),
  });
  const lp = out.log_probs, T = Number(out.out_len.data[0]), V = lp.dims[2], d = lp.data;
  const best = new Int16Array(T);
  for (let t = 0; t < T; t++) {
    let bi = 0, bv = -Infinity;
    for (let v = 0, o = t * V; v < V; v++) if (d[o + v] > bv) { bv = d[o + v]; bi = v; }
    best[t] = bi;
  }
  if (lp.dispose) lp.dispose();
  return best;
}

function decode(a, b) {                           // CTC: repeats and blanks out, then the word pieces
  const ids = []; let prev = -1;
  for (let k = a; k < b; k++) {
    const t = k - frameBase >= 0 && k - frameBase < frames.length ? frames[k - frameBase] : -1;
    if (t >= 0 && t !== BLANK && t !== prev) ids.push(t);
    prev = t;
  }
  let s = "";
  for (const i of ids) { if (kind[i] === "c") continue; s += kind[i] === "u" ? "\u0001" : pieces[i]; }
  return s.replace(/^▁+/, "").replace(/▁/g, " ").replace(/\u0001/g, " ⁇ ");
}

function add(chunk) {
  if (total - bufStart + chunk.length > buf.length) {        // keep the last KEEP_S seconds
    const drop = total - bufStart + chunk.length - buf.length;
    buf.copyWithin(0, drop, total - bufStart);
    bufStart += drop;
  }
  buf.set(chunk, total - bufStart);
  total += chunk.length;
  const needBase = Math.floor(bufStart / FR) - 64;           // frames: keep about as much as the sound
  if (needBase > frameBase + 100) {
    const shift = needBase - frameBase;
    frames.copyWithin(0, shift); frames.fill(-1, frames.length - shift); frameBase = needBase;
  }
}

async function step() {
  if (busy || !session) return;
  const end = Math.floor(total / FR) * FR;
  if (end - lastEnd < hop * SR || end - bufStart < 2 * SR) return;
  busy = true;
  try {
    const s0 = Math.max(Math.ceil(bufStart / FR) * FR, end - Math.round(WIN * SR / FR) * FR);
    const t0 = performance.now();
    const best = await hear(buf.slice(s0 - bufStart, end - bufStart));
    const ms = performance.now() - t0;
    runs++; runMs += ms;
    hop = Math.max(HOP_MIN, (ms / 1000) * 1.25);              // a slow phone hears less often
    const f0 = s0 / FR, leftF = LEFT * SR / FR;
    for (let j = 0; j < best.length; j++) {
      const k = f0 + j - frameBase;
      if (k < 0 || k >= frames.length) continue;
      if (j < leftF && frames[k] >= 0 && s0 > 0) continue;
      frames[k] = best[j];
    }
    lastEnd = end;
    const fe = end / FR, span = (sec) => decode(Math.max(0, fe - Math.round(sec * SR / FR)), fe);
    post({ type: "words", t: end / SR, t20: span(20), t10: span(10), t45: span(4.5), ms: Math.round(ms), hop });
  } catch (e) {
    post({ type: "error", text: "The speech model stopped: " + (e && e.message || e) });
  } finally {
    busy = false;
  }
  if (total - lastEnd >= hop * SR) setTimeout(step, 0);
}

self.onmessage = async (ev) => {
  const m = ev.data;
  if (m.type === "init") {
    try { await init(m.cfg); }
    catch (e) { post({ type: "error", text: "The speech model could not start: " + (e && e.message || e) }); }
  } else if (m.type === "audio") {
    add(new Float32Array(m.buf));
    step();
  } else if (m.type === "reset") {
    frames.fill(-1);
  } else if (m.type === "stats") {
    post({ type: "stats", runs, avgMs: runs ? Math.round(runMs / runs) : 0, hop, seconds: total / SR });
  }
};
