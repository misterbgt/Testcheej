// rapidfuzz for the browser: the ratio and partial_ratio scorers of rapidfuzz-cpp
// (the C++ core of the Python rapidfuzz package), on UTF-16 strings from JavaScript.
// standard headers first, then rapidfuzz with its argument-check throws as no-ops (built without exceptions)
#include <algorithm>
#include <array>
#include <bitset>
#include <cassert>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iterator>
#include <limits>
#include <numeric>
#include <ostream>
#include <stdexcept>
#include <type_traits>
#include <unordered_set>
#include <utility>
#include <vector>
#include <string>
#include <cstdlib>
#define throw (void)
#include <rapidfuzz/fuzz.hpp>
#undef throw
#include <cstdint>
#include <cstdlib>
#include <string>
#include <vector>

using namespace rapidfuzz;
typedef uint16_t ch;
typedef std::basic_string<ch> str;

#define EXPORT(name) __attribute__((export_name(#name)))

namespace {
struct Pool { std::vector<str> items; };
std::vector<Pool*> pools;
}

extern "C" {

EXPORT(rf_alloc) void* rf_alloc(size_t n) { return malloc(n ? n : 1); }
EXPORT(rf_free) void rf_free(void* p) { free(p); }

EXPORT(rf_ratio) double rf_ratio(const ch* a, int na, const ch* b, int nb, double cutoff) {
    return fuzz::ratio(a, a + na, b, b + nb, cutoff);
}

EXPORT(rf_partial_ratio) double rf_partial_ratio(const ch* a, int na, const ch* b, int nb, double cutoff) {
    return fuzz::partial_ratio(a, a + na, b, b + nb, cutoff);
}

EXPORT(rf_pool_new) int rf_pool_new() {
    pools.push_back(new Pool());
    return (int)pools.size() - 1;
}

EXPORT(rf_pool_add) void rf_pool_add(int id, const ch* s, int n) { pools[id]->items.emplace_back(s, s + n); }

EXPORT(rf_pool_size) int rf_pool_size(int id) { return (int)pools[id]->items.size(); }

EXPORT(rf_pool_drop) void rf_pool_drop(int id) {
    delete pools[id];
    pools[id] = new Pool();
}

// score the query against every string of the pool: scorer 0 = ratio, 1 = partial_ratio
EXPORT(rf_pool_score) void rf_pool_score(int id, const ch* q, int nq, int scorer, double cutoff, double* out) {
    const std::vector<str>& items = pools[id]->items;
    size_t n = items.size();
    if (scorer == 1) {
        fuzz::CachedPartialRatio<ch> sc(q, q + nq);
        for (size_t i = 0; i < n; i++) out[i] = sc.similarity(items[i], cutoff);
    } else {
        fuzz::CachedRatio<ch> sc(q, q + nq);
        for (size_t i = 0; i < n; i++) out[i] = sc.similarity(items[i], cutoff);
    }
}

// queries x choices, each packed end to end with their lengths
EXPORT(rf_cdist) void rf_cdist(const ch* qbuf, const int* qlen, int nq, const ch* cbuf, const int* clen, int nc,
                               int scorer, double cutoff, float* out) {
    std::vector<size_t> coff(nc + 1, 0);
    for (int j = 0; j < nc; j++) coff[j + 1] = coff[j] + clen[j];
    size_t qo = 0;
    for (int i = 0; i < nq; i++) {
        const ch* q = qbuf + qo;
        if (scorer == 1) {
            fuzz::CachedPartialRatio<ch> sc(q, q + qlen[i]);
            for (int j = 0; j < nc; j++)
                out[(size_t)i * nc + j] = (float)sc.similarity(cbuf + coff[j], cbuf + coff[j + 1], cutoff);
        } else {
            fuzz::CachedRatio<ch> sc(q, q + qlen[i]);
            for (int j = 0; j < nc; j++)
                out[(size_t)i * nc + j] = (float)sc.similarity(cbuf + coff[j], cbuf + coff[j + 1], cutoff);
        }
        qo += qlen[i];
    }
}
}
