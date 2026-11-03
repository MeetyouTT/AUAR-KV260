// GCC 11 allocator headers call this helper, exported only since GLIBCXX_3.4.29.
// Keep the identical standard exception semantics using the older public type.
// This hidden helper does not replace any trajectory computation.
#include <new>
namespace std {
[[noreturn]] __attribute__((visibility("hidden")))
void __throw_bad_array_new_length() {throw bad_array_new_length();}
}
