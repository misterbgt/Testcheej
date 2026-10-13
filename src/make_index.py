"""Make the web version's page (site/index.html) from the laptop app's phone controller
(pages/phone.html): the same page, talking to this phone's own engine (local.js) instead of
the laptop, listening with this phone's microphone, with a start-up panel, a full-screen
sangat screen and a way to try a recording. Each change below must find its place in
phone.html, or the build stops (so a change to phone.html can't silently break the web page).

usage: python make_index.py PHONE_HTML OUT_HTML VERSION VERSION_NAME   (build.py runs it)"""
import sys

SRC, OUT, VERSION, VERSION_NAME = sys.argv[1:5]
s = open(SRC, encoding="utf-8").read().replace("__VERSION_NAME__", VERSION_NAME).replace("__VERSION__", VERSION)


def sub(old, new, count=1):
    global s
    assert s.count(old) >= 1, f"not found in phone.html: {old[:80]}"
    s = s.replace(old, new, count)


# ---------------------------------------------------------------- head
sub('<title>Gurbani Audio Searcher (beta testing)</title>', '<title>Gurbani Audio Searcher</title>\n'
    '<meta name="apple-mobile-web-app-capable" content="yes">\n'
    '<meta name="apple-mobile-web-app-title" content="Gurbani">\n'
    '<link rel="apple-touch-icon" href="logo.png">')
sub('<link rel="icon" href="/logo64.png">', '<link rel="icon" href="logo64.png">')
sub('<img class="logo" src="/logo64.png"', '<img class="logo" src="logo64.png"')

# ---------------------------------------------------------------- styles for the new parts
sub('</style>', r'''
/* web version: start-up panel, sangat screen, recording */
.start { display: grid; gap: 12px; }
.start h2 { margin: 0; font-size: 19px; }
.start .row { display: grid; grid-template-columns: 1fr auto; gap: 4px 12px; align-items: center; }
.start .row b { font-weight: 600; }
.start .row span { color: var(--muted); font-size: 15px; grid-column: 1 / -1; }
.start .row.done span { color: var(--follow); }
.bar { height: 6px; border-radius: 3px; background: var(--rule); overflow: hidden; grid-column: 1 / -1; }
.bar i { display: block; height: 100%; width: 0; background: var(--kesri); transition: width .3s; }
.start .note { margin: 0; color: var(--muted); font-size: 15px; }
.start .err { margin: 0; color: var(--lost); font-weight: 600; }
.trybox { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.trybox .small { margin: 0; flex: 1 1 200px; }
.top .status { flex: 1 1 100%; }            /* the status on a row of its own: never cut short */
.screenbtn { border: 0; background: var(--btn); border-radius: 10px; min-height: 40px; padding: 0 12px; font-weight: 600; display: inline-flex; align-items: center; gap: 8px; }
.sangat { position: fixed; inset: 0; z-index: 20; background: #0B1324; color: #F3F1EC; display: grid; grid-template-rows: 1fr auto;
  padding: calc(env(safe-area-inset-top, 0px) + 16px) calc(env(safe-area-inset-right, 0px) + 20px) calc(env(safe-area-inset-bottom, 0px) + 12px) calc(env(safe-area-inset-left, 0px) + 20px); }
.sangat .body { display: flex; flex-direction: column; justify-content: center; gap: 2.2vh; text-align: center; min-height: 0; overflow: hidden; }
.sangat .g { font-family: var(--gur); font-size: clamp(30px, 7.2vmin, 96px); line-height: 1.35; color: #FFFFFF; margin: 0; text-wrap: balance; }
.sangat .en { font-size: clamp(17px, 3.6vmin, 44px); line-height: 1.35; color: #F2D9A6; margin: 0; text-wrap: balance; }
.sangat .nx { font-family: var(--gur); font-size: clamp(18px, 3.8vmin, 48px); color: #8EA0BF; margin: 0; text-wrap: balance; }
.sangat .msg { font-family: var(--gur); font-size: clamp(40px, 12vmin, 140px); color: #F2A33A; margin: 0; }
.sangat .msgtext { font-family: var(--ui); font-size: clamp(26px, 6vmin, 80px); color: #FFFFFF; margin: 0; }
.sangat img { max-width: 100%; max-height: 80vh; object-fit: contain; align-self: center; }
.sangat .foot { display: flex; justify-content: space-between; align-items: center; gap: 12px; color: #8EA0BF; font-size: 14px; }
.sangat .foot button { border: 1px solid #2A3C5E; background: transparent; color: #F3F1EC; border-radius: 10px; min-height: 40px; padding: 0 14px; font: inherit; }
</style>''')

