"""Root-owned public-character preview: stage, bounded run, exact evidence fetch."""
import argparse, base64, hashlib, json, sys, time, zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[4]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

ZIP_SHA='c125dd9ae7fe3e7a52ddeda0d90256ff96f4ab5aafa908358f343a252908430f'
STAGE='/home/root/aura-animation-preview-20261031/'+ZIP_SHA[:16]
RUNTIME='/home/root/aura-board-business-20261030/production-5259eab11e42af13/runtime/aura'
STARTUP_SHA='bf6cdd70768ea5fac4e5be874a387f444c0834d67db5e7a2a744671d9019d63c'
BOOT='8100a7fd-0c6a-46c4-82b8-f874988a1521'

COMMON=r'''
import base64,hashlib,io,json,os,subprocess,time,zipfile
from pathlib import Path
stage=Path(STAGE)
assert stage.parent==Path('/home/root/aura-animation-preview-20261031') and stage.resolve()==stage
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
def sha(raw):return hashlib.sha256(raw).hexdigest()
def unit():
    s=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','Job'],text=True)
    return dict(line.split('=',1) for line in s.splitlines() if '=' in line)
def camera():
    raw=Path('/proc/260102/stat').read_text(); fields=raw[raw.rfind(')')+2:].split()
    assert fields[19]=='784437'
'''

def remote(source,**values):
    header=dict(STAGE=STAGE,RUNTIME=RUNTIME,BOOT=BOOT,STARTUP_SHA=STARTUP_SHA,**values)
    return json.loads(ssh('python3 -B -','\n'.join(k+'='+repr(v) for k,v in header.items())+'\n'+COMMON+source,timeout=105))

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','run','fetch']);a=p.parse_args()
    if a.action=='stage':
        raw=(HERE/'preview_v2/public_preview_source_v2.zip').read_bytes()
        assert hashlib.sha256(raw).hexdigest()==ZIP_SHA
        result=remote(r'''
raw=base64.b64decode(PAYLOAD,validate=True);assert sha(raw)==ZIP_SHA
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    names=z.namelist();assert len(names)==len(set(names)) and 5<len(names)<16
    assert all(not Path(n).is_absolute() and '..' not in Path(n).parts and not n.endswith('/') for n in names)
    stage.mkdir(mode=0o700,parents=True,exist_ok=True)
    for name in names:
        path=stage/name;data=z.read(name)
        assert path.resolve()==path and path.is_relative_to(stage)
        path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        if path.exists():assert path.read_bytes()==data
        else:
            with path.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
camera()
r=subprocess.run(['/usr/bin/python3','-B',str(stage/'preview_public_states.py'),'--runtime',RUNTIME,'--validate-only'],capture_output=True,text=True,timeout=20)
assert r.returncode==0,(r.returncode,r.stderr[-2000:])
result=json.loads(r.stdout);result.update(stage=STAGE,zip_sha256=ZIP_SHA)
print(json.dumps(result))
''',PAYLOAD=base64.b64encode(raw).decode('ascii'),ZIP_SHA=ZIP_SHA)
    elif a.action=='run':
        integration=HERE.parent.parent
        env=json.loads((integration/'formal_character_switch/actual_baseline.json').read_text(encoding='utf-8'))['display_environment']
        assert set(env)<= {'DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','WAYLAND_DISPLAY','GDK_BACKEND'}
        result=remote(r'''
camera();before=unit();assert before['MainPID']=='0' and before['ActiveState']=='inactive' and not before.get('Job')
assert sha((Path(RUNTIME).parents[1]/'startup/config.json').read_bytes())==STARTUP_SHA
j=json.loads(Path('/home/root/aura-board-business-20261030/control-production-v1/state.json').read_text())
assert j['phase']=='NORMAL_CLOSED' and not j['guard_removed']
assert sha(Path(j['guard']).read_bytes())==j['guard_sha256']
assert not (stage/'preview_evidence').exists()
env=os.environ.copy();env.update(ENV);env.update(GDK_SCALE='1',GDK_DPI_SCALE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
start=time.monotonic()
proc=subprocess.Popen(['/usr/bin/timeout','--signal=TERM','--kill-after=5','80','/usr/bin/python3','-B',str(stage/'preview_public_states.py'),'--runtime',RUNTIME,'--evidence',str(stage/'preview_evidence'),'--owner-unit','aura-avatar-ui.service','--capture-character'],cwd=stage,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
try:out,err=proc.communicate(timeout=88)
except subprocess.TimeoutExpired:
    import signal
    os.killpg(proc.pid,signal.SIGTERM)
    try:out,err=proc.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid,signal.SIGKILL);out,err=proc.communicate(timeout=3)
group_members=[]
for stat in Path('/proc').glob('[0-9]*/stat'):
    try:
        raw=stat.read_text();fields=raw[raw.rfind(')')+2:].split()
        if int(fields[2])==proc.pid:group_members.append(int(stat.parent.name))
    except (FileNotFoundError,ProcessLookupError):pass
after=unit();camera()
result=dict(preview_process_group=proc.pid,remaining_group_members=group_members,preview_group_empty=not group_members,exit_code=proc.returncode,elapsed_seconds=time.monotonic()-start,preview_process_exited=proc.poll() is not None,production_stayed_stopped=after==before,stdout=out[-14000:],stderr=err[-4000:],stage=STAGE)
print(json.dumps(result))
''',ENV=env)
    else:
        result=remote(r'''
paths=['preview_result.json','numeric_frames.json','thinking.png','buffer_ready.png','answer.png','paused.png','cancelled.png','idle_return.png']
files={}
for name in paths:
    p=stage/'preview_evidence'/name
    if p.exists():
        assert p.resolve()==p
        raw=p.read_bytes();assert len(raw)<3000000
        files[name]=dict(sha256=sha(raw),data=base64.b64encode(raw).decode('ascii'))
print(json.dumps(dict(stage=STAGE,files=files)))
''')
        dest=HERE/('public_preview_actual_'+str(time.time_ns()));dest.mkdir()
        pins={}
        for name,item in result['files'].items():
            assert Path(name).name==name
            raw=base64.b64decode(item['data'],validate=True)
            assert hashlib.sha256(raw).hexdigest()==item['sha256']
            (dest/name).write_bytes(raw);pins[name]=item['sha256']
        result=dict(stage=STAGE,directory=str(dest),files=pins)
    output=HERE/('ROOT_PREVIEW_'+a.action.upper()+'_'+str(time.time_ns())+'.json')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(evidence=str(output),**result),ensure_ascii=True))

if __name__=='__main__':main()
