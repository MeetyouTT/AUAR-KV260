"""Post-measurement audit/archive and narrowly filtered camera boundary metadata."""
from pathlib import Path
import hashlib,json,os,runpy,subprocess,time,urllib.request,zipfile

phase=Path('/home/root/aura-yuki-validation-20261030/native_integration');ab=phase/'paired_ab'
suite=json.loads((ab/'runs/formal-resume-v2/suite-result.json').read_text())
assert suite['status']=='COMPLETE' and len(suite['cases'])==12
remaining=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit() or int(p.name)==os.getpid():continue
    try:argv=[x.decode() for x in (p/'cmdline').read_bytes().split(b'\0') if x]
    except (OSError,UnicodeError):continue
    if any(x.startswith(str(phase)+'/') and Path(x).name in {'run_suite.py','paired_renderer_harness.py','old_renderer_harness.py','validate_gtk_clock.py','validate_gtk_lifecycle.py','validate_native.py'} for x in argv):
        remaining.append(int(p.name))
assert not remaining,remaining
runpy.run_path(str(phase/'final_board_preservation.py'),run_name='__main__')
preservation=json.loads((phase/'results/final-preservation.json').read_text());assert preservation['status']=='PASS'
basis=json.loads((phase/'board_source/manifest.json').read_text())
camera_pid=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
assert camera_pid==basis['camera_pid']
metadata={'camera_pid':camera_pid,'feature_backend_kinds':{},'configuration_paths':{},'observed_after_all_measurements':True}
try:
    with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=2) as response:health=json.load(response)
    def walk(value,path='',depth=0):
        if not isinstance(value,dict) or depth>6:return
        for key,item in value.items():
            if key in {'identity_id','face_id','fingerprint','template','embedding','people','tracks','detections','name','label'}:continue
            name=path+'.'+key if path else key
            if key=='feature_backend' and isinstance(item,dict) and isinstance(item.get('kind'),str):metadata['feature_backend_kinds'][name+'.kind']=item['kind']
            elif key in {'camera_config_path','config_path','configuration_path'} and isinstance(item,str) and item.startswith('/home/root/') and item.endswith('.json'):metadata['configuration_paths'][name]=item
            elif isinstance(item,dict):walk(item,name,depth+1)
    walk(health)
except Exception as error:metadata['metadata_status']='UNKNOWN_'+type(error).__name__
def process_ticks():
    out={}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            raw=(p/'stat').read_text();v=raw.rsplit(')',1)[1].split()
            out[int(p.name)]=dict(comm=raw.split('(',1)[1].rsplit(')',1)[0],ppid=int(v[1]),ticks=int(v[11])+int(v[12]))
        except (OSError,ValueError,IndexError):pass
    return time.monotonic(),out
t0,a=process_ticks();time.sleep(1);t1,b=process_ticks();hz=os.sysconf('SC_CLK_TCK')
post_cpu=sorted([dict(pid=pid,ppid=v['ppid'],comm=v['comm'],cpu_seconds_per_second=(v['ticks']-a[pid]['ticks'])/hz/(t1-t0)) for pid,v in b.items() if pid in a],key=lambda x:x['cpu_seconds_per_second'],reverse=True)[:15]
archive=ab/'formal-resume-v2-evidence.zip';hashes={}
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
    roots=[ab/'runs/formal-resume-v2',ab/'runs/control-pilot-resume-v2']
    files=[p for root in roots for p in root.rglob('*') if p.is_file() and p.suffix in {'.json','.jsonl','.log'}]
    files += [ab/name for name in ['suite-formal-resume-v2.json','suite-control-pilot-resume-v2.json','resource-window-grant-resume.json',
        'fresh-baseline.json','isolated-server-proof.json','control-pilot-resume-v2-acceptance.json','control-pilot-resume-v2-acceptance-check-v1.json',
        'paired_renderer_harness.py','old_renderer_harness.py','old_harness_support.py','telemetry.py','run_suite.py','harness-delivery-nojpeg-v2.json']]
    for p in sorted(files):
        assert p.resolve().is_relative_to(ab.resolve())
        name=p.relative_to(ab).as_posix();data=p.read_bytes();hashes[name]=hashlib.sha256(data).hexdigest();output.writestr(name,data)
    output.writestr('evidence-sha256.json',json.dumps(hashes,indent=2))
result=dict(status='PASS',boot_id=suite['boot_id'],remaining_owned_board_processes=remaining,
    camera_boundary_metadata=metadata,production_preservation=preservation,
    post_measurement_cpu_top=post_cpu,post_measurement_cpu_scope='one-second read-only process metadata after all timed runs; never substituted for formal measurements',
    evidence_archive=str(archive),evidence_files=len(hashes),evidence_bytes=archive.stat().st_size,
    evidence_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),production_modified=False)
(ab/'formal-resume-v2-final-board-check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
