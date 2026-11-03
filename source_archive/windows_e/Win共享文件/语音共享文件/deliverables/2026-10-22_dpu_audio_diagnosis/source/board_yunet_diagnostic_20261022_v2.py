"""Owned short shadow pilot. Always restore the CURRENT YuNet DPU baseline.

Run only on the reviewed KV260 under root's deployment control. This script is
prepared locally; syntax checks do not constitute a board deployment result.
"""
import argparse
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time
import urllib.request

BASE = Path('/home/root/aura-dpu-vision-20261021/runtime/81fdb11903abb71e-live-134783')
UNIT = Path('/etc/systemd/system/aura-camera-ui.service')
UNIT_SHA = '84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
MODEL_SHA = '12b2ff5c7de157133ebd5aa71665fc5ddcd1f65d9e30e2d6e965e0752e467f25'
BASELINE = {
    'board/identity/camera_faces.py':'9d52d66d0b3fd259d08b3dc669dd5874f54fa4b068efeb01f276fa9fd3caec1c',
    'board/identity/face_targets.py':'d03e2aee39a43f31705494dd679ad4ce7d9b49ddf7bd1185f5e021cdb8990aa0',
    'board/identity/live.py':'5244ba657e5be58d68034b399906b14b6af7980d7d627c671797117e0fe4c57b',
    'board/vision/ui_camera_service.py':'890fea726de2c6d29581ab2ee4c36db5e36df52f3e84ee20cd634fc8961ec2ce',
    'board/vision/dpu_yunet.py':'7ff2b24731692fd7942b02b5375eebd3b68d842e5a1b80678aec830ad727088f',
    'board/vision/dpu_vision_runtime.py':'f5fe60a61eb9c3944d1d64097ce4cc838132a65243f28f011758da9d654dd2e6',
    'board/vision/dpu_vision_schedule.py':'3c88b99d64f59076064436b86c7348616cb640a8cc2de744f1c5ed7c420c97d1'}
OVERLAY = {'board/vision/pipeline_metrics.py': '9f0493d8548d94a9c728782c8d7a0912dcec9aba71f56fe52c90b49a39cc9c03', 'board/vision/dpu_vision_runtime.py': '5c4b97d4a616daa880ad3268e39c484474a08e71b7128b2cacfb8963b04b8277', 'board/vision/dpu_vision_schedule.py': 'acfbe653141d7098e3d87baabfbf7f530efc4309a417babfc76983ad9530dbb2', 'board/vision/ui_camera_service.py': 'e7771f01e0e47e6aa629be74fca74f30803a6ec9ed1a48b97b71de3cc452260f'}


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(args, timeout=20):
    value = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if value.returncode:
        raise RuntimeError('Command failed: '+args[0]+' '+value.stdout.decode(errors='replace')[-500:])
    return value.stdout.decode(errors='replace')


def service(*args):return command(['systemctl']+list(args))


def get(port, route):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:%d%s'%(port,route),timeout=2) as response:return json.load(response)


def camera():
    value=get(8790,'/health')
    result={k:value.get(k) for k in ('pid','capture_frames','detected_frames','capture_hz',
        'detection_hz','observation_age_ms','camera_error','detector_error','dpu_schedule','pipeline_metrics')}
    identity=value.get('identity') or {}
    result.update(identity_backend=identity.get('backend'),face_targets=identity.get('face_targets'),
        shadow=(identity.get('feature_inference') or {}).get('shadow'))
    return result


def face_count():
    return get(8790,'/v1/ui/status').get('modules',{}).get('identity',{}).get('face_count',0)


def ui_idle():
    value=get(8783,'/api/state')
    assert value.get('phase')=='IDLE' and not value.get('playing') and not value.get('paused'), 'GUI is busy'
    assert value.get('local_recording',{}).get('state')!='RECORDING','Recording is active'
    assert not value.get('local_transcription',{}).get('service',{}).get('pending'),'Transcription is pending'
    return {k:value.get(k) for k in ('phase','playing','paused','audio_output_state')}


def runtime_for(pid):
    args=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
    source=next(Path(x.decode()) for x in args if x.endswith(b'/board_camera_motion.py'))
    return source.parent.parent,Path(args[args.index(b'--config')+1].decode())


