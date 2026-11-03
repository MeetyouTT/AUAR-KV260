"""Local source/evidence-only policy construction; no board/service access."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent


def main():
    baseline=json.loads((ROOT/'actual_ui_baseline.json').read_text(encoding='utf-8'))
    assembly=ROOT.parent/'resume_yuki_run_assembly'
    policy=json.loads((assembly/'assembly_policy.v2.final.json').read_text(encoding='utf-8'))
    launch=json.loads((ROOT/'actual_candidate_launch.json').read_text(encoding='utf-8'))
    def owner(row):return dict(pid=row['pid'],birth=row['birth'],argv=row['argv'],
        cmdline_sha256=hashlib.sha256(('\0'.join(row['argv'])+'\0').encode()).hexdigest())
    value=dict(schema_version=1,target='/home/root/aura-board-owner-candidate-20261030/yuki-gui-capacity-20261030-r2',
        boot_id=policy['camera']['boot'],lock='/run/aura-avatar-ui.lock',
        startup=policy['baseline']['startup'],startup_sha256=policy['baseline']['startup_sha256'],
        runtime=policy['baseline']['runtime'],pins=policy['baseline']['pins'],
        launcher=baseline['launcher']['path'],launcher_sha256=baseline['launcher']['sha256'],
        old_supervisor=owner(baseline),old_child=owner(baseline['children'][0]),
        safety_probe='/home/root/aura-board-owner-candidate-20261030/perf-fa0bc04a6f8c15a9/probe.py',
        safety_probe_sha256='b53803cab734bb69cd8a62698c92d630ed98d9d0b2cee7ecc9232bcb4a4323a3',
        launch_canonical_sha256=hashlib.sha256(json.dumps(launch['launch'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        inspection_sha256=launch['inspection'])
    raw=json.dumps(value,indent=2).encode();(ROOT/'ui_trial_policy.json').write_bytes(raw)
    print(json.dumps(dict(policy='ui_trial_policy.json',sha256=hashlib.sha256(raw).hexdigest(),pins=len(value['pins']))))
if __name__=='__main__':main()
