#include "native_recovery.hpp"
#include <cstdlib>
#include <iostream>
#include <new>

static bool watching = false;
static unsigned allocations = 0;
void* operator new(std::size_t size) {
  if (watching) ++allocations;
  if (auto* pointer = std::malloc(size ? size : 1)) return pointer;
  throw std::bad_alloc();
}
void* operator new[](std::size_t size) { return ::operator new(size); }
void operator delete(void* pointer) noexcept { std::free(pointer); }
void operator delete[](void* pointer) noexcept { std::free(pointer); }
void operator delete(void* pointer, std::size_t) noexcept { std::free(pointer); }
void operator delete[](void* pointer, std::size_t) noexcept { std::free(pointer); }

int main() {
  using P = aura::NativeRecovery;
  constexpr auto second = 1'000'000'000ULL;
  bool passed = true;
  watching = true;
  P p;
  passed &= p.fault(100 * second, {true,false,true,false}, {10,0,100 * second,true});
  passed &= p.due(110 * second, {11,0,110 * second,true});
  passed &= p.admitted(110 * second, {11,0,110 * second,true});
  passed &= !p.success(111 * second, {true,true,true,0,120 * second});
  P::Seed seed;
  passed &= p.export_seed(111 * second, seed);
  P q;
  passed &= q.import_seed(seed, 112 * second, {12,0,112 * second,true});
  passed &= !q.success(112 * second, {true,true,true,0,120 * second});
  passed &= q.success(113 * second, {true,true,true,0,120 * second});
  passed &= q.normal_allowed();
  passed &= !q.primary_failed();
  passed &= !q.import_seed(seed, 114 * second, {13,0,114 * second,true});
  passed &= q.fault(114 * second, {false,true,false,true}, {13,0,114 * second,true});
  passed &= q.snapshot().phase == P::Phase::latched;
  passed &= !q.due(1000 * second, {100,0,1000 * second,true});
  passed &= q.error() == P::Error::none;
  watching = false;
  std::cout << "{\"passed\":" << (passed && allocations == 0 ? "true" : "false")
      << ",\"allocations_in_policy_operations\":" << allocations
      << ",\"policy_size_bytes\":" << sizeof(P) << ",\"scope\":\"host allocation hook; no hardware\"}\n";
  return passed && allocations == 0 ? 0 : 1;
}
