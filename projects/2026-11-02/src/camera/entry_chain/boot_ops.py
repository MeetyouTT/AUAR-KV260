"""Owned maintenance controller. All hardware model work is sequential.

No timeout kills an unconfirmed model owner. Existing units/configs are never
overwritten: only this controller's uniquely named drop-ins are managed.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

from policy import benchmark_safe, condition, counters, require_native_healthy, window_result

CAMERA='aura-camera-ui.service'
GUI='aura-avatar-ui.service'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def boot():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
def atomic(path,value):
    path=Path(path);temporary=path.with_name(path.name+'.tmp-'+str(os.getpid()))
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    with temporary.open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    os.replace(temporary,path)
    fd=os.open(str(path.parent),os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


class Ops:
    def __init__(self,root):
        self.root=Path(root).resolve();self.meta=json.loads((self.root/'meta.json').read_text())
        assert str(self.root)==self.meta['root']
    def state(self):return json.loads((self.root/'state.json').read_text())
    def save(self,value):
        value['updated_boot']=boot();value['updated_mono_ns']=time.monotonic_ns()
        atomic(self.root/'state.json',value)
    def phase(self,name,**values):
        state=self.state();state.update(phase=name,**values);self.save(state);return state
    def command(self,argv,timeout=15):
        p=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
        if p.returncode:raise RuntimeError('Command failed: '+repr(argv)+' '+p.stderr[-700:])
        return p.stdout
    def props(self,unit):
        out=self.command(['systemctl','show',unit,'-p','ActiveState','-p','SubState','-p','MainPID','-p','Result','-p','ExecMainStatus'])
        return dict(line.split('=',1) for line in out.splitlines() if '=' in line)
    def health(self):
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open('http://127.0.0.1:8790/health',timeout=4) as stream:return json.load(stream)
    def verify(self):
        assert os.geteuid()==0
        for name,pin in self.meta['protected'].items():assert sha(name)==pin,'Protected file changed: '+name
        for name,pin in self.meta['source_pins'].items():assert sha(self.root/name)==pin,'Controller source changed'
    def own_file(self,path,raw):
        path=Path(path);state=self.state()
        assert not path.exists() and not path.is_symlink()
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
        state.setdefault('owned',{})[str(path)]=hashlib.sha256(raw).hexdigest();self.save(state)
    def remove_own(self,path):
        path=Path(path);state=self.state();pin=state.get('owned',{}).get(str(path))
        if not path.exists():return
        assert pin and not path.is_symlink() and sha(path)==pin,'Refuse deleting unrelated override'
        path.unlink();state['owned'].pop(str(path));self.save(state)
    def paths(self):
        tag=self.meta['tag']
        return dict(camera=Path('/etc/systemd/system')/(CAMERA+'.d')/('zzzzzz-native-maintenance-'+tag+'.conf'),
            gui=Path('/etc/systemd/system')/(GUI+'.d')/('zzzzzz-native-maintenance-'+tag+'.conf'),
            execution=Path('/etc/systemd/system')/(CAMERA+'.d')/('zzzzzzz-native-execution-'+tag+'.conf'),
            rescue_service=Path('/etc/systemd/system')/('aura-native-rescue-'+tag+'.service'),
            rescue_timer=Path('/etc/systemd/system')/('aura-native-rescue-'+tag+'.timer'))
    def gate(self,role):
        return condition(self.meta['source_boot'],boot(),self.state()['phase'],role)
    def arm(self):
        self.verify();assert boot()==self.meta['source_boot'] and self.state()['phase']=='PREPARED'
        h=self.health();assert h['pid']==self.meta['old_camera_pid'] and not h['dpu_schedule']['owner_fenced']
        assert all(h['dpu_schedule']['optional'][k]['disabled'] for k in ('yunet','sface'))
        self.phase('ARMING');paths=self.paths()
        for role in ('camera','gui'):
            raw=('[Service]\nExecCondition=/usr/bin/python3 -B '+str(self.root/'boot_ops.py')+
                 ' --root '+str(self.root)+' condition '+role+'\nRestart=no\n').encode()
            self.own_file(paths[role],raw)
        service=('[Unit]\nDescription=AURA native maintenance no-execution rescue\nAfter=local-fs.target\n'
            '[Service]\nType=oneshot\nTimeoutStartSec=infinity\nKillMode=process\nExecStart=/usr/bin/python3 -B '+
            str(self.root/'boot_ops.py')+' --root '+str(self.root)+' rescue\n').encode()
        timer=('[Unit]\nDescription=AURA native maintenance boot rescue\n[Timer]\nOnBootSec=120\nUnit='+
            paths['rescue_service'].name+'\n[Install]\nWantedBy=timers.target\n').encode()
        self.own_file(paths['rescue_service'],service);self.own_file(paths['rescue_timer'],timer)
        self.command(['systemctl','daemon-reload'])
        self.command(['systemctl','enable',paths['rescue_timer'].name])
        assert self.props(CAMERA)['MainPID']==str(self.meta['old_camera_pid'])
        self.phase('ARMED',armed_source_boot=boot(),maintenance_started=False)
        return self.state()
    def reboot(self):
        self.verify();state=self.state()
        assert state['phase']=='ARMED' and boot()==self.meta['source_boot']
        assert not self.health()['dpu_schedule']['owner_fenced']
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open('http://127.0.0.1:8783/api/state',timeout=4) as stream:gui=json.load(stream)
        assert gui.get('phase')=='IDLE' and not gui.get('playing') and gui.get('audio_output_state')=='IDLE_READY'
        self.command(['systemctl','stop',GUI],timeout=40)
        assert self.props(GUI)['MainPID']=='0'
        self.phase('ARMED',reboot_requested=True)
        # The UART returns before shutdown; reconnect reads the new kernel UUID.
        self.command(['systemctl','reboot','--no-block'])
        return {'reboot_requested':True,'old_boot':boot()}
    def restore_original(self):
        state=self.state();assert not state.get('maintenance_started') or state.get('benchmark_cleanup_confirmed')
        assert self.props(CAMERA)['MainPID']=='0' and self.props(GUI)['MainPID']=='0'
        for key in ('execution','camera','gui'):self.remove_own(self.paths()[key])
        self.command(['systemctl','daemon-reload'])
        self.phase('OLD_RESTORED')
        self.command(['systemctl','reset-failed',CAMERA,GUI])
        self.command(['systemctl','start',CAMERA])
        self.command(['systemctl','start',GUI],timeout=45)
        self.command(['systemctl','disable','--now',self.paths()['rescue_timer'].name])
        return self.state()
    def rescue(self):
        state=self.state()
        if boot()==self.meta['source_boot']:return {'source_boot_no_action':True}
        if state['phase'] not in ('PREPARED','ARMING','ARMED') or state.get('maintenance_started'):
            return {'no_owner_replacement':True,'phase':state['phase']}
        # No maintenance model process has ever been started in this kernel.
        return self.restore_original()
    def benchmark(self):
        self.verify();assert boot()!=self.meta['source_boot'] and self.state()['phase']=='ARMED'
        assert all(self.props(unit)['MainPID']=='0' for unit in (CAMERA,GUI))
        self.phase('MAINTENANCE',maintenance_started=True,maintenance_boot=boot())
        folder=self.root/('benchmark-'+boot());folder.mkdir(mode=0o700)
        # Build a plan from the already pinned target files. No model is loaded.
        args=['/usr/bin/python3','-B',str(self.root/'build_plan.py'),
            '--legacy-root',self.meta['legacy_root']+'/aura','--candidate-root',self.meta['candidate_root']+'/aura',
            '--bridge',self.meta['native_library'],'--production-snapshot',self.meta['prefix_path'],
            '--expected-boot-id',boot(),'--yolo-owner-config',str(self.root/'yolo.json'),
            '--optional-models',str(self.root/'models.json'),'--new-output-directory',str(folder/'plan')]
        self.command(args,timeout=25)
        result_dir=folder/'result'
        command=['/usr/bin/python3','-B',str(self.root/'equivalence_benchmark.py'),
            '--plan',str(folder/'plan/plan.json'),'--output-directory',str(result_dir),'--execute-maintenance']
        with (folder/'benchmark.log').open('xb') as log:
            child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
            self.phase('MAINTENANCE',benchmark_pid=child.pid,benchmark_result=str(result_dir/'result.json'))
            # Deliberately no timeout/kill. An uncertain owner remains alive.
            code=child.wait()
        report=json.loads((result_dir/'result.json').read_text()) if (result_dir/'result.json').exists() else None
        checkpoint=json.loads((result_dir/'checkpoint.json').read_text()) if (result_dir/'checkpoint.json').exists() else None
        safe=benchmark_safe(report,checkpoint,code,False)
        self.phase('QUALIFIED' if safe and report and report.get('passed') else 'BENCHMARK_SAFE_FAILURE' if safe else 'UNSAFE_HOLD',
            benchmark_exit=code,benchmark_cleanup_confirmed=safe,benchmark_report=report)
        return self.state()
    def activate(self):
        self.verify();state=self.state()
        assert boot()!=self.meta['source_boot'] and state['phase']=='QUALIFIED' and state['benchmark_cleanup_confirmed']
        assert self.props(CAMERA)['MainPID']=='0'
        raw=('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(self.root/'native_entry.py')+
            '\nWorkingDirectory='+self.meta['candidate_root']+'/aura\nRestart=no\n'
            'KillMode=process\nTimeoutStopSec=infinity\nSendSIGKILL=no\n').encode()
        self.own_file(self.paths()['execution'],raw)
        self.command(['systemctl','daemon-reload']);self.phase('NATIVE_START')
        self.command(['systemctl','reset-failed',CAMERA]);self.command(['systemctl','start',CAMERA])
        until=time.monotonic()+55;last=''
        while time.monotonic()<until:
            try:
                h=self.health();require_native_healthy(h)
                # Startup model loading predates the cumulative health rate.
                # Fresh observed results prove ready; the separate short
                # window measures the steady 9.5Hz throughput requirement.
                if (h['pid']==int(self.props(CAMERA)['MainPID']) and h['detected_frames']>=5
                        and h['observation_age_ms'] is not None and 0<=h['observation_age_ms']<750):break
            except Exception as exc:last=type(exc).__name__+': '+str(exc)
            time.sleep(.5)
        else:
            self.phase('NATIVE_START_HOLD',startup_error=last)
            return self.state() # No automatic kill or replacement owner.
        self.phase('NATIVE_READY',new_camera_pid=h['pid'],startup_counters=counters(h))
        self.command(['systemctl','reset-failed',GUI]);self.command(['systemctl','start',GUI],timeout=45)
        return self.state()
    def observe(self,seconds):
        self.verify();assert 10<=seconds<=600 and self.state()['phase'] in ('NATIVE_READY','OBSERVING')
        first=self.health();require_native_healthy(first);before=counters(first);began=time.monotonic()
        self.phase('OBSERVING');samples=[]
        try:
            while time.monotonic()-began<seconds:
                time.sleep(1);h=self.health();require_native_healthy(h)
                item=counters(h);samples.append({'elapsed':time.monotonic()-began,**item})
                if item['pid']!=before['pid'] or item['faults']!=before['faults']:
                    raise ValueError('Native optional fault or process changed')
            result=window_result(before,counters(self.health()),time.monotonic()-began)
            if not result['short_window_passed']:raise ValueError('Short business window thresholds not met')
            self.phase('NATIVE_READY',last_window=result,window_samples=samples)
        except Exception as exc:
            self.phase('OBSERVATION_FAILED',observation_error=str(exc),window_samples=samples)
        return self.state()
    def protected_rollback(self):
        self.verify();state=self.state()
        assert state['phase'] in ('NATIVE_READY','OBSERVATION_FAILED','NATIVE_START_HOLD')
        h=self.health();assert not h['dpu_schedule']['owner_fenced'],'Unconfirmed owner cannot be replaced'
        native_pid=h['pid']
        self.command(['systemctl','stop',GUI],timeout=45)
        self.command(['systemctl','stop',CAMERA],timeout=20)
        props=self.props(CAMERA)
        assert props['MainPID']=='0' and props['ExecMainStatus']=='0' and props['Result']=='success'
        checkpoint=Path(json.loads(Path(self.meta['candidate_config']).read_text())['native_execution']['checkpoint_output'])
        document=json.loads(checkpoint.read_text());seed=document['seed'];aux=document['auxiliary']
        assert seed['source_pid']==native_pid and seed['boot_id']==boot() and not seed['fenced']
        assert document['scope']=='final_quiescent_before_native_owner_close' and not any(aux['pending_result_tokens'])
        assert not (Path('/proc')/str(native_pid)).exists()
        atomic(self.root/'rollback-pin.json',{'path':str(checkpoint),'sha256':sha(checkpoint)})
        self.remove_own(self.paths()['execution'])
        raw=('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(self.root/'rollback_entry.py')+
            '\nWorkingDirectory='+self.meta['legacy_root']+'/aura\nRestart=no\n').encode()
        self.own_file(self.paths()['execution'],raw)
        self.command(['systemctl','daemon-reload']);self.phase('ROLLBACK_READY',native_checkpoint_sha256=sha(checkpoint))
        self.command(['systemctl','reset-failed',CAMERA,GUI]);self.command(['systemctl','start',CAMERA])
        self.command(['systemctl','start',GUI],timeout=45)
        return self.state()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',required=True)
    parser.add_argument('action',choices=['condition','arm','reboot','rescue','benchmark','activate','observe','rollback','status','restore-original'])
    parser.add_argument('argument',nargs='?');args=parser.parse_args();ops=Ops(args.root)
    if args.action=='condition':return 0 if ops.gate(args.argument) else 1
    if args.action=='status':
        value=ops.state()
        if value.get('benchmark_result'):
            path=Path(value['benchmark_result'])
            if path.exists():value['benchmark_live_result']=json.loads(path.read_text())
            checkpoint=path.parent/'checkpoint.json'
            if checkpoint.exists():value['benchmark_live_checkpoint']=json.loads(checkpoint.read_text())
        print(json.dumps(value));return 0
    lock=(ops.root/'operation.lock').open('a+')
    fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    if args.action=='observe':value=ops.observe(int(args.argument or '60'))
    else:value=getattr(ops,{'rollback':'protected_rollback','restore-original':'restore_original'}.get(args.action,args.action))()
    print(json.dumps(value));return 0


if __name__=='__main__':raise SystemExit(main())