# ---------------------------------------------------------------- header: no casting; a sangat screen button
sub('<button type="button" class="castbtn" id="castBtn"', '<button type="button" class="castbtn" hidden id="castBtn"')
sub('<select id="bani"', '<button type="button" class="screenbtn" id="screenBtn" aria-label="Show the sangat screen full screen">'
    '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M3 5h18v12H3zM8 19h8v2H8z"/></svg>Sangat screen</button>\n  <select id="bani"')

# ---------------------------------------------------------------- start-up panel and recording, top of "Now"
sub('<div id="tab-now">', '''<div id="tab-now">
  <section class="card start" id="startBox" aria-live="polite">
    <h2>Getting ready</h2>
    <div class="row" id="rowAsr"><b>Speech model</b><div class="bar"><i id="barAsr"></i></div><span id="txtAsr">Waiting</span></div>
    <div class="row" id="rowEng"><b>Gurbani engine</b><div class="bar"><i id="barEng"></i></div><span id="txtEng">Waiting</span></div>
    <p class="note">The first time, this downloads about 200 MB, so use Wi-Fi; after that the speech model is kept on this phone. Everything runs on this phone: nothing it hears is sent anywhere.</p>
    <p class="err" id="startErr" hidden></p>
  </section>''')
sub('<section class="lines" id="linesBox" hidden>', '''<section class="card" id="tryBox">
    <div class="trybox">
      <p class="small">To try it without live kirtan, play a recording (an audio file on this phone) through it instead of the microphone.</p>
      <button type="button" class="btn slim" id="tryPick">Play a recording</button>
      <button type="button" class="btn slim" id="tryStop" hidden>Stop the recording</button>
      <input type="file" id="tryFile" accept="audio/*,video/*" hidden>
    </div>
    <p class="small" id="tryNote" style="margin:8px 0 0" hidden></p>
  </section>

  <section class="lines" id="linesBox" hidden>''')

# ---------------------------------------------------------------- the sangat screen
sub('<nav class="controls"', '''<div class="sangat" id="sangat" hidden role="dialog" aria-label="Sangat screen">
  <div class="body" id="sgBody"><p class="g" id="sgG"></p><p class="en" id="sgEn"></p><p class="nx" id="sgNx"></p></div>
  <div class="foot"><span id="sgWhere"></span><button type="button" id="sgClose">Close</button></div>
</div>

<nav class="controls"''')

# ---------------------------------------------------------------- messages: pictures stay on this phone, one screen
sub('<div class="where-to">', '<div class="where-to" hidden>')
sub('<h2>Show on</h2>', '')
sub('<p class="small" style="margin:0 !important">Shows on the screens instead of the Gurbani. Listening carries on; "Back to Gurbani" returns to the current line.</p>',
    '<p class="small" style="margin:0 !important">Shows on the sangat screen instead of the Gurbani. Listening carries on; "Back to Gurbani" returns to the current line.</p>')
sub('const im = document.createElement("img"); im.src = "/message-image/" + n;',
    'const im = document.createElement("img"); im.src = LOCAL.imageURL(n);')
sub('''    const r = await fetch("/api/message-image", { method: "POST", body: await shrink(f) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { banner(j.error || "That picture could not be used."); return; }
    banner(""); sendMsg({ kind: "image", image: j.image });
  } catch (e) { banner("That picture could not be sent to the console. Check this phone is on the same Wi-Fi."); }''',
    '''    const name = LOCAL.saveImage(await shrink(f));
    banner(""); sendMsg({ kind: "image", image: name });
  } catch (e) { banner("That picture could not be used."); }''')
sub('const where = m.screens && m.overlay ? "projector, TV and livestream" : m.screens ? "projector and TV" : "livestream";',
    'const where = "sangat screen";')

# ---------------------------------------------------------------- the microphone is this phone's
sub('<button type="button" class="btn listen" id="listen" aria-pressed="false">Listen with this phone<span',
    '<button type="button" class="btn listen" id="listen" aria-pressed="false">Start listening<span')
