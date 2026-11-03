import sys
sys.argv=['board_shadow_pilot.py', '/home/root/aura-dpu-vision-20261021/staging/d6f06aa970649c9e/bundle.tar.gz', '--patch-sha256', 'd6f06aa970649c9e076ccc916ca0c5c3257dcf79639082dd026fa7e90fed95bc', '--boot', '215c4292-ce84-4828-9827-83c32ba66564', '--model', '/home/root/aura-dpu-vision-20261021/staging/03580d3216661ba0/kit/sface_public_int8.xmodel', '--manifest', '/home/root/aura-dpu-vision-20261021/staging/03580d3216661ba0/kit/sface-manifest.json', '--manifest-sha256', 'd52e4343910f7d3c775405c161e3fdf16db27396891dc617b0e5defdb878841b', '--observe-seconds', '20', '--min-completed', '3']
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
OVERLAY = {
    'board/identity/camera_faces.py':'cbe56a648e41942b2c851fd1337cf48253305264c984580abdd65f24957c2210',
    'board/identity/deferred.py':'99b4a88344c4552a2e231d06fc7485764d096e14190d22fc8f2c96133750c141',
    'board/identity/live.py':'d6bc5093f372cafbd6609a1a7d1258abb05dfb09645ead95246032c5d05f1161',
    'board/identity/model_store.py':'310b4f3290fdf9d07b47800477e8ceb4c7631fbb9e622fac0f8c547a0d1563da',
    'board/identity/sface_shadow.py':'1421cb65fac3bc0d4db9eed52c7b0a76f414a6f2d13cdffeaa121744815691ad',
    'board/vision/dpu_sface.py':'24e295040989ce600285f3d6ce9eabb7010008e59467206dc7a247335f748cfa'}


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
        'detection_hz','observation_age_ms','camera_error','detector_error','dpu_schedule')}
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('patch',type=Path)
    parser.add_argument('--patch-sha256',required=True)
    parser.add_argument('--boot',required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--observe-seconds',type=int,default=15)
    parser.add_argument('--min-completed',type=int,default=3)
    args=parser.parse_args()
    assert 10<=args.observe_seconds<=30 and 3<=args.min_completed<=15
    assert os.uname().machine=='aarch64'
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==args.boot
    assert args.patch.is_absolute() and str(args.patch).startswith('/home/root/aura-dpu-vision-20261021/staging/')
    assert digest(args.patch)==args.patch_sha256 and digest(args.model)==MODEL_SHA
    assert args.model.is_absolute() and args.manifest.is_absolute() and digest(args.manifest)==args.manifest_sha256
    model_manifest=json.loads(args.manifest.read_text())
    dpu=[p for p in model_manifest['partitions'] if p['device']=='DPU']
    assert model_manifest['sha256']==MODEL_SHA and len(dpu)==1 and dpu[0]['fingerprint']=='0x101000056010407'
    assert len(dpu[0]['inputs'])==len(dpu[0]['outputs'])==1
    assert dpu[0]['inputs'][0]['dims']==[1,112,112,3] and dpu[0]['inputs'][0]['fix_point']==7
    assert dpu[0]['outputs'][0]['dims']==[1,128] and dpu[0]['outputs'][0]['fix_point']==5
    assert digest(UNIT)==UNIT_SHA,'Current YuNet service unit changed'
    before=camera();healthy(before);single_owner(before['pid'])
    assert runtime_for(before['pid'])==(BASE/'aura',BASE/'board_camera_ui.json')
    assert face_count()==1,'Require one actual current face before pilot'
    idle=ui_idle()
    config_path=BASE/'board_camera_ui.json';identity_path=BASE/'board_identity.json'
    config=json.loads(config_path.read_text());identity=json.loads(identity_path.read_text())
    assert Path(config['identity']['config'])==identity_path
    assert identity['feature_backend']=={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}
    assert identity['model_id']=='sface-2021dec-0ba9fbfa01b5' and 'dpu_sface_shadow' not in identity
    assert identity['face_backend']['kind']=='dpu_yunet'
    for key in ('model','manifest'):
        assert digest(identity['face_backend'][key])==identity['face_backend'][key+'_sha256']
    for rel,sha in BASELINE.items():assert digest(BASE/'aura'/rel)==sha,'Baseline changed: '+rel
    for private in [identity['database']]+([identity['enrollment_photos']['directory']] if identity.get('enrollment_photos') else []):
        assert (BASE/'aura').resolve() not in Path(private).expanduser().resolve().parents,'Biometric directory inside source; refusing clone'
    original_unit=UNIT.read_bytes()
    ui_pid=service('show','aura-avatar-ui.service','-p','MainPID','--value').strip()
    protected={str(path):digest(path) for path in (config_path,identity_path,
        Path('/etc/systemd/system/aura-avatar-ui.service'),Path('/etc/systemd/system/xserver-nodm.service')) if path.is_file()}
    root=Path('/home/root/aura-dpu-vision-20261021/shadow-pilots')/(args.patch_sha256[:16]+'-'+str(os.getpid()))
    root.mkdir(parents=True,exist_ok=False)
    candidate=root/'aura'
    with tarfile.open(args.patch,'r:gz') as archive:
        manifest=json.load(archive.extractfile('patch-manifest.json'))
        assert manifest['baseline']==BASELINE and set(manifest['files'])==set(OVERLAY)
        assert set(archive.getnames())==set(OVERLAY)|{'patch-manifest.json'}
        data={}
        for rel,sha in OVERLAY.items():
            entry=archive.getmember(rel);assert entry.isfile() and entry.size<=131072
            raw=archive.extractfile(entry).read();meta=manifest['files'][rel]
            assert hashlib.sha256(raw).hexdigest()==sha==meta['sha256'] and len(raw)==meta['bytes']
            ast.parse(raw.decode(),filename=rel);data[rel]=raw
    shutil.copytree(BASE/'aura',candidate,ignore=shutil.ignore_patterns('__pycache__','*.sqlite*','*.db'))
    for rel,raw in data.items():
        path=candidate/rel;assert not path.is_symlink();path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    original_identity=json.loads(json.dumps(identity))
    identity['dpu_sface_shadow']={'enabled':True,'model':str(args.model),'manifest':str(args.manifest),
        'model_sha256':MODEL_SHA,'manifest_sha256':args.manifest_sha256,'max_source_age_ms':1000,
        'interval_ms':1000,'compare_cosine':False}
    assert {k:v for k,v in identity.items() if k!='dpu_sface_shadow'}==original_identity
    new_identity=root/'board_identity.json';new_identity.write_text(json.dumps(identity,indent=2)+'\n')
    config['identity']['config']=str(new_identity)
    new_config=root/'board_camera_ui.json';new_config.write_text(json.dumps(config,indent=2)+'\n')
    old=original_unit.decode();assert old.count(str(BASE/'aura'))>=1 and old.count(str(config_path))>=1
    new=old.replace(str(BASE/'aura'),str(candidate)).replace(str(config_path),str(new_config)).encode()
    (root/'camera.service.original').write_bytes(original_unit);(root/'camera.service.candidate').write_bytes(new)
    (root/'rollback.py').write_text(rollback_source(root))
    report={'scope':'SHORT_REAL_FACE_SFACE_SHADOW_ALWAYS_REVERTED_TO_RETAINED_YUNET',
        'passed':False,'complete':False,'root':str(root),'boot_id':args.boot,'baseline_runtime':str(BASE/'aura'),
        'camera_before':before,'ui_before':idle,'baseline_unit_sha256':UNIT_SHA,
        'patch_sha256':args.patch_sha256,'samples':[],'identity_backend_changed':False,
        'identity_database_configuration_changed':False,'compare_cosine':False}
    first=cpu();time.sleep(5);report['baseline_cpu']=cpu_delta(first,cpu())
    ui_idle();assert UNIT.read_bytes()==original_unit
    for path,sha in protected.items():assert digest(path)==sha
    cursor=kernel_cursor()
    timer='aura-sface-shadow-rollback-'+str(os.getpid());report['timer']=timer
    command(['systemd-run','--unit='+timer,'--on-active=180s','/usr/bin/python3','-B',str(root/'rollback.py')])
    armed=True
    try:
        service('stop','aura-camera-ui.service')
        assert UNIT.read_bytes()==original_unit
        atomic(UNIT,new);service('daemon-reload');service('start','--no-block','aura-camera-ui.service')
        deadline=time.monotonic()+35
        while time.monotonic()<deadline:
            try:
                state=camera();healthy(state,True)
                if runtime_for(state['pid'])==(candidate,new_config):break
            except Exception:pass
            time.sleep(.4)
        else:raise RuntimeError('Cold shadow startup did not become ready')
        single_owner(state['pid'])
        initial=state;started=time.monotonic();cpus=[cpu()]
        for index in range(args.observe_seconds):
            state=camera();healthy(state,True)
            assert state['pid']==initial['pid'],'Camera process changed'
            report['samples'].append(state);cpus.append(cpu())
            time.sleep(max(0,started+index+1-time.monotonic()))
        state=camera();healthy(state,True);cpus.append(cpu())
        elapsed=time.monotonic()-started
        report['camera_after']=state
        report['observed_yolo_hz']=(state['detected_frames']-initial['detected_frames'])/elapsed
        report['observed_yunet_hz']=(state['dpu_schedule']['optional']['yunet']['calls']-initial['dpu_schedule']['optional']['yunet']['calls'])/elapsed
        completed=(state['shadow'].get('execution') or {}).get('completed',0)
        report['shadow_completed']=completed
        report['shadow_accepted']=state['shadow'].get('accepted',0)
        report['pilot_cpu_total']=cpu_delta(cpus[0],cpus[-1])
        comparison=next(p for p in cpus if cpus[-1]['mono']-p['mono']<=5.1)
        report['pilot_cpu_last_5s']=cpu_delta(comparison,cpus[-1])
        report['usb_audio_warning_count']=audio_warnings(cursor)
        assert report['observed_yolo_hz']>=8.5 and report['observed_yunet_hz']>=1.5,'Primary/face throughput below guard'
        assert completed>=args.min_completed and report['shadow_accepted']>=args.min_completed,'Insufficient actual shadow completions'
        assert state['shadow']['same_crop_cosine']['count']==0,'Unexpected cosine mode'
        assert report['usb_audio_warning_count']==0,'USB audio warnings returned'
        assert ui_pid==service('show','aura-avatar-ui.service','-p','MainPID','--value').strip(),'GUI process changed'
        for path,sha in protected.items():assert digest(path)==sha,'Protected config changed'
        report['passed']=True
    except Exception as exc:
        report['error']=type(exc).__name__+': '+str(exc)[:500]
    finally:
        try:write_report(root,report)
        except Exception as exc:report['intermediate_report_error']=type(exc).__name__
        try:
            report['rollback_output']=command(['/usr/bin/python3','-B',str(root/'rollback.py')],timeout=70)[-500:]
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                try:
                    restored=camera();healthy(restored)
                    if runtime_for(restored['pid'])==(BASE/'aura',config_path):break
                except Exception:pass
                time.sleep(.4)
            else:raise RuntimeError('Retained YuNet restoration was not verified')
            assert UNIT.read_bytes()==original_unit
            single_owner(restored['pid'])
            assert not restored.get('shadow'),'Shadow remained after rollback'
            for path,sha in protected.items():assert digest(path)==sha
            for rel,sha in BASELINE.items():assert digest(BASE/'aura'/rel)==sha
            report['restored']=restored;report['rollback_verified']=True
            service('stop',timer+'.timer');armed=False
        except Exception as exc:
            report['rollback_error']=type(exc).__name__+': '+str(exc)[:500]
            report['rollback_verified']=False;report['passed']=False
        report['rollback_timer_left_armed']=armed
        report['ui_pid_preserved']=ui_pid==service('show','aura-avatar-ui.service','-p','MainPID','--value').strip()
        report['complete']=True
        write_report(root,report)
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    import sys
    source=Path(sys._getframe().f_code.co_filename).resolve()
    key=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    launch=Path('/home/root/aura-dpu-vision-20261021/shadow-launches')/key
    launch.mkdir(parents=True,exist_ok=True)
    if os.environ.get('AURA_RUN_SFACE_SHADOW_PILOT')=='1':
        try:
            main()
            result={'finished':True,'scope':'See shadow-pilots result for passed/rollback status'}
        except Exception as exc:
            result={'finished':True,'error':type(exc).__name__+': '+str(exc)}
        (launch/'launch-result.json').write_text(json.dumps(result,indent=2)+'\n')
    else:
        assert not (launch/'launch-result.json').exists(),'Pilot launcher already completed'
        name='aura-sface-shadow-pilot-'+key
        command(['systemd-run','--unit='+name,'--property=RuntimeMaxSec=160','--setenv=AURA_RUN_SFACE_SHADOW_PILOT=1','/usr/bin/python3','-B',str(source)])
        print(json.dumps({'started':True,'unit':name,'launch_result':str(launch/'launch-result.json')}),flush=True)

