from pathlib import Path
import json, hashlib, shutil, subprocess, sys, datetime

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
DEP=PROJECT/'deliverables/2026-11-02_5090_deployment'
EXPORT=Path('E:/AUAR_工程交付_20261102/aura')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    expected=load(DEP/'visual_artifact_fix_20261102/release/fresh_expected_after.json')
    pins=expected['component_sha256']
    relevant={k:v for k,v in pins.items() if any(x in k for x in ('yuki','egl_window','character','realtime_stage','audio_envelope'))}
    matches={}
    for rel,h in relevant.items():
        p=EXPORT/'src/software'/rel
        if p.is_file(): matches[rel]={'path':str(p),'sha256':sha(p),'expected':h,'match':sha(p)==h}
    native=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/animation_thinking_collaboration/all_states_motion_v3_minimal/candidate/native'
    sources={str(p.relative_to(native)):{'path':str(p),'sha256':sha(p)} for p in native.iterdir() if p.is_file()}
    for rel,row in matches.items():
        if row['match'] and (rel.endswith('.py') or rel.endswith('.json')):
            dest=HERE/'baseline/runtime'/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(row['path'],dest)
    for rel,row in sources.items():
        dest=HERE/'baseline/native'/rel
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(row['path'],dest)
    receipt=dict(schema='aura-animation-offline-baseline-1',host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        recorded_startup_sha256=expected['startup_sha256'],recorded_startup_path=expected['startup_path'],
        historical_receipt_only=True,actual_device_read=False,engineering_export_modified=False,
        component_pins=relevant,local_matches=matches,native_sources=sources)
    save(HERE/'baseline/OFFLINE_SOURCE_BASELINE.json',receipt)
    print(json.dumps({'startup':expected['startup_sha256'],'relevant':relevant,'local_matches':{k:v['match'] for k,v in matches.items()},'native_sources':sources},ensure_ascii=False))
    remote='''import json,platform,shutil,os\nprint(json.dumps(dict(machine=platform.machine(),python=platform.python_version(),tools={k:shutil.which(k) for k in ['c++','cmake','ffmpeg','Xvfb']},home=os.path.expanduser('~'))))\n'''
    r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=7','aura-ubuntu','python3 -'],input=remote.encode(),capture_output=True,timeout=20)
    save(HERE/'baseline/UBUNTU_BUILD_HOST.json',dict(returncode=r.returncode,stdout=r.stdout.decode(errors='replace'),stderr=r.stderr.decode(errors='replace')))
    print(r.stdout.decode(errors='replace'),r.stderr.decode(errors='replace'))

if __name__=='__main__':main()
