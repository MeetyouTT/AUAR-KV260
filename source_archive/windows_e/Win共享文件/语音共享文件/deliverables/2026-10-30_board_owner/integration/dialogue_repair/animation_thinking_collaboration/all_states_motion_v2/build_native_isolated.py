"""Root-owner-only native build recipe. This file never connects to a device.

Run on the board ONLY when the coordinating owner grants its build window.
It writes a new directory here, verifies original build inputs, reuses the
unchanged core/renderer objects, and performs CPU-only native policy checks.
It neither installs the library nor opens any GTK/EGL/audio/model service.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native-root', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--resx', type=Path, required=True)
    parser.add_argument('--resource-root', type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != 'Linux':
        raise SystemExit('Device-local Linux build recipe; no SSH or automatic remote execution')
    baseline = json.loads((HERE/'NATIVE_BASELINE.json').read_text(encoding='utf-8'))
    root = args.native_root.resolve(strict=True)
    for relative, expected in baseline['base_pins'].items():
        if sha(root/relative) != expected:
            raise ValueError('Original native build input changed: '+relative)
    for relative, expected in baseline['header_pins'].items():
        if sha(root/relative) != expected:
            raise ValueError('Original native build header changed: '+relative)
    for path, name in ((args.model,'assets/yuki/model.runtime.json'),(args.resx,'assets/yuki/yuk_0.ems.resx.json')):
        if sha(path) != baseline['character_asset_pins'][name]:
            raise ValueError('Public character asset changed: '+name)
    source = HERE/'candidate/native'
    out = HERE/'native_build'
    # Never overwrite a previous build or any production directory.
    out.mkdir(exist_ok=False)
    core = root/'build_host/libyuki_core.a'
    objects = root/'build_host/CMakeFiles/aura_yuki.dir'
    deps = root.parent/'deps'
    common = ['nice','-n','15','/usr/bin/c++','-std=gnu++20','-O2','-DNDEBUG',
              '-I'+str(source),'-I'+str(root/'host'),'-I'+str(root/'candidate_core/include'),
              '-isystem',str(deps/'json'),'-isystem','/usr/include/libpng16']
    steps=[]
    def run(label, argv):
        started=time.monotonic()
        completed=subprocess.run(argv, capture_output=True, text=True, check=False)
        step=dict(label=label,argv=argv,returncode=completed.returncode,
                  elapsed_seconds=round(time.monotonic()-started,3),
                  stdout=completed.stdout[-12000:],stderr=completed.stderr[-12000:])
        steps.append(step)
        (out/'steps.json').write_text(json.dumps(steps,indent=2)+'\n',encoding='utf-8')
        if completed.returncode:
            raise RuntimeError('Isolated native step failed: '+label)
        return completed.stdout
    run('compile_candidate_host',common+['-fPIC','-Wall','-Wextra','-Wpedantic','-c',
        str(source/'yuki_host.cpp'),'-o',str(out/'yuki_host.cpp.o')])
    run('link_candidate_library',['nice','-n','15','/usr/bin/c++','-fPIC','-shared',
        '-Wl,-soname,libaura_yuki.so','-o',str(out/'libaura_yuki.so'),str(out/'yuki_host.cpp.o'),
        str(objects/'gles2_renderer.cpp.o'),str(objects/'diagnostic_api.cpp.o'),str(core),
        '/usr/lib/libGLESv2.so','/usr/lib/libpng16.so','/usr/lib/libz.so'])
    run('compile_cpu_only_policy_test',common+[str(HERE/'tests/native_all_states_motion.cpp'),str(core),
        '-o',str(out/'native_eye_gate')])
    native_test=run('run_cpu_only_policy_test',[str(out/'native_eye_gate'),
        str(args.model),str(args.resx),str(args.resource_root)])
    exports=run('exports',['nm','-D','--defined-only',str(out/'libaura_yuki.so')])
    dynamic=run('dependencies',['readelf','-d',str(out/'libaura_yuki.so')])
    if 'yuki_control_features' not in exports:
        raise ValueError('New native capability is absent')
    expected=set(baseline['needed_before'])
    actual={line.split('[')[1].split(']')[0] for line in dynamic.splitlines() if '(NEEDED)' in line}
    if actual != expected:
        raise ValueError('Native shared dependencies changed')
    # Validate the CPU test's machine-readable report; no physical FPS claim.
    check=json.loads(native_test.strip().splitlines()[-1])
    if check.get('status') != 'PASS' or check.get('gpu_or_audio_device_opened') is not False:
        raise ValueError('Native policy verification did not pass')
    receipt=dict(schema='aura.animation-thinking-native-build.v1',
        status='ISOLATED_COMPILED_CPU_POLICY_PASSED_NOT_INSTALLED',
        source_sha256=sha(source/'yuki_host.cpp'),header_sha256=sha(source/'yuki_host.h'),
        motion_header_sha256=sha(source/'gentle_motion.hpp'),continuous_motion_feature_bit=2,
        library_sha256=sha(out/'libaura_yuki.so'),library_bytes=(out/'libaura_yuki.so').stat().st_size,
        native_policy_test=check,shared_dependencies_identical=True,
        new_api='yuki_control_features',control_struct_layout_unchanged=True,
        production_installed=False,gtk_or_egl_opened=False,audio_device_opened=False,
        model_inference=False,physical_fps_measured=False,visual_preview_passed=False,
        steps=steps)
    (out/'native_build_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'],library_sha256=receipt['library_sha256'])))


if __name__ == '__main__':
    main()