sub('const MIC = { id: null, secure: location.protocol === "https:",', 'const MIC = { id: null, secure: true,')
sub('''function renderMic() {
  $("listen").setAttribute("aria-pressed", String(MIC.on));
  $("listen").firstChild.textContent = MIC.on ? "Give mic back to laptop" : "Listen with this phone";
  const o = MIC.owner;
  $("micLine").textContent = !o ? "" : MIC.on ? "Listening with this phone's microphone."
    : o.owner === "phone" ? `Listening with ${o.name}'s microphone.` : "Listening with the laptop's microphone.";
}''', '''function renderMic() {
  $("listen").setAttribute("aria-pressed", String(MIC.on));
  $("listen").firstChild.textContent = MIC.on ? "Stop listening" : "Start listening";
  $("micLine").textContent = MIC.on ? "Listening with this phone's microphone. Keep this page open and the phone unlocked." : "";
}''')
sub('''$("listen").onclick = async () => {
  if (MIC.on) { stopPhoneMic(true); return; }
  if (!MIC.secure) {
    if (!MIC.httpsPort) { banner("This console can't offer a secure address, so phones can't be the microphone. Check the log on the laptop."); return; }
    $("secureSheet").hidden = false; tab("now"); scrollTo(0, 0); return;
  }
  try { await startPhoneMic(); }
  catch (e) { stopPhoneMic(false); banner("The microphone couldn't be opened. Allow microphone access for this page in the browser's settings, then try again."); }
};''', '''$("listen").onclick = async () => {
  if (MIC.on) { stopPhoneMic(true); return; }
  if (LOCAL.player) stopTry();
  try { await startPhoneMic(); }
  catch (e) { stopPhoneMic(false); banner("The microphone couldn't be opened. In Safari, tap aA in the address bar, then Website Settings, and allow the Microphone; then try again."); }
};''')
sub('''MIC.stream.getAudioTracks()[0].onended = () => { stopPhoneMic(true); banner("This phone's microphone stopped. The laptop's microphone has taken over."); };''',
    '''MIC.stream.getAudioTracks()[0].onended = () => { stopPhoneMic(true); banner("This phone's microphone stopped (another app may have taken it). Tap Start listening again."); };''')

# ---------------------------------------------------------------- connection: this phone's engine
sub('''  ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws?role=remote`);''',
    '''  ws = new LOCAL.Socket("local");''')
sub('''function checkVersion(v) {''', '''function checkVersion(v) {
  return;                              // the web version updates with the page itself''')
sub('''  else if (m.type === "loading") $("statusText").textContent = "The console is starting";''',
    '''  else if (m.type === "loading") $("statusText").textContent = "Getting ready";''')
sub('<span id="statusText">Connecting to the console</span>', '<span id="statusText">Getting ready</span>')
sub('<p class="empty" id="empty">Nothing is on the screen yet. It appears here as soon as the console recognises the kirtan or paath.</p>',
    '<p class="empty" id="empty">Nothing is on the screen yet. Tap Start listening below; the Gurbani appears here as soon as the kirtan or paath is recognised.</p>')

