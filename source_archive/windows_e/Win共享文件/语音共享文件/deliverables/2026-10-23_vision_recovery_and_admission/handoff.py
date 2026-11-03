"""Owned audio/camera transitions. No model, identity or motion changes."""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from live_checks import PARENT_RELEASE, PARENT_UNIT_SHA, PARENT_CONFIG, PARENT_IDENTITY, validate_state, validate_parent_state, validate_candidate_state, camera_snapshot, wait_parent_ready

BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
DEFINITIONS=Path('/home/root/aura-post-power-20261022/helpers/10261c1b5b2b7458/source.py')
DEFINITION_SHA='10261c1b5b2b745877121c90d940be80e67f91ae57a524ed2040a1f52af4f65c'
CFG=Path('/home/root/aura-speech-motion-20261021/de989bf024a9/startup/config.json')
CFG_SHA='6c47003c4d020066a3ba4c9daa8f905101d633c4cf507951bea3ac3ca86a161d'
PREF=Path('/home/root/.local/share/aura/handsfree_dialogue.json')
AUDIO='aura-avatar-ui.service'
CAMERA='aura-camera-ui.service'
XSERVER='xserver-nodm.service'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path,value):
    p=Path(path);tmp=p.with_name(p.name+'.tmp-'+str(os.getpid()))
    with tmp.open('x') as f:
        json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(str(tmp),str(p))


def transition(ops,target,*,force=False):
    """Caller arms an independent restore before entering this protocol."""
    ops.verify()
    if not force and ops.ready(target):return {'already_ready':True}
    ops.assert_idle_or_stopped()
    ops.assert_guard_armed()
    ops.stop_audio()
    ops.wait_pcm_closed()
    ops.verify()
    ops.switch_gui(target)
    ops.switch_camera(target)
    ops.wait_camera(target)
    ops.restore_preference()
    ops.start_audio()
    ops.wait_audio_ready()
    ops.verify()
    return {'already_ready':False}


def owned_operation(ops,target,observe,*,force=False):
    """The same restore protocol runs after success and after every failure."""
    try:
        transition(ops,target,force=force)
        return observe()
    finally:
        transition(ops,'original')


