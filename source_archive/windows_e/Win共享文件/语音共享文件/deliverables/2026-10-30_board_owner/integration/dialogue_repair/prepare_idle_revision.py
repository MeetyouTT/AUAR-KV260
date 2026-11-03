"""Prepare the two reviewed idle-work edits against current v14, without deployment."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
OUT=HERE/'idle_cpu_integration'
BASE_STARTUP='39b102a4a505db491cf06b90e3a5232bfb656c79cb0a3c221551d76d414a9a0a'
BASE_MANIFEST='a2545970650f60b95cdc6e4f0a31c234f37adb5f0662c9f04ded791352f53353'

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--audio-sha256',required=True)
    args=parser.parse_args()
    spec_path=HERE.parent/'production_business_acceptance/spec.json'
    spec_raw=spec_path.read_bytes()
    spec=json.loads(spec_raw)
    assert spec['startup_sha256']==BASE_STARTUP and spec['component_pins']==378
    baseline=json.loads((HERE/'first_wait_integration/baseline_manifest.json').read_text(encoding='utf-8'))['component_sha256']
    sources={}
    for folder,relative,expected in (
        ('presentation_idle_candidate','tools/board_avatar_gtk.py','7d95b5f682f7abf4a69509d5843c3345dcc31f8dbefeb0e9f3af27b19aa3542d'),
        ('playback_idle_candidate','tools/gstreamer_audio_worker.py',args.audio_sha256),
    ):
        before=HERE/folder/'before'/relative
        after=HERE/folder/'after'/relative
        before_sha=hashlib.sha256(before.read_bytes()).hexdigest()
        raw=after.read_bytes()
        assert before_sha==baseline[relative]
        assert hashlib.sha256(raw).hexdigest()==expected
        ast.parse(raw,feature_version=(3,9))
        sources[relative]=dict(source=after.relative_to(PROJECT).as_posix(),sha256=expected,before_sha256=before_sha)
    v14=json.loads((HERE/'first_wait_integration/revision.json').read_text(encoding='utf-8'))
    revision=dict(stage='automatic-listening-v15-idle-cpu',before_startup_sha256=BASE_STARTUP,
        before_manifest_sha256=BASE_MANIFEST,sources=sources,business_options=v14['business_options'],
        gui_options=v14['gui_options'],wake_word_required=False,conversation_mode='half_duplex',
        source_only=True,private_data_replayed=False,models_or_thresholds_changed=False,
        queue_frames=8,target_fps=16,reason='Avoid duplicate idle audio state IPC and conflicting subtitle writers.')
    OUT.mkdir(exist_ok=True)
    backup=OUT/'before_spec.json'
    if backup.exists():assert backup.read_bytes()==spec_raw
    else:backup.write_bytes(spec_raw)
    target=OUT/'revision.json'
    target.write_text(json.dumps(revision,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(revision=str(target),sources=sources)))
