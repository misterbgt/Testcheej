import rfjs

_cache: dict = {}            # word pairs come back again and again: remember their scores


def ratio(s1, s2, *, processor=None, score_cutoff=None):
    if s1 is None or s2 is None:
        return 0.0
    if processor is not None:
        s1, s2 = processor(s1), processor(s2)
    key = (s1, s2)
    r = _cache.get(key)
    if r is None:
        r = rfjs.ratio(s1, s2, 0)
        if len(_cache) > 200000:
            _cache.clear()
        _cache[key] = r
    return r if score_cutoff is None or r >= score_cutoff else 0.0


def partial_ratio(s1, s2, *, processor=None, score_cutoff=None):
    if s1 is None or s2 is None:
        return 0.0
    if processor is not None:
        s1, s2 = processor(s1), processor(s2)
    return rfjs.partial_ratio(s1, s2, score_cutoff or 0)
