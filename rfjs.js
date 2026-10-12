// rapidfuzz scorers (ratio, partial_ratio) compiled to WebAssembly from rapidfuzz-cpp,
// for the Python engine running in Pyodide (python side: rapidfuzz/ shim package).
// Works in a browser worker and in Node (for testing).
(function (root) {
  let ex = null, mem = null;
  const pools = new Map();            // pool key -> wasm pool id

  async function load(urlOrBytes) {
    let bytes = urlOrBytes;
    if (typeof urlOrBytes === "string") bytes = await (await fetch(urlOrBytes)).arrayBuffer();
    const { instance } = await WebAssembly.instantiate(bytes, {});
    ex = instance.exports;
    if (ex._initialize) ex._initialize();
    return api;
  }

  function u16() { return new Uint16Array(ex.memory.buffer); }
  function put(s) {                    // copy a JS string into wasm memory as UTF-16
    const p = ex.rf_alloc(s.length * 2);
    const m = u16(), o = p >> 1;
    for (let i = 0; i < s.length; i++) m[o + i] = s.charCodeAt(i);
    return p;
  }
  function score2(fn, a, b, cutoff) {
    const pa = put(a), pb = put(b);
    const r = fn(pa, a.length, pb, b.length, cutoff || 0);
    ex.rf_free(pa); ex.rf_free(pb);
    return r;
  }
  const ratio = (a, b, c) => score2(ex.rf_ratio, a, b, c);
  const partial_ratio = (a, b, c) => score2(ex.rf_partial_ratio, a, b, c);

  function pool(key, strings) {        // register a list of choices once
    if (pools.has(key)) return pools.get(key);
    const id = ex.rf_pool_new();
    for (const s of strings) { const p = put(s); ex.rf_pool_add(id, p, s.length); ex.rf_free(p); }
    pools.set(key, id);
    return id;
  }
  function hasPool(key) { return pools.has(key); }
  // scores of query against every pool string: Float64Array (scorer 0 ratio, 1 partial_ratio)
  function poolScore(key, query, scorer, cutoff) {
    const id = pools.get(key), n = ex.rf_pool_size(id);
    const pq = put(query), out = ex.rf_alloc(n * 8);
    ex.rf_pool_score(id, pq, query.length, scorer, cutoff || 0, out);
    const res = new Float64Array(ex.memory.buffer, out, n).slice();
    ex.rf_free(pq); ex.rf_free(out);
    return res;
  }
  function pack(list) {
    let total = 0; for (const s of list) total += s.length;
    const buf = ex.rf_alloc(total * 2), lens = ex.rf_alloc(list.length * 4);
    const m = u16(), l = new Int32Array(ex.memory.buffer, lens, list.length);
    let o = buf >> 1;
    list.forEach((s, i) => { for (let k = 0; k < s.length; k++) m[o + k] = s.charCodeAt(k); o += s.length; l[i] = s.length; });
    return [buf, lens];
  }
  // queries x choices matrix as a Float32Array (row-major)
  function cdist(queries, choices, scorer, cutoff) {
    const nq = queries.length, nc = choices.length;
    if (!nq || !nc) return new Float32Array(0);
    const [qb, ql] = pack(queries), [cb, cl] = pack(choices);
    const out = ex.rf_alloc(nq * nc * 4);
    ex.rf_cdist(qb, ql, nq, cb, cl, nc, scorer, cutoff || 0, out);
    const res = new Float32Array(ex.memory.buffer, out, nq * nc).slice();
    [qb, ql, cb, cl, out].forEach(p => ex.rf_free(p));
    return res;
  }
  const api = { load, ratio, partial_ratio, pool, hasPool, poolScore, cdist };
  root.rfjs = api;
  if (typeof module !== "undefined") module.exports = api;
})(typeof self !== "undefined" ? self : globalThis);
