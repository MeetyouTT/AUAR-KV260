#!/bin/sh
# Explicit native AArch64 build. Only writes to a new output directory.
set -eu
if [ "$#" -ne 1 ]; then echo "usage: sh native_build.sh NEW_OUTPUT" >&2; exit 2; fi
case "$(uname -m)" in aarch64|arm64) ;; *) echo "AArch64 build environment required" >&2; exit 2;; esac
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
case "$1" in /*) out="$1";; *) out="$(pwd)/$1";; esac
mkdir "$out"
cc -Wall -Wextra -std=c11 -O2 -fPIC -shared -Wl,-z,relro,-z,now "$root/src/fpga/native/vsrv_mmio.c" -o "$out/libvsrv.so"
cc -Wall -Wextra -std=c11 -O2 -fPIC -shared -Wl,-z,relro,-z,now "$root/src/motion/mmio_src/vsrv_mmio.c" -o "$out/libvsrv_batch.so"
c++ -std=c++17 -O3 -fPIC -shared -pthread $(pkg-config --cflags opencv4) "$root/src/software/tools/native_pixels.cpp" -o "$out/libaura_pixels.so" $(pkg-config --libs opencv4)
python3 -B "$root/src/software/board/vision/native/build_yolox.py" --output "$out/libaura_yolox.so"
c++ -shared -Wl,-z,defs -pthread "$root/src/camera/native_operator/native_bridge.operator.aarch64.o" -o "$out/libaura_native_operator.so" -lvart-runner -lxir -ldl
# The object above retains the exact original translation unit. Set RECOMPILE_VART=1
# if the matching VART/XIR development headers and a C++17 compiler are installed.
if [ "${RECOMPILE_VART:-0}" = 1 ]; then
    c++ -std=c++17 -O2 -pthread -fPIC -shared -Wl,-z,defs "$root/src/camera/native_operator/native_bridge.cpp" -o "$out/libaura_native_operator_from_source.so" -lvart-runner -lxir -ldl
fi
# Ruckig was built with C++20. Keep the hardware-slew tests separate.
set --
for f in "$root"/src/motion/trajectory_src/ruckig/src/ruckig/*.cpp; do
    case "$f" in */cloud_client.cpp) continue ;; esac
    set -- "$@" "$f"
done
c++ -std=c++20 -O2 -fPIC -fvisibility=hidden -shared -Wl,-z,relro,-z,now -Wl,--exclude-libs,ALL -I"$root/src/motion/trajectory_src/ruckig/include" "$root/src/motion/trajectory_src/aura_trajectory.cpp" "$root/src/motion/trajectory_src/compat_runtime.cpp" "$@" -o "$out/libaura_trajectory.so"
cmake -S "$root/src/avatar/native_integration/host" -B "$out/yuki-build" -DCMAKE_BUILD_TYPE=Release
cmake --build "$out/yuki-build" --target aura_yuki --parallel 1
