#include "tensor_layout.hpp"
#include "native_bridge.h"
#include <iostream>
#include <stdexcept>
static void check(bool value) { if (!value) throw std::runtime_error("layout contract failed"); }
template<class F> void rejects(F value) {
  bool rejected = false;try { value(); } catch (const std::exception&) { rejected = true; }check(rejected);
}
int main() {
  try {
    aura::Int8Layout yunet({1,320,320,3});check(yunet.bytes() == 307200);
    check(yunet.offset({0,1,2,1}) == 967);check(yunet.offset({}) == 0);
    aura::Int8Layout sface({1,128});check(sface.offset({0,127}) == 127);
    rejects([] { aura::Int8Layout bad({2,112,112,3}); });
    rejects([] { aura::Int8Layout bad({1,2147483647,2147483647}); });
    rejects([&] { yunet.offset({0,320,0,0}); });
    rejects([&] { yunet.offset({0,-1,0,0}); });
    rejects([&] { yunet.offset({0}); });
    check(sizeof(AuraNativeReport) == 64);
    std::cout << "{\"passed\":true,\"groups\":6,\"scope\":\"bounded int8 layout and C report ABI only; no VART/model calls\"}\n";
    return 0;
  } catch (const std::exception& error) { std::cerr << error.what() << '\n';return 1; }
}
