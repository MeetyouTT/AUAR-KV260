"""GUI-only manual-pan publication. Never stop camera, reload PL, or auto-jog."""
import argparse,fcntl,hashlib,importlib.util,json,os,shutil,subprocess,sys,time,urllib.request
from pathlib import Path

ROOT=Path('/home/root/aura-pan-ui-v2-20261024/observed-ecfbdef064d157b6')
BOARD_CONTROLLER=Path('/home/root/aura-post-power-20261022/helpers/ded9704ecc463a50/source.py')
BOARD_CONTROLLER_SHA='ded9704ecc463a5040ff59056efa71321eb104b6aa0d9f047e9e80fb14662c45'
BOARD_ROOT=Path('/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2')
GUI='aura-avatar-ui.service';CAMERA='aura-camera-ui.service'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def need(value,message):
    if not value:raise RuntimeError(message)


class GuiTrial:
    def __init__(self):
        self.meta=json.loads((ROOT/'meta.json').read_text());self.base=self.meta['baseline']
        self.prepared=json.loads((ROOT/'prepared.json').read_text())
        self.prefix='aura-pan-ui-v2-'+self.meta['tag']
        self.override=Path('/etc/systemd/system')/(GUI+'.d')/('zzzzzzzzzzzzzz-aura-pan-ui-'+self.meta['tag']+'.conf')
        self.source=Path(__file__).resolve()
        need(sha(BOARD_CONTROLLER)==BOARD_CONTROLLER_SHA,'Hardware controller changed')
        spec=importlib.util.spec_from_file_location('pan_hardware_context',str(BOARD_CONTROLLER))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.board=module.Trial(BOARD_ROOT)

    def command(self,args,timeout=15):
        p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        need(p.returncode==0,'Command failed: '+repr(args)+' '+p.stderr[-500:])
        return p.stdout

    def props(self,unit):
        text=self.command(['systemctl','show',unit,'--property=ActiveState,SubState,MainPID,Result,ExecMainStatus,DropInPaths'])
        return dict(l.split('=',1) for l in text.splitlines() if '=' in l)

    def get(self,port,path):
        op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with op.open('http://127.0.0.1:'+str(port)+path,timeout=3) as response:return json.load(response)

    def health(self):
        h=self.get(8790,'/health');s=h['dpu_schedule'];i=h['identity']
        return {'pid':h['pid'],'detected_frames':h['detected_frames'],'native_critical':s['native_critical'],
            'owner_fenced':s['owner_fenced'],'primary_period_overruns':s['primary_period_overruns'],
            'optional_overruns':{k:s['optional'][k]['overruns'] for k in ['yunet','sface']},
            'optional_disabled':{k:s['optional'][k]['disabled'] for k in ['yunet','sface']},
            'identity_ready':i['ready'],'worker_alive':i['face_targets']['worker_alive'],
            'gaps':i['face_targets']['freshness_metrics']['counters']['observed_gap_intervals']}

    def state(self):return json.loads((ROOT/'trial-state.json').read_text())

    def save(self,phase,**values):
        p=ROOT/'trial-state.json';d=json.loads(p.read_text()) if p.exists() else {}
        d.update(phase=phase,host_boot=self.base['boot'],updated_monotonic_ns=time.monotonic_ns(),**values)
        temporary=p.with_name(p.name+'.tmp-'+str(os.getpid()))
        with temporary.open('x') as f:json.dump(d,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(temporary,p);return d

    def verify(self):
        self.board.verify()
        need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==self.base['boot'],'Boot changed')
        need(self.props(CAMERA)['MainPID']==str(self.base['camera_pid']),'Existing camera owner changed')
        for n,pin in self.base['camera_unit']['file_sha256'].items():need(sha(n)==pin,'Camera service source changed')
        for n,pin in self.base['gui_unit']['file_sha256'].items():need(sha(n)==pin,'Original GUI service source changed')
        need(sha(self.base['startup_config_path'])==self.base['startup_config_sha256'],'Original startup changed')
        need(sha(ROOT/'startup/config.json')==self.prepared['startup_config_sha256'],'Candidate startup changed')
        need(sha(ROOT/'startup/launcher.py')==self.prepared['launcher_sha256'],'Candidate launcher changed')
        for n,pin in self.prepared['source_after'].items():need(sha(ROOT/'runtime/aura'/n)==pin,'GUI source differs: '+n)
        if (ROOT/'trial-state.json').exists():
            pin=self.state().get('controller_sha256')
            if pin:need(sha(self.source)==pin,'Owned GUI controller changed')
        h=self.health()
        need(h['pid']==self.base['camera_pid'] and h['native_critical'] and not h['owner_fenced']
            and h['worker_alive'] and h['identity_ready'],'Camera health differs')
        return h

    def stop_gui(self):
        self.command(['systemctl','stop','--no-block',GUI])
        end=time.monotonic()+45
        while time.monotonic()<end:
            if self.props(GUI)['MainPID']=='0':return
            time.sleep(.25)
        raise RuntimeError('GUI did not stop; no replacement')

    def wait_gui(self,new):
        end=time.monotonic()+210;last=''
        while time.monotonic()<end:
            try:
                g=self.get(8783,'/api/state');p=self.props(GUI)
                need(p['ActiveState']=='active' and g['phase']=='IDLE' and not g['playing']
                    and g['audio_output_state']=='IDLE_READY','GUI startup pending')
                if new:
                    pan=g['manual_pan']
                    need(pan['state']=='READY' and pan['minimum_us']==1425 and pan['maximum_us']==1445,
                        'Observed manual backend not READY: '+str(pan.get('error','')))
                    need(pan['automatic_following'] is False and not pan['history'],'Unexpected automatic motion')
                    readback=pan['readback'];need(readback['flags']==0 and readback['lease_left_ms']==0,'Motion output not disabled')
                return g
            except Exception as error:last=str(error);time.sleep(.5)
        raise RuntimeError('GUI readiness failed: '+last)

    def restore(self):
        if not self.override.exists():
            self.command(['systemctl','start','--no-block',GUI]);self.wait_gui(False)
            self.command(['systemctl','stop',self.prefix+'-guard.timer'])
            return self.save('ORIGINAL_GUI_ALREADY_RESTORED')
        state=self.state()
        need(not self.override.is_symlink() and sha(self.override)==state['override_sha256'],'Refuse removing another override')
        self.stop_gui();self.override.unlink();self.command(['systemctl','daemon-reload'])
        self.command(['systemctl','reset-failed',GUI]);self.command(['systemctl','start','--no-block',GUI])
        self.wait_gui(False);self.verify()
        self.command(['systemctl','stop',self.prefix+'-guard.timer'])
        return self.save('ORIGINAL_GUI_RESTORED_CAMERA_UNCHANGED')

    def activate(self):
        before=self.verify();need(not (ROOT/'trial-state.json').exists(),'UI trial already launched')
        need(self.props(GUI)['MainPID']==self.base['gui_unit']['MainPID'],'Original GUI owner changed')
        g=self.get(8783,'/api/state')
        need(g['phase']=='IDLE' and not g['playing'] and g['audio_output_state']=='IDLE_READY'
            and g.get('local_recording',{}).get('state')!='RECORDING','GUI audio is busy')
        self.save('PREPARED',controller_sha256=sha(self.source),before_camera=before,original_gui_pid=self.base['gui_unit']['MainPID'])
        self.command(['systemd-run','--unit='+self.prefix+'-guard','--on-active=420','--timer-property=AccuracySec=1',
            '--property=Type=oneshot','--property=TimeoutStartSec=infinity','--property=KillMode=process',
            '/usr/bin/python3','-B',str(self.source),'recover'])
        try:
            self.save('STOPPING_ONLY_GUI');self.stop_gui()
            old=Path(self.prepared['existing_gui_runtime'])
            prefs={}
            for p in old.glob('*settings*.json'):
                if p.is_file():shutil.copy2(p,ROOT/'runtime'/p.name);prefs[p.name]=sha(p)
            self.save('GUI_STOPPED',preferences_before=prefs)
            raw=('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(ROOT/'startup/launcher.py')+
                 ' --config '+str(ROOT/'startup/config.json')+'\nWorkingDirectory='+str(ROOT/'runtime/aura')+'\n').encode()
            need(not self.override.exists(),'Do not overwrite another GUI override')
            with self.override.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            self.save('OWN_OVERRIDE_INSTALLED',override=str(self.override),override_sha256=hashlib.sha256(raw).hexdigest())
            self.command(['systemctl','daemon-reload']);self.command(['systemctl','reset-failed',GUI])
            self.command(['systemctl','start','--no-block',GUI]);self.wait_gui(True)
            first=self.verify();began=time.monotonic();self.save('OBSERVING',first_camera=first)
            for _ in range(60):
                time.sleep(1);h=self.health();need(h['pid']==first['pid'] and not h['owner_fenced'],'Camera owner changed')
            last=self.verify();elapsed=time.monotonic()-began;g=self.wait_gui(True)
            need(last['gaps']==first['gaps'] and last['primary_period_overruns']==first['primary_period_overruns'],'New primary/freshness failure')
            need(last['optional_overruns']==first['optional_overruns'] and not any(last['optional_disabled'].values()),'Optional backend failed')
            rate=(last['detected_frames']-first['detected_frames'])/elapsed;need(rate>=9.3,'YOLO throughput fell')
            for name,pin in self.state()['preferences_before'].items():need(sha(ROOT/'runtime'/name)==pin,'Preference changed during the trial')
            pan=g['manual_pan']
            self.save('ACCEPTED_MANUAL_READY_NO_AUTOMATIC_MOTION',camera_pid_unchanged=True,
                gui_pid=self.props(GUI)['MainPID'],camera=last,window_seconds=elapsed,yolo_window_hz=rate,
                manual_pan=pan,automatic_motion_commands_sent=0)
            self.command(['systemctl','stop',self.prefix+'-guard.timer'])
        except BaseException as error:
            self.save('UI_TRIAL_FAILED',error_type=type(error).__name__,error=str(error))
            try:self.restore()
            except BaseException as restore_error:self.save('GUI_RECOVERY_HOLD',restore_error=str(restore_error))
            raise


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',nargs='?',choices=['check','launch','run','recover'])
    args=parser.parse_args()
    if args.action is None:print(json.dumps({'gui_controller_staged':True,'service_changes':False}));return
    t=GuiTrial()
    if args.action=='check':t.verify();print(json.dumps({'passed':True,'new_mmio_opened':False}));return
    if args.action=='launch':
        t.verify();print(t.command(['systemd-run','--unit='+t.prefix+'-activation','--property=Type=exec',
            '--property=Nice=10','--property=TimeoutStartSec=infinity','--property=KillMode=process',
            '/usr/bin/python3','-B',str(t.source),'run']));return
    with (ROOT/'operation.lock').open('a+') as own,(Path(t.board.base['ops_root'])/'operation.lock').open('a+') as other:
        fcntl.flock(own,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.action=='run':t.activate()
        else:t.restore()
    print(json.dumps({'phase':t.state()['phase'],'camera_pid':t.base['camera_pid']}))


if __name__=='__main__':main()