def single_owner(pid):
    owners=[]
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            if any(x.endswith(b'/board_camera_motion.py') for x in (proc/'cmdline').read_bytes().split(b'\0')):
                owners.append(int(proc.name))
        except OSError:pass
    assert owners==[pid] or sorted(owners)==[pid], 'Unexpected camera processes: '+repr(owners)
    assert int(service('show','aura-camera-ui.service','-p','MainPID','--value').strip())==pid
    lock=Path('/run/aura-person-dpu.lock').stat()
    found=[]
    for line in Path('/proc/locks').read_text().splitlines():
        parts=line.split()
        if len(parts)<6 or parts[1]!='FLOCK' or parts[3]!='WRITE':continue
        dev=parts[5].split(':')
        if (len(dev)==3 and int(dev[0],16)==os.major(lock.st_dev)
                and int(dev[1],16)==os.minor(lock.st_dev) and int(dev[2])==lock.st_ino):found.append(int(parts[4]))
    assert found==[pid], 'DPU process owner lock mismatch: '+repr(found)


def cpu():
    values=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
    return {'mono':time.monotonic(),'total':sum(values),'idle':values[3]+values[4]}


def cpu_delta(first,last):
    total=last['total']-first['total']
    return {'duration_s':last['mono']-first['mono'],
        'cpu_percent_of_board':100*(total-last['idle']+first['idle'])/total if total>0 else None}


def atomic(path,raw):
    path=Path(path);temp=path.with_name(path.name+'.owned-shadow-'+str(os.getpid()))
    with temp.open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    os.replace(str(temp),str(path))


def write_report(root,report):atomic(root/'deployment-result.json',(json.dumps(report,indent=2)+'\n').encode())


def rollback_source(root):
    # An independent timer needs only these backed-up bytes and this script.
    return '''import fcntl,os,subprocess
from pathlib import Path
root=Path(ROOT_VALUE)
lock=(root/'rollback.lock').open('a+')
fcntl.flock(lock,fcntl.LOCK_EX)
unit=Path('/etc/systemd/system/aura-camera-ui.service')
old=(root/'camera.service.original').read_bytes();new=(root/'camera.service.candidate').read_bytes()
assert unit.read_bytes() in (old,new),'Unrelated later camera unit; refusing overwrite'
subprocess.run(['systemctl','stop','aura-camera-ui.service'],check=True,timeout=40)
assert unit.read_bytes() in (old,new),'Unit changed while stopping; refusing overwrite'
temp=unit.with_name(unit.name+'.shadow-rollback-'+str(os.getpid()))
temp.write_bytes(old);os.replace(str(temp),str(unit))
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],check=True,timeout=15)
'''.replace('ROOT_VALUE',repr(str(root)))


def kernel_cursor():
    raw=command(['journalctl','-k','-n','0','--show-cursor','--no-pager'],timeout=5)
    return next(x.split(': ',1)[1] for x in raw.splitlines() if x.startswith('-- cursor: '))


def audio_warnings(cursor):
    raw=command(['journalctl','-k','--after-cursor='+cursor,'-o','json','--no-pager','-n','5000'],timeout=10)
    count=0
    for line in raw.splitlines():
        try:message=json.loads(line).get('MESSAGE','')
        except ValueError:continue
        count+=int('WARN: HC couldn\'t access mem fast enough' in message)
    return count


def healthy(state,shadow=False):
    assert not state['camera_error'] and not state['detector_error'],'Camera/detector error'
    assert state['observation_age_ms'] is not None and state['observation_age_ms']<750,'Primary observation expired'
    assert state['identity_backend']=='WINDOWS_CPU_SFACE_ORT','Primary identity backend changed'
    face=state.get('face_targets') or {}
    assert face.get('backend')=='DPU_YUNET_INT8' and face.get('ready') and not face.get('error'),'YuNet baseline lost'
    jobs=(state.get('dpu_schedule') or {}).get('optional',{})
    for key in ('yunet','sface'):
        job=jobs.get(key,{})
        assert not job.get('disabled') and not job.get('overruns',0),'Optional task overrun: '+key
    if shadow:
        value=state.get('shadow') or {}
        assert value.get('ready') and not value.get('failures') and not value.get('last_error'),'Shadow unavailable'
        assert value.get('mode')=='SHADOW_ONLY_WINDOWS_IDENTITY' and value.get('templates_written')==0


"""Long shadow validation. Prefix with the pinned reviewed pilot library to deploy.

This uses the existing six-file shadow overlay, never the new calibration code.
The only production change is an isolated camera unit, always reverted.
"""
import math


