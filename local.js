// The web version's stand-in for the laptop app: instead of a websocket to the laptop,
// the page talks to two workers on this phone - asr-worker.js (sound -> words) and
// engine-worker.js (words -> Gurbani, with the laptop app's own engine). The page's code
// is the phone controller's, unchanged where it can be: it opens a "WebSocket", sends the
// same commands and gets the same messages.
(function () {
  "use strict";
  const P = new URLSearchParams(location.search);
  const here = (p) => new URL(p, location.href).href;
  const CFG = {
    pyodide: P.has("local") ? here("vendor/pyodide/") : "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/",
    ort: P.has("local") ? here("vendor/ort/") : "https://cdn.jsdelivr.net/npm/onnxruntime-web@1.22.0/dist/",
    model: P.get("model") ? here(P.get("model"))
      : "https://huggingface.co/karansea/indicconformer-stt-pa-ctc-shabad-preview/resolve/main/v4.int8.onnx",
    vocab: here("vocab.json"),
    app: here("app.zip"),
  };
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private browsing: not kept */ } },
  };

  const L = {
    cfg: CFG, clients: new Set(), ready: { asr: false, engine: false }, progress: { asr: "Waiting", engine: "Waiting" },
    error: null, images: new Map(), last: { track: null, state: null }, listeners: new Set(), stats: {},
  };
  window.LOCAL = L;

  function emit(kind, data) { for (const f of L.listeners) try { f(kind, data); } catch (e) { console.error(e); } }
  L.on = (f) => { L.listeners.add(f); return () => L.listeners.delete(f); };

  // ---------------------------------------------------------------- workers
  const asr = new Worker("asr-worker.js", { type: "module" }), engine = new Worker("engine-worker.js");
  asr.onmessage = (ev) => {
    const m = ev.data;
    if (m.type === "progress") { L.progress.asr = m.text; emit("progress", { who: "asr", ...m }); }
    else if (m.type === "ready") { L.ready.asr = true; L.progress.asr = "Ready"; L.stats.warmMs = m.warmMs; emit("ready", { who: "asr" }); }
    else if (m.type === "words") {
      L.stats.asrMs = m.ms; L.stats.hop = m.hop; L.lastWords = m;
      emit("words", m);
      if (L.ready.engine) engine.postMessage(m);
    } else if (m.type === "error") { fail(m.text); }
    else if (m.type === "note") { notice(m.text); }
    else if (m.type === "stats") emit("stats", m);
  };
  engine.onmessage = (ev) => {
    const m = ev.data;
    if (m.type === "progress") { L.progress.engine = m.text; emit("progress", { who: "engine", ...m }); }
    else if (m.type === "ready") { L.ready.engine = true; L.progress.engine = "Ready"; L.stats.loadS = m.loadS; emit("ready", { who: "engine" }); }
    else if (m.type === "msgs") {
      if (m.ms !== undefined) L.stats.engineMs = m.ms;
      for (const x of m.msgs) {
        if (x.type === "settings") store.set("gas-settings", x.settings);
        if (x.type === "screen_msg") store.set("gas-texts", x.recent_texts || []);
        if (x.type === "track") L.last.track = x;
        if (x.type === "state") L.last.state = x;
      }
      broadcast(m.msgs);
    } else if (m.type === "error") { if (m.fatal) fail(m.text); else notice(m.text); }
  };
  asr.onerror = (e) => fail("The speech model stopped (the phone may be short of memory). Close other apps and tabs, then reload this page.");
  engine.onerror = (e) => fail("The Gurbani engine stopped (the phone may be short of memory). Close other apps and tabs, then reload this page.");
  function fail(text) { L.error = text; emit("error", text); broadcast([{ type: "notice", message: text }]); }
  function notice(text) { broadcast([{ type: "notice", message: text }]); }

  asr.postMessage({ type: "init", cfg: CFG });
  engine.postMessage({ type: "init", cfg: { ...CFG, settings: store.get("gas-settings", {}), texts: store.get("gas-texts", []) } });

  // ---------------------------------------------------------------- the page's "websocket"
  function broadcast(msgs) {
    for (const c of L.clients) for (const x of msgs) c._deliver(x);
  }
  class LocalSocket {
    constructor(url) {
      this.url = url; this.readyState = 0; this.binaryType = "arraybuffer";
      this.onopen = this.onmessage = this.onclose = this.onerror = null;
      setTimeout(() => {
        this.readyState = 1; L.clients.add(this);
        if (this.onopen) this.onopen({});
        if (!(L.ready.engine)) this._deliver({ type: "loading", message: "Starting" });
        else engine.postMessage({ type: "cmd", c: { cmd: "hello" } });         // banis, settings, history, state
        if (L.last.track) this._deliver(L.last.track);
        if (L.last.state) this._deliver(L.last.state);
      }, 0);
    }
    _deliver(m) {
      if (this.readyState !== 1 || !this.onmessage) return;
      m = mapImages(m);
      this.onmessage({ data: JSON.stringify(m) });
    }
    send(data) {
      if (typeof data !== "string") { L.audio(data); return; }
      let c; try { c = JSON.parse(data); } catch (e) { return; }
      if (c.cmd === "mic_take" || c.cmd === "mic_release" || (c.cmd || "").startsWith("cast_")) return;
      if (c.cmd === "reset") asr.postMessage({ type: "reset" });
      if (!L.ready.engine) { this._deliver({ type: "notice", message: "Still starting. Try again in a moment." }); return; }
      engine.postMessage({ type: "cmd", c });
    }
    close() { this.readyState = 3; L.clients.delete(this); }
  }
  L.Socket = LocalSocket;
  L.command = (c) => { if (L.ready.engine) engine.postMessage({ type: "cmd", c }); };

  // ---------------------------------------------------------------- sound
  L.secondsHeard = 0;
  L.audio = (buffer) => {               // Float32 samples at 16 kHz (an ArrayBuffer)
    const n = buffer.byteLength / 4;
    L.secondsHeard += n / 16000;
    if (L.ready.asr) asr.postMessage({ type: "audio", buf: buffer }, [buffer]);
  };
  L.askStats = () => asr.postMessage({ type: "stats" });

  // a recording instead of the microphone (to try it out): fed in at real speed
  L.player = null;
  L.playFile = async (file, onEnd) => {
    L.stopFile();
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const data = await ctx.decodeAudioData(await file.arrayBuffer());
    ctx.close && ctx.close();
    const n16 = Math.ceil(data.duration * 16000);
    const off = new (window.OfflineAudioContext || window.webkitOfflineAudioContext)(1, n16, 16000);
    const src = off.createBufferSource(); src.buffer = data; src.connect(off.destination); src.start();
    const pcm = (await off.startRendering()).getChannelData(0);
    let pos = 0;
    const speed = +P.get("speed") || 1, CH = 8000;
    const timer = setInterval(() => {
      if (pos >= pcm.length) { L.stopFile(); if (onEnd) onEnd(); return; }
      const c = pcm.slice(pos, pos + CH); pos += CH;
      L.audio(c.buffer);
      emit("level", rms(c));
    }, 500 / speed);
    L.player = { timer, get pos() { return pos / 16000; }, duration: pcm.length / 16000 };
    return L.player;
  };
  L.stopFile = () => { if (L.player) { clearInterval(L.player.timer); L.player = null; } };
  function rms(c) { let s = 0; for (let i = 0; i < c.length; i++) s += c[i] * c[i]; return Math.sqrt(s / Math.max(1, c.length)); }

  // ---------------------------------------------------------------- pictures stay on this phone
  L.saveImage = (blob) => {
    const hex = Array.from(crypto.getRandomValues(new Uint8Array(8)), b => b.toString(16).padStart(2, "0")).join("");
    const ext = /png/.test(blob.type) ? "png" : /gif/.test(blob.type) ? "gif" : "jpg";
    const name = `${hex}.${ext}`;
    L.images.set(name, URL.createObjectURL(blob));
    return name;
  };
  L.imageURL = (nameOrPath) => {
    const name = String(nameOrPath || "").split("/").pop();
    return L.images.get(name) || "";
  };
  function mapImages(m) {
    if (m.type === "screen_msg") {
      const imgs = (m.recent_images || []).filter(n => L.images.has(n));
      const msg = m.msg && m.msg.kind === "image" ? { ...m.msg, image: L.imageURL(m.msg.image) } : m.msg;
      return { ...m, msg, recent_images: imgs };
    }
    return m;
  }
})();
