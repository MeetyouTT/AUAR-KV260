"""Owned finite board maintenance; default invocation only reports readiness."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

CAMERA='aura-camera-ui.service'
GUI='aura-avatar-ui.service'
APP='aura-visual-servo-b4096-v2'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok,message):
    if not ok:raise RuntimeError(message)


def verify_checkpoint(document,before,*,boot,pid,birth,alive,lock_free,unit,manifest_sha=None,unit_sha=None):
    require(document.get('schema')=='aura-native-protection-checkpoint-2' and
        document.get('scope')=='final_quiescent_before_native_owner_close','Wrong checkpoint scope')
    seed,aux=document['seed'],document['auxiliary']
    require(seed['boot_id']==boot and seed['source_pid']==pid and seed['source_birth_ticks']==birth
        and seed['checkpoint_kind']==1,'Checkpoint does not match stopped owner')
    require(not alive and lock_free and unit.get('MainPID')=='0' and
        unit.get('ExecMainStatus')=='0' and unit.get('Result')=='success','Owner did not stop cleanly')
    require(not seed['fenced'] and not aux['fenced'] and not aux['active'] and not aux['primary_waiting']
        and not any(aux['pending_result_tokens']),'Native completion unconfirmed')
    require(seed['primary_calls']>=before['primary_calls'] and
        seed['primary_period_overruns']>=before['primary_period_overruns'],'Primary counters decreased')
    for index,task in [(1,'yunet'),(2,'sface')]:
        require(seed['admissions'][index]>=before['optional'][task]['calls'] and
            seed['overruns'][index]>=before['optional'][task]['overruns'],'Optional counters decreased')
    require(aux['sface_counters']['completed']>=before['sface_completed'],'SFace history decreased')
    if manifest_sha is not None:
        require(seed.get('source_manifest_sha256')==manifest_sha,'Checkpoint source manifest differs')
    if unit_sha is not None:
        require(document.get('source_unit_sha256')==unit_sha,'Checkpoint service source differs')


class Trial:
    def __init__(self,root):
        self.root=Path(root).resolve()
        require(re.fullmatch(r'/home/root/aura-pan-vsrv2-20261024/778d2512-[0-9a-f]{8}(?:-r[2-9][0-9]*)?',str(self.root)), 'Wrong maintenance root')
        self.meta=json.loads((self.root/'payload.json').read_text());self.base=self.meta['baseline']
        self.manifest=json.loads((self.root/'candidate-manifest.json').read_text())
        self.source=Path(__file__).resolve()
        self.prefix='aura-pan-vsrv2-'+self.root.name[len('778d2512-'):]

    def command(self,args,timeout=20):
        p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        require(p.returncode==0,'Command failed: '+repr(args)+' '+p.stderr[-500:])
        return p.stdout

    def props(self,unit):
        s=self.command(['systemctl','show',unit,'--property=MainPID,ActiveState,SubState,Result,ExecMainStatus,KillMode,SendSIGKILL,TimeoutStopUSec'])
        return dict(l.split('=',1) for l in s.splitlines() if '=' in l)

    def get(self,port,path):
        op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with op.open('http://127.0.0.1:'+str(port)+path,timeout=3) as response:return json.load(response)

    def state(self):return json.loads((self.root/'trial-state.json').read_text())

    def save(self,phase,**values):
        p=self.root/'trial-state.json'
        d=json.loads(p.read_text()) if p.exists() else {}
        d.update(phase=phase,updated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),**values)
        temporary=p.with_name(p.name+'.tmp-'+str(os.getpid()))
        with temporary.open('x') as f:json.dump(d,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(temporary,p)
        with (self.root/'events.jsonl').open('a') as f:
            f.write(json.dumps({'phase':phase,'monotonic':time.monotonic()})+'\n')
        return d

    def verify(self):
        require(os.uname().machine=='aarch64' and os.geteuid()==0,'Target root only')
        require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==self.base['boot_id'],'Boot changed; no action')
        require(sha('/sys/firmware/fdt')==self.base['fdt_sha256'],'Boot FDT changed')
        require(sha(self.root/'candidate-manifest.json')==self.meta['candidate_manifest_sha256'],'Candidate manifest changed')
        for name,pin in self.meta['files'].items():require(sha(self.root/name)==pin,'Payload changed: '+name)
        for unit in self.base['services'].values():
            for name,pin in unit['unit_file_sha256'].items():require(sha(name)==pin,'Existing service changed: '+name)
        require(sha(self.base['camera_config'])==self.base['camera_config_sha256'],'r4 configuration changed')
        require(sha(self.base['gui_config'])==self.base['gui_config_sha256'],'GUI configuration changed')
        require(sha(self.base['database_path'])==self.base['database_sha256'],'Identity database changed')
        if (self.root/'trial-state.json').exists():
            pin=self.state().get('controller_sha256')
            if pin:require(sha(self.source)==pin,'Owned controller changed')

    def active(self):
        text=self.command(['xmutil','listapps'])
        return [f[0] for f in (line.split() for line in text.splitlines())
                if len(f)==6 and f[1] in ('XRT_FLAT','PL_FLAT') and f[-1].rstrip(',')=='0']

    def firmware(self):return Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()

    def brief(self,h):
        s=h['dpu_schedule'];i=h['identity']
        return {'pid':h['pid'],'detected_frames':h['detected_frames'],'detection_hz':h['detection_hz'],
            'primary_calls':s['primary_calls'],'primary_period_overruns':s['primary_period_overruns'],
            'optional':{k:{n:v.get(n) for n in ['calls','overruns','native_completed','disabled','recovery']}
                for k,v in s['optional'].items()},'sface_completed':i['feature_inference']['completed'],
            'identity_ready':i['ready'],'owner_fenced':s['owner_fenced'],'native_critical':s['native_critical'],
            'worker_alive':i['face_targets']['worker_alive'],
            'gaps':i['face_targets']['freshness_metrics']['counters']['observed_gap_intervals']}

    def wait_stop(self,unit,seconds):
        self.command(['systemctl','stop','--no-block',unit])
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            state=self.props(unit)
            if state['MainPID']=='0':return state
            time.sleep(.25)
        raise RuntimeError('Stop unconfirmed; do not kill or replace '+unit)

    def dpu_lock(self):
        lock=Path('/run/aura-person-dpu.lock').open('a+')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(Path('/sys/module/zocl/refcnt').read_text().strip()=='0','ZOCL still has clients')
        return lock

    def pcm_owners(self):
        result=[]
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():continue
            try:
                for fd in (p/'fd').iterdir():
                    try:value=os.readlink(fd)
                    except OSError:continue
                    if value.startswith('/dev/snd/pcm'):
                        result.append(int(p.name));break
            except OSError:pass
        return result

    def stop_models(self):
        h=self.get(8790,'/health');before=self.brief(h)
        require(not before['owner_fenced'],'Unconfirmed native owner; no stop/replacement')
        pid=h['pid'];proc=Path('/proc')/str(pid)
        birth=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19])
        if self.props(GUI)['MainPID']!='0':
            g=self.get(8783,'/api/state')
            require(g['phase']=='IDLE' and not g['playing'] and g['audio_output_state']=='IDLE_READY'
                and g.get('local_recording',{}).get('state')!='RECORDING'
                and not g.get('local_transcription',{}).get('service',{}).get('pending'),'Interactive audio is busy')
        self.save('STOPPING_CURRENT_BUSINESS',before=before,source_pid=pid,source_birth_ticks=birth)
        self.wait_stop(GUI,40)
        end=time.monotonic()+10
        while self.pcm_owners() and time.monotonic()<end:time.sleep(.25)
        require(not self.pcm_owners(),'PCM owner did not close; no camera/firmware switch')
        prop=self.props(CAMERA)
        require(prop['KillMode']=='process' and prop['SendSIGKILL']=='no'
            and prop['TimeoutStopUSec']=='infinity','Safe native shutdown properties missing')
        unit=self.wait_stop(CAMERA,60)
        with self.dpu_lock():
            document=json.loads(Path(self.base['checkpoint']).read_text())
            native=json.loads(Path(self.base['camera_config']).read_text())['native_execution']
            verify_checkpoint(document,before,boot=self.base['boot_id'],pid=pid,birth=birth,
                alive=proc.exists(),lock_free=True,unit=unit,
                manifest_sha=native['source_manifest_sha256'],unit_sha=native['source_unit_sha256'])
        self.save('CHECKPOINT_AND_OWNER_RELEASE_CONFIRMED',checkpoint_sha256=sha(self.base['checkpoint']),
            stopped_counter_snapshot=before,checkpoint_primary_calls=document['seed']['primary_calls'],
            checkpoint_optional_overruns=document['seed']['overruns'])

    def install(self):
        require(self.active()==[self.base['app']] and self.firmware()==self.base['firmware_name'],'Baseline application differs')
        for name,item in self.base['firmware_files'].items():require(sha(name)==item['sha256'],'Baseline firmware changed')
        destination=Path('/lib/firmware/xilinx')/APP
        require(not destination.is_symlink(),'Candidate destination must not redirect')
        destination.mkdir(exist_ok=True)
        for name,pin in self.manifest['runtime_files'].items():
            target=Path(name);source=self.root/'runtime'/APP/target.name
            require(target.parent==destination and not target.is_symlink() and sha(source)==pin,'Candidate file differs')
            if target.exists():require(sha(target)==pin,'Do not overwrite an existing differing candidate')
            else:
                with target.open('xb') as out:out.write(source.read_bytes());out.flush();os.fsync(out.fileno())
        self.save('CANDIDATE_FILES_INSTALLED_NOT_LOADED')

    def switch(self,target):
        require(self.props(CAMERA)['MainPID']=='0' and self.props(GUI)['MainPID']=='0','Business services are not stopped')
        with self.dpu_lock(), Path('/run/aura-vsrv.lock').open('a+') as motion:
            fcntl.flock(motion,fcntl.LOCK_EX|fcntl.LOCK_NB)
            active=self.active()
            require(active in ([self.base['app']],[APP],[]),'Unexpected active application')
            if active!=[target]:
                if active:
                    self.command(['xmutil','unloadapp'],45)
                    require(self.active()==[],'Application unload not confirmed')
                self.command(['xmutil','loadapp',target],60)
            require(self.active()==[target] and self.firmware()==target+'.bit.bin','Application load not confirmed')
            require(Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating','FPGA not operating')
        self.save('FIRMWARE_LOADED_OUTPUT_NOT_ARMED',active_app=target)

    def id_stop(self):
        context={'boot_id':self.base['boot_id'],'fdt_sha256':self.base['fdt_sha256'],'firmware_name':APP+'.bit.bin'}
        (self.root/'context.json').write_text(json.dumps(context,indent=2)+'\n')
        self.command(['/usr/bin/python3','-B',str(self.root/'bench_identity_stop.py'),'--execute',
            '--confirmation','ID_STOP_ONLY','--manifest',str(self.root/'candidate-manifest.json'),
            '--manifest-sha256',self.meta['candidate_manifest_sha256'],'--context',str(self.root/'context.json'),
            '--output',str(self.root/'id-stop.json')],20)
        require(json.loads((self.root/'id-stop.json').read_text())['identity_stop_passed'],'ID/STOP failed')
        self.save('NEW_VSRV2_ID_AND_STOP_PASSED')

    def start_models(self):
        require(self.props(CAMERA)['MainPID']=='0','Do not replace an existing owner')
        self.command(['systemctl','reset-failed',CAMERA,GUI])
        self.command(['systemctl','start','--no-block',CAMERA])
        end=time.monotonic()+65;last=''
        while time.monotonic()<end:
            try:
                h=self.get(8790,'/health');b=self.brief(h)
                require(b['native_critical'] and not b['owner_fenced'] and b['worker_alive']
                    and b['identity_ready'] and h['detected_frames']>=5,'Native r4 not ready')
                previous=self.state()['stopped_counter_snapshot']
                require(b['primary_calls']>=previous['primary_calls'],'Primary history lost')
                for k in ['yunet','sface']:
                    require(b['optional'][k]['overruns']>=previous['optional'][k]['overruns'],'Fault history lost')
                break
            except Exception as error:last=str(error);time.sleep(.5)
        else:raise RuntimeError('Native camera startup not confirmed: '+last)
        self.command(['systemctl','start','--no-block',GUI])
        gui_config=json.loads(Path(self.base['gui_config']).read_text())
        grace=gui_config.get('display_wait_seconds',90)+gui_config.get('ready_wait_seconds',90)+30
        require(type(grace) in (int,float) and 90<=grace<=240,'Invalid existing GUI startup grace')
        end=time.monotonic()+grace
        while time.monotonic()<end:
            try:
                g=self.get(8783,'/api/state')
                require(self.props(GUI)['ActiveState']=='active' and not g['playing'],'GUI not ready')
                break
            except Exception:time.sleep(.5)
        else:raise RuntimeError('Original GUI restart not confirmed')
        self.save('ORIGINAL_R4_AND_GUI_RUNNING',restarted=self.brief(self.get(8790,'/health')))

    def observe(self,seconds=60):
        before=self.brief(self.get(8790,'/health'));began=time.monotonic()
        for _ in range(seconds):
            time.sleep(1);after=self.brief(self.get(8790,'/health'))
            require(after['pid']==before['pid'] and not after['owner_fenced'] and after['worker_alive'],'Business owner changed or fenced')
        elapsed=time.monotonic()-began
        require(after['identity_ready'] and all(not after['optional'][k]['disabled'] for k in ['yunet','sface']),'Optional backend did not recover')
        require((after['detected_frames']-before['detected_frames'])/elapsed>=9.3,'YOLO throughput below controlled window gate')
        require(after['primary_period_overruns']==before['primary_period_overruns'] and after['gaps']==before['gaps'],'New primary/freshness failure')
        self.verify()
        result={'elapsed_s':elapsed,'before':before,'after':after,
            'yolo_window_hz':(after['detected_frames']-before['detected_frames'])/elapsed,
            'sface_new_completed':after['sface_completed']-before['sface_completed'],
            'physical_motion_verified':False,'external_waveform_verified':False}
        (self.root/'coexistence-window.json').write_text(json.dumps(result,indent=2)+'\n')
        self.save('CANDIDATE_READY_FOR_FINITE_OBSERVATION',window=result)

    def restore(self):
        self.verify();active=self.active();require(active in ([APP],[self.base['app']],[]),'Other user changed firmware')
        camera=self.props(CAMERA)
        if camera['MainPID']!='0':
            if active==[self.base['app']] and camera['ActiveState']=='active':
                self.command(['systemctl','start','--no-block',GUI])
                self.command(['systemctl','stop',self.prefix+'-guard.timer'])
                return self.save('BASELINE_ALREADY_RUNNING')
            self.stop_models()
        require(self.props(CAMERA)['MainPID']=='0','Unconfirmed owner retained; no firmware reload')
        if self.props(GUI)['MainPID']!='0':self.wait_stop(GUI,40)
        self.switch(self.base['app']);self.start_models()
        require(Path('/etc/vart.conf').read_text()==self.base['vart_conf'],'Original VART path not restored')
        self.command(['systemctl','stop',self.prefix+'-guard.timer'])
        return self.save('BASELINE_RESTORED_AFTER_TRIAL_FAILURE')

    def activate(self):
        self.verify();require(not (self.root/'trial-state.json').exists(),'Trial already launched; query its state')
        for name in [CAMERA,GUI]:require(self.props(name)['MainPID']==self.base['services'][name]['MainPID'],'Initial service PID changed')
        self.save('PREPARED',controller=str(self.source),controller_sha256=sha(self.source))
        self.command(['systemd-run','--unit='+self.prefix+'-guard','--on-active=600',
            '--timer-property=AccuracySec=1','--property=Type=oneshot','--property=TimeoutStartSec=infinity',
            '--property=KillMode=process','--property=SendSIGKILL=no','/usr/bin/python3','-B',str(self.source),
            '--root',str(self.root),'recover'])
        try:
            self.install();self.stop_models();self.switch(APP);self.id_stop();self.start_models();self.observe()
        except BaseException as error:
            self.save('ACTIVATION_FAILED',error_type=type(error).__name__,error=str(error))
            try:self.restore()
            except BaseException as recovery_error:self.save('RECOVERY_HOLD',recovery_error=str(recovery_error))
            raise

    def commit(self):
        self.verify();require(self.state()['phase']=='CANDIDATE_READY_FOR_FINITE_OBSERVATION','Trial not ready')
        report=json.loads((self.root/'finite-step-result.json').read_text())
        require(report['status']=='FINITE_ACK_AND_STOP_PASS_OBSERVATION_PENDING'
            and report['result']['stopped']['flags']==0,'Finite output was not stopped')
        h=self.brief(self.get(8790,'/health'))
        require(not h['owner_fenced'] and h['identity_ready'] and h['worker_alive'],'r4 not healthy')
        self.command(['systemctl','stop',self.prefix+'-guard.timer'])
        return self.save('CANDIDATE_STOPPED_RETAINED_PHYSICAL_FEEDBACK_PENDING',final_health=h,
            motion_output_disabled=True,physical_motion_verified=False,external_waveform_verified=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root');parser.add_argument('action',nargs='?',choices=['check','launch','run','recover','commit'])
    args=parser.parse_args()
    if not args.root or not args.action:
        print(json.dumps({'controller_source_staged':True,'production_modified':False}));return
    trial=Trial(args.root)
    if args.action=='check':trial.verify();print(json.dumps({'context_passed':True,'production_modified':False}));return
    if args.action=='launch':
        trial.verify();print(trial.command(['systemd-run','--unit='+trial.prefix+'-activation',
            '--property=Type=exec','--property=Nice=10','--property=TimeoutStartSec=infinity',
            '--property=KillMode=process','--property=SendSIGKILL=no','/usr/bin/python3','-B',str(trial.source),
            '--root',str(trial.root),'run']));return
    with (trial.root/'operation.lock').open('a+') as own, (Path(trial.base['ops_root'])/'operation.lock').open('a+') as existing:
        fcntl.flock(own,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(existing,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.action=='run':trial.activate()
        elif args.action=='recover':trial.restore()
        else:trial.commit()
    print(json.dumps({'phase':trial.state()['phase'],'root':str(trial.root)}))


if __name__=='__main__':main()