def process_cpu(pid):
    raw=(Path('/proc')/str(pid)/'stat').read_text().rsplit(') ',1)[1].split()
    return {'pid':pid,'ticks':int(raw[11])+int(raw[12]),'start_ticks':int(raw[19]),
            'rss_pages':int(raw[21]),'threads':int(raw[17])}


def measured_cpu(pid):
    value=cpu();value['camera']=process_cpu(pid)
    return value


def measured_delta(first,last):
    value=cpu_delta(first,last);a=first['camera'];b=last['camera']
    assert a['pid']==b['pid'] and a['start_ticks']==b['start_ticks'],'Process changed within CPU window'
    core_seconds=(b['ticks']-a['ticks'])/os.sysconf('SC_CLK_TCK')
    value.update(camera_core_seconds=core_seconds,
        camera_percent_of_board=100*core_seconds/value['duration_s']/os.cpu_count(),
        cpu_count=os.cpu_count(),camera_rss_bytes=b['rss_pages']*os.sysconf('SC_PAGE_SIZE'),
        camera_threads=b['threads'])
    return value


def coverage(samples):
    # A conservative, explicitly sampled estimate, not continuous presence truth.
    seconds=0.;completed=0;accepted=0;yunet=0
    for a,b in zip(samples,samples[1:]):
        if a['face_count']==b['face_count']==1:
            seconds+=b['elapsed_s']-a['elapsed_s']
            completed+=b['shadow']['execution']['completed']-a['shadow']['execution']['completed']
            accepted+=b['shadow']['accepted']-a['shadow']['accepted']
            yunet+=b['dpu_schedule']['optional']['yunet']['calls']-a['dpu_schedule']['optional']['yunet']['calls']
    return {'scope':'5-second intervals with one face at BOTH endpoints; sampled estimate, not continuous coverage',
        'sampled_single_face_seconds':seconds,'sface_completed_in_covered_intervals':completed,
        'sface_accepted_in_covered_intervals':accepted,
        'sface_accepted_hz_in_covered_intervals':accepted/seconds if seconds else None,
        'yunet_hz_in_covered_intervals':yunet/seconds if seconds else None}


def validate_observation(report):
    state=report['camera_after'];shadow=state['shadow'];first=report['samples'][0]
    elapsed=report['observation_elapsed_s']
    yolo=(state['detected_frames']-first['detected_frames'])/elapsed
    yunet=(state['dpu_schedule']['optional']['yunet']['calls']-first['dpu_schedule']['optional']['yunet']['calls'])/elapsed
    complete=shadow['execution']['completed']-first['shadow']['execution']['completed']
    accepted=shadow['accepted']-first['shadow']['accepted']
    cov=coverage(report['samples'])
    report.update(observed_yolo_hz=yolo,observed_yunet_hz=yunet,
        shadow_completed=complete,shadow_accepted=accepted,face_coverage=cov)
    insufficient=[];failures=[]
    if complete<100 or accepted<100:insufficient.append('Fewer than100 actual and target/freshness-accepted SFace completions')
    if cov['sampled_single_face_seconds']<=0:insufficient.append('No single-face intervals at both sampled endpoints')
    if yolo<max(9.,report['baseline_observed_yolo_hz']*.95):failures.append('Primary throughput below preregistered gate')
    if cov['sampled_single_face_seconds']>0:
        if cov['sface_accepted_hz_in_covered_intervals']<.5:failures.append('SFace valid completion rate below0.5Hz in sampled covered intervals')
        if cov['yunet_hz_in_covered_intervals']<1.5:failures.append('YuNet rate below1.5Hz in sampled covered intervals')
    if elapsed<1800:failures.append('Observation shorter than1800s')
    if report['usb_audio_warning_count']!=0:failures.append('USB audio warning')
    if shadow['same_crop_cosine']['count']!=0 or shadow['templates_written'] or shadow['identity_decisions_from_shadow']:
        failures.append('Unexpected identity output or cosine mode')
    if shadow['failures']:failures.append('Shadow computation failure')
    report['stale_results_rejected']=shadow['stale']
    report['coverage_insufficiencies']=insufficient;report['gate_failures']=failures
    report['observation_status']='FAILED' if failures else 'INSUFFICIENT_FACE_COVERAGE' if insufficient else 'PASSED'
    report['passed']=not failures and not insufficient


