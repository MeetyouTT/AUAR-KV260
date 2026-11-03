"""Prepare a two-head-channel native candidate against current v22 pins."""
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
ANIM=HERE.parent
REPAIR=ANIM.parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def once(value,old,new):
    if value.count(old)!=1:raise ValueError(old[:70])
    return value.replace(old,new)


def main():
    mapping_path=REPAIR/'release_v22_camera_rebind_candidate/camera_rebind_evidence/source_mapping.json'
    mapping=json.loads(mapping_path.read_text(encoding='utf-8'))
    if mapping['startup_sha256']!='48cb1a3a1fc62eae32c93a5be02df0bd60926cd064884a06990dd24b62762885':
        raise ValueError('Requires current baseline review')
    pins={name:mapping['component_pins'][name] for name in ('tools/native_yuki.py',
        'tools/formal_native_yuki.py','tools/formal_yuki.py','config/yuki_pair.formal.json','tools/libaura_yuki.so')}
    for name,digest in pins.items():
        source=ANIM/'paired_overlay/aura'/name
        if sha(source)!=digest:raise ValueError('Current pair differs: '+name)
        target=HERE/'before/aura'/name;target.parent.mkdir(parents=True,exist_ok=True)
        if source.suffix!='.so':shutil.copyfile(source,target)
    native=HERE/'candidate/native';native.mkdir(parents=True,exist_ok=False)
    for name in ('yuki_host.cpp','yuki_host.h'):
        shutil.copyfile(ANIM/'all_states_motion_v2/candidate/native'/name,native/name)
    host=(native/'yuki_host.cpp').read_text(encoding='utf-8')
    host=once(host,'std::array<ParamId,6> motion{};','std::array<ParamId,2> motion{};')
    host=once(host,'std::array<float,6> motion_offsets{};','std::array<float,2> motion_offsets{};')
    host=once(host,'{"head_LR","head_UD","head_slant","body_LR","body_UD","body_slant"}',
        '{"head_LR","head_slant"}')
    host=once(host,'h.gentle_motion.step(mood,live?double(h.control.gain*h.control.level):0.)',
        'h.gentle_motion.step(mood)')
    (native/'yuki_host.cpp').write_text(host,encoding='utf-8')
    tests=HERE/'tests';tests.mkdir()
    shutil.copyfile(ANIM/'tests/native_eye_gate.cpp',tests/'native_eye_gate.cpp')
    shutil.copyfile(ANIM/'all_states_motion_v2/NATIVE_BASELINE.json',HERE/'NATIVE_BASELINE.json')
    builder=(ANIM/'all_states_motion_v2/build_native_isolated.py').read_text(encoding='utf-8')
    builder=once(builder,'    parser = argparse.ArgumentParser()\n',
        "    parser = argparse.ArgumentParser()\n    parser.add_argument('--execute-root-only',action='store_true',required=True)\n")
    (HERE/'build_native_isolated.py').write_text(builder,encoding='utf-8')
    result=dict(schema='aura.minimal-motion-baseline.v22',startup_sha256=mapping['startup_sha256'],
        source_manifest_sha256=mapping['source_manifest_sha256'],boot_id=mapping['boot_id'],
        source_mapping_sha256=sha(mapping_path),pair_pins=pins,base_native_source_sha256=sha(ANIM/'candidate/native/yuki_host.cpp'),
        target_fps=16,asr_threads=2,gtcrn_threads=1,user_listening_enabled=False,user_microphone_open=False,
        gtk_pause_keepalive_seconds=5,production_modified=False,device_actions=False)
    (HERE/'BASELINE_V22.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