class BoardOps:
    def __init__(self,folder):
        self.folder=Path(folder)
        assert self.folder.resolve()==self.folder and self.folder.parent==Path('/home/root/aura-coordinated-switch-20261023')
        assert digest(DEFINITIONS)==DEFINITION_SHA
        sys.dont_write_bytecode=True
        spec=importlib.util.spec_from_file_location('_retained_trial_definitions',DEFINITIONS)
        self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
        self.m.camera=lambda:camera_snapshot(self.m)
        self.meta=json.loads((self.folder/'session.json').read_text()) if (self.folder/'session.json').exists() else None

    def service(self,*args):
        timeout=40 if args and args[0]=='stop' and any(name in args for name in (AUDIO,CAMERA)) else 20
        return self.m.command(['systemctl']+list(args),timeout=timeout)
    def active(self,name):return self.service('show',name,'-p','ActiveState','--value').strip()=='active'
    def pid(self,name):return int(self.service('show',name,'-p','MainPID','--value').strip())
    def ui(self):return self.m.get(8783,'/api/state')

    def save_meta(self):atomic_json(self.folder/'session.json',self.meta)

    def capture(self,wrapper):
        assert self.meta is None
        wait_parent_ready(self)
        assert self.active(AUDIO) and self.active(CAMERA)
        assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
        assert digest(CFG)==CFG_SHA and digest(self.m.UNIT)==PARENT_UNIT_SHA
        usb=Path('/sys/bus/usb/devices/1-1.2')
        assert (usb/'idVendor').read_text().strip()=='17ef' and (usb/'idProduct').read_text().strip()=='a03b'
        assert (usb/'devnum').read_text().strip()=='3'
        assert any(part.startswith('1-1.2:') for part in Path('/sys/class/sound/card1/device').resolve().parts)
        h=self.m.camera();validate_parent_state(h);self.m.single_owner(h['pid'])
        assert self.m.runtime_for(h['pid'])==(Path(PARENT_RELEASE)/'aura',Path(PARENT_CONFIG))
        self.assert_idle_or_stopped()
        self.assert_capture_closed()
        cfg=json.loads(CFG.read_text());marker=json.loads(Path(cfg['display_recovery_marker']).read_text())
        assert not cfg.get('startup_display_retrain',False) or all(marker.get(k)==v for k,v in
            {'boot_id':BOOT,'output':cfg['output'],'mode':cfg['mode'],'edid_sha256':cfg['edid_sha256']}.items())
        protected=[CFG,CFG.parent/'launcher.py',Path(PARENT_CONFIG),Path(PARENT_IDENTITY),self.m.BASE/'board_camera_ui.json',self.m.BASE/'board_identity.json',
                   Path('/lib/systemd/system/xserver-nodm.service'),Path('/etc/default/xserver-nodm')]
        protected+=list(Path(cfg['runtime']).glob('avatar*settings.json'))
        protected+=list(Path('/etc/systemd/system/aura-avatar-ui.service.d').glob('*.conf'))
        gui_unit=Path('/etc/systemd/system/aura-avatar-ui.service')
        if gui_unit.exists():protected.append(gui_unit)
        protected+=[self.m.BASE/'aura'/name for name in self.m.BASELINE]
        identity=json.loads((self.m.BASE/'board_identity.json').read_text())
        assert identity['face_backend']['kind']=='dpu_yunet'
        assert identity['feature_backend']=={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}
        for key in ('model','manifest'):
            path=Path(identity['face_backend'][key]);assert digest(path)==identity['face_backend'][key+'_sha256'];protected.append(path)
        for name,sha in self.m.BASELINE.items():assert digest(self.m.BASE/'aura'/name)==sha
        original=(self.folder/'camera.original');original.write_bytes(self.m.UNIT.read_bytes());original.chmod(0o600)
        preference=self.folder/'preference.original';preference.write_bytes(PREF.read_bytes());preference.chmod(0o600)
        self.meta={'boot':BOOT,'wrapper':str(wrapper),'wrapper_sha256':digest(wrapper),
            'protected':{str(p):digest(p) for p in protected},'preference_sha256':digest(PREF),
            'allowed_preference_hashes':[digest(PREF)],'unit_hashes':{'original':digest(original)},
            'runtimes':{'original':str(Path(PARENT_RELEASE)/'aura')},'config':PARENT_CONFIG,
            'configs':{'original':PARENT_CONFIG},
            'gui_dropin_paths':[str(p) for p in Path('/etc/systemd/system/aura-avatar-ui.service.d').glob('*.conf')],
            'xserver_pid':self.pid(XSERVER),'guard':'aura-handoff-restore-'+self.folder.name,
            'initial_camera_pid':h['pid'],'initial_audio_pid':self.pid(AUDIO),'guard_armed':False}
        self.save_meta();self.verify()
        return h

    def verify(self):
        assert self.meta is not None
        assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==self.meta['boot']==BOOT
        for name,sha in self.meta['protected'].items():assert digest(name)==sha,'Protected file changed: '+name
        assert digest(self.m.UNIT) in self.meta['unit_hashes'].values(),'Camera unit changed outside this session'
        assert digest(self.meta['wrapper'])==self.meta['wrapper_sha256']
        assert self.pid(XSERVER)==self.meta['xserver_pid'] and self.active(XSERVER)
        assert digest(PREF) in self.meta['allowed_preference_hashes'],'Preference changed outside owned audio stop'
        if self.meta.get('gui_override'):
            override=Path(self.meta['gui_override'])
            assert not override.is_symlink()
            if override.exists():assert digest(override)==self.meta['gui_override_sha256'],'Owned GUI override changed'
        expected=set(self.meta['gui_dropin_paths'])
        if self.meta.get('gui_override') and Path(self.meta['gui_override']).exists():expected.add(self.meta['gui_override'])
        actual={str(p) for p in Path('/etc/systemd/system/aura-avatar-ui.service.d').glob('*.conf')}
        assert actual==expected,'GUI drop-in set changed outside this transition'

    def assert_idle_or_stopped(self):
        if not self.active(AUDIO):return
        self.m.ui_idle();s=self.ui()
        assert s.get('pending_job') is None and not s.get('playing') and not s.get('paused')
        recording=s.get('local_recording',{})
        assert recording.get('state')=='IDLE' and not recording.get('can_stop')
        assert not s.get('local_transcription',{}).get('service',{}).get('pending')
        pan=s.get('manual_pan',{})
        assert not pan.get('automatic_following') and pan.get('pulse_us') is None

    def assert_capture_closed(self):
        # Enabled-but-waiting is an existing user preference, not an active
        # recording. Preserve it while checking the actual capture state.
        assert not self.ui().get('handsfree_dialogue',{}).get('microphone_open')

    def arm(self):
        self.verify();entry=self.meta['restore_entry']
        self.m.command(['systemd-run','--unit='+self.meta['guard'],'--on-active=600s',
            '--property=RuntimeMaxSec=300','/usr/bin/python3','-B',entry,'--guard'],timeout=10)
        self.meta['guard_armed']=True;self.save_meta();self.assert_guard_armed()

    def assert_guard_armed(self):
        assert self.meta['guard_armed']
        assert self.active(self.meta['guard']+'.timer'),'Independent restore is not armed'

    def stop_audio(self):
        self.verify()
        state=self.service('show',AUDIO,'-p','ActiveState','--value').strip()
        if state=='activating' and self.meta.get('owned_audio_starting'):
            pass  # This transition's not-yet-ready process must also close PCM.
        else:self.assert_idle_or_stopped()
        if state in ('active','activating','reloading'):self.service('stop',AUDIO)
        self.meta['owned_audio_starting']=False;self.save_meta()
        # The application may save its own preference on an orderly stop.
        sha=digest(PREF)
        if sha not in self.meta['allowed_preference_hashes']:
            self.meta['allowed_preference_hashes'].append(sha);self.save_meta()
        assert not self.active(AUDIO)

    def wait_pcm_closed(self):
        paths=[Path('/proc/asound/card1/pcm0p/sub0/status'),Path('/proc/asound/card1/pcm0c/sub0/status')]
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            if not paths[0].exists():raise RuntimeError('MCP01 playback status disappeared')
            if all(not p.exists() or p.read_text().strip()=='closed' for p in paths):
                self.meta['quiescent_cursor']=self.m.kernel_cursor();self.save_meta();return
            time.sleep(.2)
        raise RuntimeError('Owned audio PCM did not close')

    def switch_camera(self,target):
        self.verify();self.wait_pcm_closed()
        data=(self.folder/('camera.'+target)).read_bytes()
        assert hashlib.sha256(data).hexdigest()==self.meta['unit_hashes'][target]
        self.service('stop',CAMERA);assert digest(self.m.UNIT) in self.meta['unit_hashes'].values()
        if self.m.UNIT.read_bytes()!=data:
            self.m.atomic(self.m.UNIT,data);self.service('daemon-reload')
        self.service('start','--no-block',CAMERA)

    def switch_gui(self,target):
        if not self.meta.get('gui_override'):return
        self.verify();assert not self.active(AUDIO)
        path=Path(self.meta['gui_override'])
        if target=='original':
            if path.exists():
                assert digest(path)==self.meta['gui_override_sha256']
                path.unlink();self.service('daemon-reload')
        else:
            source=self.folder/'gui.candidate.conf'
            assert digest(source)==self.meta['gui_override_sha256']
            if not path.exists():
                self.m.atomic(path,source.read_bytes());self.service('daemon-reload')

    def wait_camera(self,target):
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            try:
                h=self.m.camera()
                (validate_parent_state if target=='original' else validate_candidate_state)(h)
                assert self.m.runtime_for(h['pid'])==(Path(self.meta['runtimes'][target]),Path(self.meta['configs'][target]))
                self.m.single_owner(h['pid']);return h
            except Exception:time.sleep(.4)
        raise RuntimeError('Camera target did not become healthy: '+target)

    def restore_preference(self):
        self.verify()
        original=(self.folder/'preference.original').read_bytes()
        assert hashlib.sha256(original).hexdigest()==self.meta['preference_sha256']
        if PREF.read_bytes()!=original:self.m.atomic(PREF,original)

    def start_audio(self):
        self.verify();self.meta['owned_audio_starting']=True;self.save_meta()
        self.service('start','--no-block',AUDIO)

    def wait_audio_ready(self):
        deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            try:
                s=self.ui()
                if self.active(AUDIO) and s.get('audio_output_state')=='IDLE_READY':
                    assert s.get('local_recording',{}).get('state')=='IDLE'
                    assert not s.get('handsfree_dialogue',{}).get('microphone_open')
                    self.meta['owned_audio_starting']=False;self.save_meta()
                    return s
            except Exception:pass
            time.sleep(.5)
        raise RuntimeError('Original audio did not become ready')

    def ready(self,target):
        try:
            self.verify();h=self.m.camera()
            (validate_parent_state if target=='original' else validate_candidate_state)(h)
            assert digest(self.m.UNIT)==self.meta['unit_hashes'][target]
            assert self.m.runtime_for(h['pid'])==(Path(self.meta['runtimes'][target]),Path(self.meta['configs'][target]))
            assert self.active(AUDIO) and self.ui().get('audio_output_state')=='IDLE_READY'
            assert digest(PREF)==self.meta['preference_sha256']
            if self.meta.get('gui_override'):
                override=Path(self.meta['gui_override'])
                assert override.exists()==(target!='original')
                if target!='original':
                    args=(Path('/proc')/str(self.pid(AUDIO))/'cmdline').read_bytes().split(b'\0')
                    assert str(self.meta['gui_launcher']).encode() in args
            return True
        except Exception:return False

    def restore(self):
        with (self.folder/'restore.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            # The guard service is already firing at this point; its timer may
            # no longer be active. Identity/pin checks still apply, but no new
            # independently guarded transition is started.
            class Restoring:
                def __init__(self,parent):self.parent=parent
                def __getattr__(self,name):return getattr(self.parent,name)
                def assert_guard_armed(self):assert self.parent.meta['guard_armed']
            result=transition(Restoring(self),'original')
            assert self.ready('original')
            result.update(restored=True,camera_pid=self.pid(CAMERA),audio_pid=self.pid(AUDIO),
                original_unit_sha256=self.meta['unit_hashes']['original'])
            atomic_json(self.folder/'restore-result.json',result)
            return result

    def disarm(self):
        assert self.ready('original')
        self.service('stop',self.meta['guard']+'.timer')
        self.meta['guard_armed']=False;self.save_meta()


def run_baseline(folder,wrapper):
    ops=BoardOps(folder);report={'scope':'COORDINATED_ORIGINAL_CAMERA_AUDIO_120S','complete':False,'passed':False,'phase':'PREFLIGHT'}
    save=lambda:atomic_json(Path(folder)/'report.json',report)
    save();armed=False
    try:
        report['camera_before']=ops.capture(wrapper);report['audio_before_pid']=ops.pid(AUDIO)
        ops.arm();armed=True;report['phase']='HANDOFF';save()
        transition(ops,'original',force=True)
        cursor=ops.meta['quiescent_cursor'];first=ops.m.camera();first_cpu=ops.m.cpu();started=time.monotonic()
        report['phase']='OBSERVING';report['samples']=[];save()
        for index in range(25):
            h=ops.m.camera();ops.m.healthy(h);ops.m.single_owner(h['pid']);ops.m.ui_idle();ops.verify()
            assert h['pid']==first['pid'] and ops.ready('original')
            warnings=ops.m.audio_warnings(cursor);assert warnings==0,'USB warning during coordinated baseline'
            report['samples'].append({'elapsed_s':time.monotonic()-started,'pid':h['pid'],
                'detected_frames':h['detected_frames'],'capture_frames':h['capture_frames'],
                'dpu_schedule':h['dpu_schedule'],'source_age_ms':h['face_targets']['source_age_ms'],
                'audio_pid':ops.pid(AUDIO),'usb_warnings':warnings})
            report['elapsed_s']=report['samples'][-1]['elapsed_s'];save()
            if index<24:time.sleep(max(0,started+(index+1)*5-time.monotonic()))
        elapsed=time.monotonic()-started;last=ops.m.camera()
        report.update(observed_seconds=elapsed,yolo_hz=(last['detected_frames']-first['detected_frames'])/elapsed,
            yunet_hz=(last['face_targets']['processed']-first['face_targets']['processed'])/elapsed,
            cpu_window=ops.m.cpu_delta(first_cpu,ops.m.cpu()),usb_warning_count=ops.m.audio_warnings(cursor))
        report['passed']=elapsed>=120 and report['yolo_hz']>=9 and report['usb_warning_count']==0
    except Exception as exc:report['error']=type(exc).__name__+': '+str(exc)[:400]
    finally:
        report['phase']='RESTORING';save()
        if armed:
            try:
                result=subprocess.run(['/usr/bin/python3','-B',str(wrapper),'--restore',str(folder)],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=300,text=True)
                assert result.returncode==0,result.stderr[-500:]
                report['restoration']=json.loads(result.stdout)
                assert report['restoration']['restored'];ops.disarm();armed=False
            except Exception as exc:report['restore_error']=type(exc).__name__+': '+str(exc)[:400];report['passed']=False
        report.update(complete=True,phase='FINISHED',guard_left_armed=armed);save()
    return {'root':str(folder),'passed':report['passed'],'complete':True,'guard_left_armed':armed}