# ---------------------------------------------------------------- web-only code, after the page's own
sub('''connect();
render();
})();''', r'''connect();
render();

/* ---------------- web version: start-up, sangat screen, recordings ---------------- */
function pctOf(text) { const m = /(\d+)%/.exec(text || ""); return m ? +m[1] : null; }
function renderStart() {
  const L = LOCAL;
  const row = (who, bar, txt, rowId) => {
    const done = L.ready[who], t = done ? "Ready" : L.progress[who];
    $(txt).textContent = t; $(rowId).classList.toggle("done", done);
    const p = done ? 100 : pctOf(t);
    $(bar).style.width = (p === null ? (t === "Waiting" ? 2 : 50) : p) + "%";
  };
  row("asr", "barAsr", "txtAsr", "rowAsr"); row("engine", "barEng", "txtEng", "rowEng");
  $("startErr").hidden = !L.error; $("startErr").textContent = L.error || "";
  const ready = L.ready.asr && L.ready.engine;
  $("startBox").hidden = ready && !L.error;
  $("listen").disabled = !ready;
  $("tryPick").disabled = !ready;
}
LOCAL.on((kind) => { if (kind === "progress" || kind === "ready" || kind === "error") renderStart(); });
renderStart();

function stopTry() { LOCAL.stopFile(); $("tryStop").hidden = true; $("tryPick").hidden = false; $("tryNote").hidden = true; }
$("tryPick").onclick = () => $("tryFile").click();
$("tryStop").onclick = stopTry;
$("tryFile").onchange = async () => {
  const f = $("tryFile").files[0]; $("tryFile").value = "";
  if (!f) return;
  if (MIC.on) stopPhoneMic(true);
  $("tryNote").hidden = false; $("tryNote").textContent = "Reading the recording…";
  try {
    const pl = await LOCAL.playFile(f, () => { stopTry(); banner("The recording has finished."); });
    $("tryPick").hidden = true; $("tryStop").hidden = false;
    const tick = setInterval(() => {
      if (!LOCAL.player) { clearInterval(tick); return; }
      const s = Math.floor(LOCAL.player.pos), d = Math.floor(pl.duration);
      $("tryNote").textContent = `Playing ${f.name} through the app: ${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")} of ${Math.floor(d / 60)}:${String(d % 60).padStart(2, "0")} (silently)`;
    }, 1000);
  } catch (e) { $("tryNote").textContent = "That file couldn't be read. Try an MP3, M4A or WAV."; }
};

function renderSangat() {
  if ($("sangat").hidden) return;
  const st = S.state, m = S.msg;
  const track = st && st.track_id ? S.tracks[st.track_id] : null;
  const pos = st ? (st.pos !== null && st.pos !== undefined ? st.pos : st.last_pos) : null;
  const body = $("sgBody");
  if (m && m.screens) {
    body.replaceChildren();
    if (m.kind === "image") { const im = document.createElement("img"); im.src = m.image; im.alt = ""; body.append(im); }
    else { const p = document.createElement("p"); p.className = m.kind === "vaheguru" ? "msg" : (/[਀-੿]/.test(m.text) ? "msg" : "msgtext"); p.textContent = m.text; body.append(p); }
    $("sgWhere").textContent = "";
    return;
  }
  if (!$("sgG")) body.innerHTML = '<p class="g" id="sgG"></p><p class="en" id="sgEn"></p><p class="nx" id="sgNx"></p>';
  if (!track || pos === null || pos === undefined) { $("sgG").textContent = "ੴ ਸਤਿਗੁਰ ਪ੍ਰਸਾਦਿ ॥"; $("sgEn").textContent = ""; $("sgNx").textContent = ""; $("sgWhere").textContent = ""; return; }
  const Ls = track.lines, line = Ls[pos] || {};
  const np = st.next_pos !== undefined && st.next_pos !== null ? st.next_pos : (pos + 1 < Ls.length ? pos + 1 : null);
  const set = SETTINGS_WEB();
  $("sgG").textContent = line.g || "";
  $("sgEn").textContent = set.en === false ? "" : (line.en || "");
  $("sgNx").textContent = set.next === false || np === null || !Ls[np] ? "" : Ls[np].g;
  $("sgWhere").textContent = [line.ang ? `Ang ${line.ang}` : (line.ref || ""), track.kind === "bani" ? track.subtitle : ""].filter(Boolean).join(" · ");
}
let WEB_SETTINGS = {};
const SETTINGS_WEB = () => WEB_SETTINGS;
LOCAL.on(() => {});
const _recv = receive;
receive = function (m) { if (m.type === "settings") WEB_SETTINGS = m.settings || {}; _recv(m); };
const _render = render;
render = function () { _render(); renderSangat(); };
let wake = null;
$("screenBtn").onclick = async () => {
  $("sangat").hidden = false; renderSangat();
  try { if ("wakeLock" in navigator && !wake) wake = await navigator.wakeLock.request("screen"); } catch (e) { /* not offered */ }
};
$("sgClose").onclick = () => { $("sangat").hidden = true; if (wake && !MIC.on) { wake.release().catch(() => {}); wake = null; } };
})();''')

# the page's own functions are declared with "function": allow them to be wrapped above
s = s.replace("function receive(m) {", "var receive = function (m) {", 1)
s = s.replace("function render() {", "var render = function () {", 1)
sub('<script>\n(() => {', f'<script src="local.js?v={VERSION}"></script>\n<script>\n(() => {{')

open(OUT, "w", encoding="utf-8").write(s)
print("wrote", OUT, len(s))
