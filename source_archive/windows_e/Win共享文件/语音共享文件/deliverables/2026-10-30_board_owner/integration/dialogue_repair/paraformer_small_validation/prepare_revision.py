"""Prepare the reviewed small-ASR configuration and single selector source for normal-closed publication."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent
PROJECT=HERE.parents[4]
BASE_STARTUP='67d03ca40d709d22d761706bfca51a55e352adf86763ced7fb5eb5a688123a55'
BASE_MANIFEST='8312169b6747d6f0e1c2c8a73c20ecee6cd7b949083f977871412a96390c2e73'
SOURCE_BEFORE='c77e9ba24a4f0401ff2927d8ece187d5997b16308a7ec71c60c01e6be06b13f4'
STABLE_DIRECTORY='/home/root/aura-board-asr-models/paraformer-small-63ddc3cd0f2810b6'

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-sha256',required=True)
    args=parser.parse_args()
    spec_path=REPAIR.parent/'production_business_acceptance/spec.json'
    spec_raw=spec_path.read_bytes();spec=json.loads(spec_raw)
    assert spec['startup_sha256']==BASE_STARTUP and spec['component_pins']==378
    candidate=REPAIR/'paraformer_small_integration_candidate'
    assert (candidate/'HANDOFF.json').is_file()
    rel='tools/production_board_business_gui.py'
    before=candidate/'before'/rel;after=candidate/'after'/rel
    assert hashlib.sha256(before.read_bytes()).hexdigest()==SOURCE_BEFORE
    raw=after.read_bytes();assert hashlib.sha256(raw).hexdigest()==args.source_sha256
    ast.parse(raw,feature_version=(3,9))
    stable=json.loads((HERE/'STABLE_RESOURCES.json').read_text(encoding='utf-8'))
    assert stable['directory']==STABLE_DIRECTORY and stable['status']=='STABLE_ASR_RESOURCES_PREPARED_NOT_ACTIVATED'
    previous=json.loads((REPAIR/'idle_cpu_integration/revision.json').read_text(encoding='utf-8'))
    options=dict(previous['business_options'],asr_variant='paraformer_small',asr_directory=STABLE_DIRECTORY)
    assert options['asr_threads']==3
    revision=dict(stage='automatic-listening-v16-small-asr',before_startup_sha256=BASE_STARTUP,
        before_manifest_sha256=BASE_MANIFEST,sources={rel:dict(source=after.relative_to(PROJECT).as_posix(),
            sha256=args.source_sha256,before_sha256=SOURCE_BEFORE)},business_options=options,
        gui_options=previous['gui_options'],wake_word_required=False,conversation_mode='half_duplex',
        private_data_replayed=False,asr_model_changed=True,asr_interface_changed=False,
        queue_frames=8,target_fps=16,preserve_explicit_manual_pause=True,
        reason='Use the publicly screened Paraformer Small INT8 through the unchanged bounded board ASR adapter.',
        rollback=dict(asr_variant='baseline',asr_directory='/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/models/paraformer',asr_threads=3),
        user_homophone_tolerance='accepted',full_physical_dialogue_acceptance=False)
    for name,value in (('before_spec.json',spec_raw),('revision.json',(json.dumps(revision,indent=2)+'\n').encode())):
        target=HERE/name
        if target.exists():assert target.read_bytes()==value
        else:target.write_bytes(value)
    print(json.dumps(dict(revision=str(HERE/'revision.json'),source_sha256=args.source_sha256,asr_variant='paraformer_small',preserve_user_pause=True)))