def main():
    assert os.uname().machine=='aarch64'
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='215c4292-ce84-4828-9827-83c32ba66564'
    patch=Path('/home/root/aura-dpu-vision-20261021/staging/684f232ba4be7e3b/bundle.tar.gz')
    patch_sha='684f232ba4be7e3bdc4b8a5092bdfc527f564f615a78f46c65d80956dcd3b921'
    model=Path('/home/root/aura-dpu-vision-20261021/staging/03580d3216661ba0/kit/sface_public_int8.xmodel')
    manifest_path=model.with_name('sface-manifest.json')
    manifest_sha='d52e4343910f7d3c775405c161e3fdf16db27396891dc617b0e5defdb878841b'
    assert digest(patch)==patch_sha and digest(model)==MODEL_SHA and digest(manifest_path)==manifest_sha
    assert digest(UNIT)==UNIT_SHA,'Baseline unit changed'
    before=camera();baseline_health(before);single_owner(before['pid']);idle=ui_idle()
    config_path=BASE/'board_camera_ui.json';identity_path=BASE/'board_identity.json'
    assert runtime_for(before['pid'])==(BASE/'aura',config_path)
    config=json.loads(config_path.read_text());identity=json.loads(identity_path.read_text())
    assert Path(config['identity']['config'])==identity_path and identity['face_backend']['kind']=='dpu_yunet'
    assert identity['feature_backend']=={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}
    assert identity['model_id']=='sface-2021dec-0ba9fbfa01b5' and 'dpu_sface_shadow' not in identity
    for rel,sha in BASELINE.items():assert digest(BASE/'aura'/rel)==sha
    for key in ('model','manifest'):assert digest(identity['face_backend'][key])==identity['face_backend'][key+'_sha256']
    for private in [identity['database']]+([identity['enrollment_photos']['directory']] if identity.get('enrollment_photos') else []):
        assert (BASE/'aura').resolve() not in Path(private).expanduser().resolve().parents
    original=UNIT.read_bytes()
    ui_pid=service('show','aura-avatar-ui.service','-p','MainPID','--value').strip()
    xserver_pid=service('show','xserver-nodm.service','-p','MainPID','--value').strip()
    protected_paths=[config_path,identity_path]
    for unit_name in ['aura-avatar-ui.service','xserver-nodm.service']:
        path=Path(service('show',unit_name,'-p','FragmentPath','--value').strip())
        assert path.is_absolute() and path.is_file(),'Missing actual service fragment: '+unit_name
        protected_paths.append(path)
    protected={str(p):digest(p) for p in protected_paths}
    root=Path('/home/root/aura-dpu-vision-20261021/yunet-diagnostics')/(patch_sha[:16]+'-'+str(os.getpid()))
    root.mkdir(parents=True,exist_ok=False);candidate=root/'aura'
    with tarfile.open(patch) as archive:
        meta=json.load(archive.extractfile('patch-manifest.json'))
        assert meta['baseline']==BASELINE and set(meta['files'])==set(OVERLAY)
        assert set(archive.getnames())==set(OVERLAY)|{'patch-manifest.json'}
        data={}
        for rel,sha in OVERLAY.items():
            item=archive.getmember(rel);assert item.isfile() and item.size<=131072
            raw=archive.extractfile(item).read()
            assert hashlib.sha256(raw).hexdigest()==sha==meta['files'][rel]['sha256'] and len(raw)==meta['files'][rel]['bytes']
            ast.parse(raw.decode(),filename=rel);data[rel]=raw
    shutil.copytree(BASE/'aura',candidate,ignore=shutil.ignore_patterns('__pycache__','*.sqlite*','*.db'))
    for rel,raw in data.items():
        path=candidate/rel;assert not path.is_symlink();path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    saved=json.loads(json.dumps(identity))
    assert identity==saved and 'dpu_sface_shadow' not in identity
    new_identity=root/'board_identity.json';new_identity.write_text(json.dumps(identity,indent=2)+'\n')
    config['identity']['config']=str(new_identity)
    new_config=root/'board_camera_ui.json';new_config.write_text(json.dumps(config,indent=2)+'\n')
    old=original.decode();assert old.count(str(BASE/'aura'))>=1 and old.count(str(config_path))>=1
    assert old.count('[Service]\n')==1 and 'AURA_DPU_DIAGNOSTICS' not in old
    new=old.replace(str(BASE/'aura'),str(candidate)).replace(str(config_path),str(new_config))
    new=new.replace('[Service]\n','[Service]\nEnvironment=AURA_PIPELINE_METRICS=1 AURA_DPU_DIAGNOSTICS=1\n').encode()
    (root/'camera.service.original').write_bytes(original);(root/'camera.service.candidate').write_bytes(new)
    (root/'rollback.py').write_text(rollback_source(root))
    report={'scope':'YUNET_OPTIONAL_DIAGNOSTIC_120S_ALWAYS_RESTORED',
        'passed':False,'complete':False,'phase':'BASELINE','root':str(root),'baseline_runtime':str(BASE/'aura'),
        'baseline_unit_sha256':UNIT_SHA,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'patch_sha256':patch_sha,'samples':[],'camera_before':before,'ui_before':idle,
        'identity_backend_changed':False,'identity_database_configuration_changed':False,'compare_cosine':False,
        'ui_pid_before':ui_pid,'xserver_pid_before':xserver_pid,
        'measurement_scope':'5-second health snapshots, enabled bounded stage/optional diagnostics and /proc CPU deltas; no XRT collection owned by this script',
        'preregistered_gates':{'seconds':120,'actual_yunet_wait_successes_minimum':3,'yolo_min_hz':9.,
            'formal_identity_accepted':False,'long_run_accepted':False}}
    baseline_initial=camera();baseline_cursor=kernel_cursor()
    baseline_first=measured_cpu(before['pid']);time.sleep(15);baseline_last=measured_cpu(before['pid'])
    baseline_after=camera();baseline_health(baseline_after)
    assert audio_warnings(baseline_cursor)==0,'USB audio already warning in baseline; refuse candidate'
    report['baseline_cpu']=measured_delta(baseline_first,baseline_last)
    report['baseline_observed_yolo_hz']=(baseline_after['detected_frames']-baseline_initial['detected_frames'])/report['baseline_cpu']['duration_s']
    ui_idle();assert UNIT.read_bytes()==original
    for p,sha in protected.items():assert digest(p)==sha
    cursor=kernel_cursor();timer='aura-sface-shadow-rollback-'+str(os.getpid());report['timer']=timer
    command(['systemd-run','--unit='+timer,'--on-active=360s','/usr/bin/python3','-B',str(root/'rollback.py')])
    armed=True
    try:
        service('stop','aura-camera-ui.service');assert UNIT.read_bytes()==original
        atomic(UNIT,new);service('daemon-reload');service('start','--no-block','aura-camera-ui.service')
        deadline=time.monotonic()+35
        while time.monotonic()<deadline:
            try:
                state=camera();report['latest_camera_seen']=state;healthy(state)
                if runtime_for(state['pid'])==(candidate,new_config):break
            except Exception:pass
            time.sleep(.4)
        else:raise RuntimeError('Shadow startup timeout')
        single_owner(state['pid']);started=time.monotonic();cpus=[measured_cpu(state['pid'])]
        report['phase']='OBSERVING';report['camera_pid']=state['pid']
        for index in range(25):
            state=camera();report['latest_camera_seen']=state;healthy(state)
            assert state['pid']==report['camera_pid'],'Camera process changed'
            state['face_count']=face_count();state['elapsed_s']=time.monotonic()-started
            current_cpu=measured_cpu(state['pid']);state['cpu_window']=measured_delta(cpus[-1],current_cpu) if index else None
            cpus.append(current_cpu);report['samples'].append(state)
            report['elapsed_s']=state['elapsed_s'];report['last_yunet_completed']=state.get('pipeline_metrics',{}).get('stages',{}).get('yunet.execute_wait',{}).get('count',0)
            if index%6==0 or index==24:
                assert audio_warnings(cursor)==0,'USB audio warnings returned'
                assert ui_pid==service('show','aura-avatar-ui.service','-p','MainPID','--value').strip(),'UI process changed'
                assert xserver_pid==service('show','xserver-nodm.service','-p','MainPID','--value').strip(),'Xserver process changed'
                write_report(root,report)
            if index<24:time.sleep(max(0,started+(index+1)*5-time.monotonic()))
        report['camera_after']=state;report['observation_elapsed_s']=time.monotonic()-started
        report['pilot_cpu_total']=measured_delta(cpus[0],cpus[-1]);report['usb_audio_warning_count']=audio_warnings(cursor)
        validate_diagnostic(report)
        for p,sha in protected.items():assert digest(p)==sha
        report['phase']='RESTORING'
    except Exception as exc:
        report['error']=type(exc).__name__+': '+str(exc)[:500];report['observation_status']='FAILED'
    finally:
        write_report(root,report)
        try:
            report['rollback_output']=command(['/usr/bin/python3','-B',str(root/'rollback.py')],timeout=70)[-500:]
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                try:
                    restored=camera();healthy(restored)
                    if runtime_for(restored['pid'])==(BASE/'aura',config_path):break
                except Exception:pass
                time.sleep(.4)
            else:raise RuntimeError('YuNet restoration unavailable')
            assert UNIT.read_bytes()==original and not restored.get('shadow')
            single_owner(restored['pid'])
            for p,sha in protected.items():assert digest(p)==sha
            for rel,sha in BASELINE.items():assert digest(BASE/'aura'/rel)==sha
            report['restored']=restored;report['rollback_verified']=True
            service('stop',timer+'.timer');armed=False
        except Exception as exc:
            report['rollback_error']=type(exc).__name__+': '+str(exc)[:500]
            report['rollback_verified']=False;report['passed']=False
        report['rollback_timer_left_armed']=armed
        report['ui_pid_preserved']=ui_pid==service('show','aura-avatar-ui.service','-p','MainPID','--value').strip()
        report['xserver_pid_preserved']=xserver_pid==service('show','xserver-nodm.service','-p','MainPID','--value').strip()
        report['complete']=True;report['phase']='FINISHED';write_report(root,report)
    print(json.dumps({'root':str(root),'passed':report['passed'],'complete':True,
        'status':report.get('observation_status'),'rollback_verified':report['rollback_verified']}),flush=True)


