"""Derive a fresh read-only selected-binding precheck from the original reviewed flow."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1]
original = OUT / 'parallel_platform/gui_startup_review/collect_gui_candidate_precheck24.py'
source = original.read_text(encoding='utf-8')

def change(before, after, expected=1):
    global source
    assert source.count(before) == expected, (before, source.count(before))
    source = source.replace(before, after)

change('all original 23 pins plus actual run config', 'all existing 24 pins plus the restored camera run config')
change("STARTUP_SHA = '07c5aa3b1c8da060e5a7d8520021bce7f167a8cf303b48a0a24f8e2a8b63035d'", "STARTUP_SHA = '0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f'")
change("SELECTED_SHA = 'a7402eb0f3e8d5391a95136d65759569be86eceeb75d830146a4b1d14cc81667'", "SELECTED_SHA = '4d8f0c2bccea1c7a56761fbcb204f40ba3b3c2fc9efad76af778aff535d378ac'")
change("UI_SHA = 'a695d620ddad3216de2d0447ec91d0e983a67343c2282179adece8014fccc063'", "UI_SHA = 'fc21e6f2ef831442b08966957fa7aeb744a9b74124ee8778edc40397285626cd'")
change('1333', '79866', expected=6)
change('2359', '2265436', expected=3)
change("'ActiveState':'failed','SubState':'failed'", "'ActiveState':'inactive','SubState':'dead'")
change("len(selected['source_sha256']) == 23", "len(selected['source_sha256']) == 24")
change("len(candidate['source_sha256']) == 24", "len(candidate['source_sha256']) == 25")
change("'candidate_source_files_verified':24", "'candidate_source_files_verified':25")
change("'candidate_preserves_all_23_source_pins':True", "'candidate_preserves_all_24_source_pins':True")
change('aura-selected-gui-binding-candidate-precheck-24-1', 'aura-selected-restored-gui-binding-candidate-precheck-25-1')
change('RAM_24_PIN_CANDIDATE_ORIGINAL_VERIFY_PASS_PRODUCTION_STILL_STALE', 'RAM_25_PIN_CANDIDATE_ORIGINAL_VERIFY_PASS_PRODUCTION_STILL_STALE')
anchor = 'units(); owner()\nassert digest(BUSINESS'
assert source.count(anchor) == 1
platform = """def platform():
    assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\\0') == b'aura-visual-servo-b4096-wide-v1.bit.bin'
    assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip() == 'operating'
    assert Path('/etc/vart.conf').read_bytes() == b'firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-wide-v1/aura-visual-servo-b4096-wide-v1.xclbin\\n'
    assert digest('/sys/firmware/fdt') == 'd68bc147f22f5ab23bc60f0c2762af4bcd7b64340953e9c948e28ffa6b80f7ca'
    overlays = Path('/sys/kernel/config/device-tree/overlays')
    assert sorted(p.name for p in overlays.iterdir()) == ['aura-visual-servo-b4096-wide-v1_image_1']
    assert (overlays/'aura-visual-servo-b4096-wide-v1_image_1/status').read_text().strip() == 'applied'
    assert Path('/sys/bus/platform/drivers/zocl-drm/axi:zyxclmm_drm').resolve(strict=True) == Path('/sys/devices/platform/axi/axi:zyxclmm_drm')
    assert Path('/sys/class/drm/renderD128/device').resolve(strict=True) == Path('/sys/devices/platform/axi/axi:zyxclmm_drm')

platform()
"""
source = source.replace(anchor, platform + anchor)
change("run_config=json.loads(raw(RUN)); run_sha=digest(RUN)", "run_config=json.loads(raw(RUN)); run_sha=digest(RUN)\nassert run_sha == 'c8df0795664d21d52eab3a4f1cf55e0d1a721577d547c512e83ee1931d80871d'")
change("units(); owner()\nraw_candidate=", "units(); owner(); platform()\nraw_candidate=")
ast.parse(source)
target = HERE/'collect_gui_binding_precheck25.py'
with target.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(source)
print(json.dumps({'file': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}))
