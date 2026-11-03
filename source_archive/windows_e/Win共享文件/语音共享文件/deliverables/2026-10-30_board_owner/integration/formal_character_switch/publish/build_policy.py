"""Local public-evidence policy construction only; no device calls."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
INTEGRATION=HERE.parents[1]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def main():
    baseline=load(HERE.parent/'actual_baseline.json')
    prior=load(INTEGRATION/'resume_ui_trial_round2/policy.json')
    resources=load(INTEGRATION/'resume_yuki_run_assembly/assembly_policy.v2.final.json')
    folder=INTEGRATION/'formal_switch';manifest=load(folder/'manifest.json')
    zsha=digest(folder/'formal_yuki.overlay.zip');msha=digest(folder/'manifest.json')
    assert zsha=='f94fca2c94288acb1ffb5306e3d2dcbbb20caa12b8ca31700670bccf0b612cdc'
    assert msha=='bd284ab673df0381561563b2dc32f39e434b468d456f662f2df0f2f00f0e75dc'
    assert baseline['original_pins']==286 and not baseline['original_component_changes'] and not baseline['original_alias_changes']
    assert baseline['launcher_sha256']==prior['launcher_sha256']==manifest['original_launcher_must_remain_sha256']
    prefix='/home/root/aura-character-xuefei-20261030/';fingerprint=zsha[:16]
    value={'schema':1,'boot_id':baseline['boot_id'],'camera':baseline['camera'],
        'target':prefix+fingerprint,'control':prefix+'control-'+fingerprint,
        'overlay_sha256':zsha,'overlay_manifest_sha256':msha,
        'overlay_manifest':prefix+'incoming-'+fingerprint+'/manifest.json',
        'original':{'runtime':prior['runtime'],'startup':prior['startup'],'startup_sha256':prior['startup_sha256'],
            'launcher':prior['launcher'],'launcher_sha256':prior['launcher_sha256'],'pins':prior['pins'],
            'aliases':prior['source_aliases'],'supervisor':baseline['supervisor'],'child':baseline['child'],
            'properties':baseline['properties'],'unit_sources':baseline['unit_source_sha256']},
        'public_copies':[v for v in resources['public_copies'] if v['target'].startswith('runtime/')],
        'public_probe':prior['safety_probe'],'public_probe_sha256':prior['safety_probe_sha256'],
        'x11_source':'/home/root/aura-board-owner-candidate-20261030/ui-round2-4750fc97e43a75bd/x11_close.py',
        'x11_sha256':digest(INTEGRATION/'resume_ui_trial_round2/x11_close.py'),
        'readiness_seconds':180,'business_mode':'UNCHANGED_LEGACY','database_copy':False,'cleanup_enabled':False,
        'baseline_evidence_sha256':digest(HERE.parent/'actual_baseline.json')}
    assert len(value['public_copies'])==4
    raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    (HERE/'policy.json').write_bytes(raw)
    print(json.dumps({'policy_sha256':hashlib.sha256(raw).hexdigest(),'target':value['target'],
                      'control':value['control'],'public_files':4,'source_pins':286}))


if __name__=='__main__':main()
