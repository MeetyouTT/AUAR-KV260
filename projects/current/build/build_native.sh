#!/bin/sh
# Build the actual native sources. Use native ARM64 or configure a matching GNU cross toolchain/sysroot.
set -eu
[ "$#" = 1 ] || { echo 'usage: sh build/build_native.sh NEW_EXTERNAL_DIRECTORY' >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
out=$(python3 -c 'from pathlib import Path;import sys;print(Path(sys.argv[1]).resolve())' "$1")
case "$out/" in "$root/"*) echo 'choose a directory outside the package' >&2; exit 2;; esac
cc_bin=${CC:-cc}
cxx_bin=${CXX:-c++}
case "$("$cc_bin" -dumpmachine)" in aarch64*|arm64*) ;; *) echo 'Select the target AArch64 CC/CXX and pkg-config sysroot.' >&2; exit 2;; esac
case "$("$cxx_bin" -dumpmachine)" in aarch64*|arm64*) ;; *) echo 'Target C++ compiler must be AArch64.' >&2; exit 2;; esac
for tool in cmake pkg-config python3; do command -v "$tool" >/dev/null; done
pkg-config --exists opencv4 glesv2 libpng gstreamer-app-1.0 gstreamer-video-1.0 || { echo 'Missing target OpenCV4/GLES2/libpng development files' >&2; exit 2; }
mkdir "$out"
"$cc_bin" -std=c11 -O2 -fPIC -shared -Wl,-z,relro,-z,now "$root/src/native/vsrv/vsrv_mmio.c" -o "$out/libvsrv.so"
"$cc_bin" -std=c11 -O2 -fPIC -shared -Wl,-z,relro,-z,now "$root/src/motion/mmio_src/vsrv_mmio.c" -o "$out/libvsrv_batch.so"
"$cxx_bin" -std=c++17 -O3 -fPIC -shared -pthread $(pkg-config --cflags opencv4 gstreamer-app-1.0 gstreamer-video-1.0) "$root/src/tools/native_pixels.cpp" -o "$out/libaura_pixels.so" $(pkg-config --libs opencv4 gstreamer-app-1.0 gstreamer-video-1.0)
"$cxx_bin" -std=c++17 -O2 -fPIC -shared -Wl,-z,defs $(pkg-config --cflags opencv4) "$root/src/board/vision/native/yolox_bridge.cpp" -o "$out/libaura_yolox.so" -lvitis_ai_library-yolovx -lvitis_ai_library-dpu_task -lopencv_core -lglog
for item in native_operator native_v2; do
    case "$item" in native_operator) lib=libaura_native_operator.so;; native_v2) lib=libaura_native_v2_candidate.so;; esac
    "$cxx_bin" -std=c++17 -O2 -pthread -fPIC -shared -Wl,-z,defs "$root/src/camera/$item/native_bridge.cpp" -o "$out/$lib" -lvart-runner -lxir -ldl
done
set --
for cpp in "$root"/src/motion/trajectory_src/ruckig/src/ruckig/*.cpp; do
    case "$cpp" in */cloud_client.cpp) continue;; esac
    set -- "$@" "$cpp"
done
"$cxx_bin" -std=c++20 -O2 -fPIC -fvisibility=hidden -shared -Wl,-z,relro,-z,now -Wl,--exclude-libs,ALL -I"$root/src/motion/trajectory_src/ruckig/include" "$root/src/motion/trajectory_src/aura_trajectory.cpp" "$root/src/motion/trajectory_src/compat_runtime.cpp" "$@" -o "$out/libaura_trajectory.so"
set --
if [ -n "${CMAKE_TOOLCHAIN_FILE:-}" ]; then set -- "-DCMAKE_TOOLCHAIN_FILE=$CMAKE_TOOLCHAIN_FILE"; fi
cmake -S "$root/src/native/avatar/native_integration/host" -B "$out/yuki-build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER="$cxx_bin" "$@"
cmake --build "$out/yuki-build" --target aura_yuki --parallel 1
cp "$out/yuki-build/libaura_yuki.so" "$out/libaura_yuki.so"
python3 - "$out" <<'PY'
import hashlib,json,sys
from pathlib import Path
out=Path(sys.argv[1]);libs=sorted(out.glob('*.so'))
assert len(libs)==8
for p in libs:
 b=p.read_bytes()
 if len(b)<20 or b[:4]!=b'\x7fELF' or b[4]!=2 or b[5]!=1 or int.from_bytes(b[18:20],'little')!=183:raise ValueError('not AArch64 ELF: '+p.name)
(out/'native_result.json').write_text(json.dumps({'status':'PASS','architecture':'AArch64','hardware_executed':False,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in libs}},indent=2))
PY

