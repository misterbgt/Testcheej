#include <cstdlib>
#include <new>
void* operator new(size_t n) { return malloc(n ? n : 1); }
void* operator new[](size_t n) { return malloc(n ? n : 1); }
void operator delete(void* p) noexcept { free(p); }
void operator delete[](void* p) noexcept { free(p); }
void operator delete(void* p, size_t) noexcept { free(p); }
void operator delete[](void* p, size_t) noexcept { free(p); }
// the two pieces of the C++ library rapidfuzz needs (no libc++ is linked)
#include <cstddef>
namespace std { inline namespace __1 {
[[noreturn]] void __libcpp_verbose_abort(char const*, ...) { abort(); }
size_t __next_prime(size_t n) {
    if (n < 2) return 2;
    for (;; n++) {
        bool prime = (n % 2 != 0) || n == 2;
        for (size_t d = 3; prime && d * d <= n; d += 2)
            if (n % d == 0) prime = false;
        if (prime) return n;
    }
}
}}
