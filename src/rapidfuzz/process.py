import numpy as np
import rfjs
from pyodide.ffi import to_js

from . import fuzz

_pools: dict = {}            # id(list) -> the list, for choice lists scored again and again
POOL_MIN = 500


def _scorer_id(scorer):
    if scorer is fuzz.partial_ratio:
        return 1
    if scorer is fuzz.ratio or scorer is None:
        return 0
    return None


def _listed(choices):
    """(keys, values) of a list or a dict of choices; big ones are remembered (and
    sent to the scorer once) as long as the same object is passed."""
    key = id(choices)
    hit = _pools.get(key)
    if hit is not None and hit[0] is choices:
        return hit[1], hit[2], key
    if hasattr(choices, "items"):
        keys, vals = list(choices.keys()), list(choices.values())
    else:
        vals = list(choices)
        keys = list(range(len(vals)))
    if len(vals) >= POOL_MIN:
        _pools[key] = (choices, keys, vals)
        rfjs.pool(str(key), to_js([c if c is not None else "" for c in vals]))
        return keys, vals, key
    return keys, vals, None


def _scores(query, vals, pool, sc, cutoff):
    if pool is not None:
        return np.frombuffer(rfjs.poolScore(str(pool), query, sc, cutoff).to_py(), dtype=np.float64).copy()
    res = rfjs.cdist(to_js([query]), to_js([c if c is not None else "" for c in vals]), sc, cutoff)
    return np.frombuffer(res.to_py(), dtype=np.float32).astype(np.float64)


def extract(query, choices, *, scorer=None, processor=None, limit=5, score_cutoff=None, **kwargs):
    """As rapidfuzz.process.extract: [(choice, score, index or key)], best first
    (equal scores in the choices' order)."""
    if processor is not None:
        query = processor(query)
        choices = {k: processor(v) for k, v in choices.items()} if hasattr(choices, "items") \
            else [processor(c) for c in choices]
    keys, vals, pool = _listed(choices)
    if not vals:
        return []
    sc = _scorer_id(scorer)
    if sc is None:                                   # another scorer: plain Python
        s = np.array([scorer(query, c) if c is not None else -1.0 for c in vals], dtype=np.float64)
    else:
        s = _scores(query, vals, pool, sc, score_cutoff or 0)
    cut = score_cutoff or 0
    idx = np.nonzero(s >= cut)[0]
    if limit is not None and len(idx) > limit:
        part = idx[np.argpartition(-s[idx], limit - 1)[:limit]]
        kth = s[part].min()
        idx = idx[s[idx] >= kth]
    order = sorted(idx.tolist(), key=lambda i: (-s[i], i))
    out = [(vals[i], float(s[i]), keys[i]) for i in order if vals[i] is not None]
    return out[:limit] if limit is not None else out


def cdist(queries, choices, *, scorer=None, processor=None, score_cutoff=None, dtype=None, workers=1, **kwargs):
    """As rapidfuzz.process.cdist: a len(queries) x len(choices) matrix of scores."""
    queries, choices = list(queries), list(choices)
    if processor is not None:
        queries = [processor(q) for q in queries]
        choices = [processor(c) for c in choices]
    sc = _scorer_id(scorer)
    nq, nc = len(queries), len(choices)
    if sc is None:
        m = np.array([[scorer(q, c) for c in choices] for q in queries], dtype=np.float32).reshape(nq, nc)
    elif not nq or not nc:
        m = np.zeros((nq, nc), dtype=np.float32)
    else:
        res = rfjs.cdist(to_js(queries), to_js(choices), sc, score_cutoff or 0)
        m = np.frombuffer(res.to_py(), dtype=np.float32).reshape(nq, nc).copy()
    return m.astype(dtype) if dtype is not None else m
