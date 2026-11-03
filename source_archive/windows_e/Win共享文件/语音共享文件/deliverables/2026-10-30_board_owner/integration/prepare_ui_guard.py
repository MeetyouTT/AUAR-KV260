"""Install one reversible no-force-kill guard, without closing any UI."""
import datetime
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(PROJECT/'deliverables/2026-10-18_board_dialogue')]
from board_ssh import ssh
from resume_baseline import write_json

SCRIPT=r'''
import hashlib,importlib.util,json,os,re,subprocess,time
from pathlib import Path
UNIT='aura-avatar-ui.service'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='8100a7fd-0c6a-46c4-82b8-f874988a1521'
def show():
 raw=subprocess.check_output(['systemctl','show',UNIT,'--all'],text=True)
 return dict(l.split('=',1) for l in raw.splitlines() if '=' in l)
def owner(pid):
 p=Path('/proc')/str(pid)
 return dict(birth=p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
             argv=[x.decode() for x in p.joinpath('cmdline').read_bytes().split(bytes([0])) if x])
def idle():
 p=Path('/home/root/aura-board-owner-candidate-20261030/perf-fa0bc04a6f8c15a9/probe.py')
 assert hashlib.sha256(p.read_bytes()).hexdigest()=='b53803cab734bb69cd8a62698c92d630ed98d9d0b2cee7ecc9232bcb4a4323a3'
 spec=importlib.util.spec_from_file_location('_guard_metadata',str(p));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 value=m.safety_snapshot();assert value['ui_pid']==1296 and value['camera_pid']==260102
 assert value['pan_state']=='FAULT' and value['pulse_us'] is None
 return value
before=show();assert before['MainPID']=='1296' and before['ActiveState']=='active' and not before.get('Job')
assert owner(1296)=={'birth':BASE['birth'],'argv':BASE['argv']}
assert owner(1366)=={'birth':BASE['children'][0]['birth'],'argv':BASE['children'][0]['argv']}
assert before['ExecStart']==BASE['properties']['ExecStart']
state_before=idle()
paths=[before['FragmentPath']]+before['DropInPaths'].split();pins={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
count=max(len(re.match(r'z*',Path(p).name).group()) for p in paths)+1
name='z'*count+'-aura-yuki-capacity-20261030.conf'
assert len(name)<255 and all(Path(p).name<name for p in before['DropInPaths'].split())
folder=Path('/run/systemd/system')/(UNIT+'.d');folder.mkdir(mode=0o755,exist_ok=True)
assert folder.resolve()==folder
guard=folder/name;assert not guard.exists() and not guard.is_symlink()
raw=b'[Service]\nRestart=no\nSendSIGKILL=no\nTimeoutStopSec=infinity\nKillSignal=SIGTERM\n'
data_root=Path('/home/root/aura-board-owner-candidate-20261030/ui-capacity-control-20261030')
assert not data_root.exists();data_root.mkdir(mode=0o700)
record=dict(phase='GUARD_INTENT',unit=UNIT,guard=str(guard),guard_sha256=hashlib.sha256(raw).hexdigest(),
 original_properties={k:before.get(k,'') for k in BASE['properties']},original_source_sha256=pins,
 original_supervisor=BASE['pid'],original_child=1366,state=state_before)
def save():
 p=data_root/'state.json';tmp=data_root/'state.partial.json'
 fd=os.open(str(tmp),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 with os.fdopen(fd,'w') as out:json.dump(record,out);out.flush();os.fsync(out.fileno())
 os.replace(str(tmp),str(p))
save()
fd=os.open(str(guard),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=8)
after=show()
assert after['MainPID']=='1296' and after['ExecStart']==before['ExecStart'] and not after.get('Job')
assert after['Restart']=='no' and after['SendSIGKILL']=='no' and after['TimeoutStopUSec']=='infinity' and after['KillSignal']=='15'
assert [p for p in after['DropInPaths'].split() if p!=str(guard)]==before['DropInPaths'].split()
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in pins.items())
assert idle()==state_before
record.update(phase='GUARDED',guarded_utc=UTC);save()
print(json.dumps(dict(status='GUARDED_NO_UI_CLOSED',guard=str(guard),journal=str(data_root/'state.json'),ui_pid=1296,gtk_pid=1366,camera_pid=260102,original_sources_unchanged=True)))
'''


def main():
    baseline=json.loads((HERE/'resume_ui_trial/actual_ui_baseline.json').read_text(encoding='utf-8'))
    prefix='BASE='+repr(baseline)+'\nUTC='+repr(datetime.datetime.now(datetime.timezone.utc).isoformat())+'\n'
    value=json.loads(ssh('python3 -B -',prefix+SCRIPT,timeout=35))
    write_json(HERE/'resume_ui_trial/actual_guard.json',value)
    print(json.dumps(value))


if __name__=='__main__':main()
