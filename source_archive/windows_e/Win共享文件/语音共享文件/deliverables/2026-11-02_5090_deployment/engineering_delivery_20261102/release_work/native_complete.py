from common import *
f=ROOT/'build/scripts/native_build.sh'
s=f.read_text().replace('cc -Wall -Wextra -std=c11 -O2 -fPIC -shared', 'cc -Wall -Wextra -std=c11 -O2 -fPIC -shared -Wl,-z,relro,-z,now').replace('c++ -std=c++17 -O3 -fPIC -shared -pthread "$root/src/software/tools/native_pixels.cpp" -o "$out/libaura_pixels.so"','c++ -std=c++17 -O3 -fPIC -shared -pthread $(pkg-config --cflags opencv4) "$root/src/software/tools/native_pixels.cpp" -o "$out/libaura_pixels.so" $(pkg-config --libs opencv4)')
marker='cmake -S "$root/src/avatar'
s=s.replace(marker,'''# The object above retains the exact original translation unit. Set RECOMPILE_VART=1
# if the matching VART/XIR development headers and a C++17 compiler are installed.
if [ "\${RECOMPILE_VART:-0}" = 1 ]; then
    c++ -std=c++17 -O2 -pthread -fPIC -shared -Wl,-z,defs "$root/src/camera/native_operator/native_bridge.cpp" -o "$out/libaura_native_operator_from_source.so" -lvart-runner -lxir -ldl
fi
# Ruckig was built with C++20. Keep the hardware-slew tests separate.
set --
for f in "$root"/src/motion/trajectory_src/ruckig/src/ruckig/*.cpp; do
    case "$f" in */cloud_client.cpp) continue ;; esac
    set -- "$@" "$f"
done
c++ -std=c++20 -O2 -fPIC -fvisibility=hidden -shared -Wl,-z,relro,-z,now -Wl,--exclude-libs,ALL -I"$root/src/motion/trajectory_src/ruckig/include" "$root/src/motion/trajectory_src/aura_trajectory.cpp" "$root/src/motion/trajectory_src/compat_runtime.cpp" "$@" -o "$out/libaura_trajectory.so"
cmake -S "$root/src/avatar'''.replace('\\$','$'))
f.write_bytes(s.encode())
# Smoke-test the original model-owner tests without a resident GPU or network calls.
host=ROOT/'src/windows/deliverables/2026-10-30_board_owner/integration/production_model_host'
r=subprocess.run([sys.executable,'-B','-m','unittest','test_production_runtime','-v'],cwd=host,capture_output=True)
(QA/'windows_host_unit.txt').write_bytes(r.stdout+r.stderr)
print(r.returncode,(r.stdout+r.stderr).decode(errors='replace')[-490:])
