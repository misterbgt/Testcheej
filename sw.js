// Keeps the engine's files on the phone, so the page opens without downloading them again
// (and works with no signal once it has run once). The speech model is kept separately,
// by asr-worker.js. Registered by local.js as sw.js?v=BUILD: a new build is a new cache,
// and the old one is deleted.
"use strict";
const BUILD = new URL(self.location.href).searchParams.get("v") || "dev";
const CACHE = "gurbani-app-" + BUILD;

// Fetched fresh whenever there is a connection (so a new version is noticed), the saved copy otherwise.
const FRESH = (u) => u.origin === self.location.origin && /(\/|index\.html|local\.js|sw\.js)$/.test(u.pathname);
// Kept for good once got: every file asked for with the build in its name, and the pinned
// Pyodide / onnxruntime files from the CDN. The speech model (Hugging Face) is not touched here.
const KEEP = (u) => (u.origin === self.location.origin) || u.hostname === "cdn.jsdelivr.net";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil((async () => {
  for (const k of await caches.keys()) if (k.startsWith("gurbani-app-") && k !== CACHE) await caches.delete(k);
  await self.clients.claim();
})()));

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || req.headers.has("range")) return;
  const u = new URL(req.url);
  if (!KEEP(u)) return;
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const store = (res) => { if (res && (res.ok || res.type === "opaque")) cache.put(req, res.clone()).catch(() => {}); return res; };
    if (req.mode === "navigate" || FRESH(u)) {
      try { return store(await fetch(req)); }
      catch (err) { const hit = await cache.match(req, { ignoreSearch: false }) || await cache.match(u.origin + u.pathname) ; if (hit) return hit; throw err; }
    }
    const hit = await cache.match(req);
    if (hit) return hit;
    return store(await fetch(req));
  })());
});