def baseline_health(state):
    assert not state['camera_error'] and not state['detector_error']
    assert state['observation_age_ms'] is not None and state['observation_age_ms']<750
    assert state['identity_backend']=='WINDOWS_CPU_SFACE_ORT' and state.get('shadow') is None
    face=state['face_targets']
    assert face['ready'] and not face['error'] and face['backend'] in ('DPU_YUNET_INT8','CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN')
    usb=Path('/sys/bus/usb/devices/1-1.2')
    assert (usb/'idVendor').read_text().strip()=='17ef' and (usb/'idProduct').read_text().strip()=='a03b'
    assert (usb/'devnum').read_text().strip()=='4','Audio address changed; refuse fixed-boot endpoint observation'

def validate_diagnostic(report):
    first=report['samples'][0];last=report['camera_after'];dt=report['observation_elapsed_s']
    completed=last['pipeline_metrics']['stages']['yunet.execute_wait']['count']
    assert dt>=120 and completed>=3
    assert last.get('shadow') is None and report['usb_audio_warning_count']==0
    assert (last['detected_frames']-first['detected_frames'])/dt>=9.,'Primary throughput below diagnostic gate'
    report.update(passed=True,observation_status='SHORT_DIAGNOSTIC_NO_FAILURE_REPRODUCED',
        diagnostic_completed_waits=completed,formal_identity_or_long_run_accepted=False,
        observed_yolo_hz=(last['detected_frames']-first['detected_frames'])/dt,
        observed_yunet_hz=(last['dpu_schedule']['optional']['yunet']['calls']-first['dpu_schedule']['optional']['yunet']['calls'])/dt)


if __name__=='__main__':
    import sys
    source=Path(sys._getframe().f_code.co_filename).resolve();key=digest(source)[:16]
    launch=Path('/home/root/aura-dpu-vision-20261021/yunet-diagnostic-launches')/key
    launch.mkdir(parents=True,exist_ok=True)
    if os.environ.get('AURA_RUN_YUNET_DIAGNOSTIC')=='1':
        try:
            main();result={'finished':True,'scope':'Read yunet-diagnostics deployment-result.json for actual diagnostic/restoration'}
        except Exception as exc:result={'finished':True,'error':type(exc).__name__+': '+str(exc)[:500]}
        (launch/'launch-result.json').write_text(json.dumps(result,indent=2)+'\n')
    else:
        assert not (launch/'launch-result.json').exists()
        unit='aura-yunet-diagnostic-'+key
        command(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=280',
            '--setenv=AURA_RUN_YUNET_DIAGNOSTIC=1','/usr/bin/python3','-B',str(source)])
        print(json.dumps({'started':True,'unit':unit,'launch_result':str(launch/'launch-result.json')}),flush=True)
