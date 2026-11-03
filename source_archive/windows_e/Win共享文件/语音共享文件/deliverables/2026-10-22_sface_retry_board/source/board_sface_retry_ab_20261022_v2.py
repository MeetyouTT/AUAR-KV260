MERGED_HASHES={'board/identity/calibration_http.py': '42159f8b5a37c8bd0a86628df035d959cfd8ce8558b3433bf6b7b9fd01cfb621', 'board/identity/camera_faces.py': 'd2f5303b8fc4440c5a17ef0306a22a17f4494015bbc93874ca716d9f52f1834e', 'board/identity/deferred.py': '99b4a88344c4552a2e231d06fc7485764d096e14190d22fc8f2c96133750c141', 'board/identity/live.py': '92ff7ea739c92942b37f60158bdbdec517596ce33fcc0113766e8f2a8fff2044', 'board/identity/model_store.py': '310b4f3290fdf9d07b47800477e8ceb4c7631fbb9e622fac0f8c547a0d1563da', 'board/identity/sface_calibration.py': '23a5c619b483e65c7dd152e5a225df55763ac2936dbf5ae717c6ec998fb19e5c', 'board/identity/sface_producer.py': '663ae00fa98888767959c528c3d479a2ba9952d3975ef1a17b897623b3274a8e', 'board/identity/sface_shadow.py': '5ad5071f020d0914a1a153f6992c85d92b7a05580032697f5a1cee036aea88c5', 'board/vision/dpu_sface.py': '24e295040989ce600285f3d6ce9eabb7010008e59467206dc7a247335f748cfa', 'board/vision/dpu_vision_runtime.py': '5c4b97d4a616daa880ad3268e39c484474a08e71b7128b2cacfb8963b04b8277', 'board/vision/dpu_vision_schedule.py': 'acfbe653141d7098e3d87baabfbf7f530efc4309a417babfc76983ad9530dbb2', 'board/vision/pipeline_metrics.py': 'd9ce314b6998f8074777b666c2358522b0b1eb663293847d2eda2a7f7930e3b2', 'board/vision/ui_camera_service.py': 'd0f8251f0310ba67668e23eb60aba06805cebcea8afdd0e29893cc567c56ac50'}
def digest_bytes(raw):return hashlib.sha256(raw).hexdigest()
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
        'detection_hz','observation_age_ms','camera_error','detector_error','dpu_schedule','pipeline_metrics')}
    identity=value.get('identity') or {}
    result.update(identity_backend=identity.get('backend'),face_targets=identity.get('face_targets'),
        shadow=(identity.get('feature_inference') or {}).get('shadow'),
        producer=(identity.get('feature_inference') or {}).get('producer'))
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



DELTA_SHA='82a024c3944aea152237db70fcd936ca100b7a47be6acaed501e4b9b4f57be9e'
DELTA_FILES={'board/identity/deferred.py': 'a09e7e751a8441d7f3be0d52c558ae8687360042872722eb3b3af87b9d24dc01', 'board/identity/sface_shadow.py': '69ae50d51ec325b79e264dc49f61e70d7d578fb1ed4f43f4fcc32235382059b5', 'board/vision/dpu_sface.py': '7bff1b22eaa7e9fd5334c28f210664942f43ba4592ec32cc0750f32f1b239b0b', 'retry-manifest.json': '4defde1c925ac3d9c920ace3c7d4096dc46f6c33b1ec527df8554049517be0d5', 'tests/test_slot_retry.py': '9c5a5243b8d56a75f79c7302585eda45127edf88f77d6a5cf6cb470a22dc9d32', 'tests/test_shadow.py': '22ddd0e11fe1cd7b7df7b4f52b8a52b12ea5adcf2c2198e81ddc7bbbc95a0144', 'tests/bootstrap.py': 'a3ff1d1d9870c4a4d8a645ea6b227c9ff463111a77f133e2fa8c721aacc2478a'}
RETRY_HASHES={'board/identity/calibration_http.py': '42159f8b5a37c8bd0a86628df035d959cfd8ce8558b3433bf6b7b9fd01cfb621', 'board/identity/camera_faces.py': 'd2f5303b8fc4440c5a17ef0306a22a17f4494015bbc93874ca716d9f52f1834e', 'board/identity/deferred.py': 'a09e7e751a8441d7f3be0d52c558ae8687360042872722eb3b3af87b9d24dc01', 'board/identity/live.py': '92ff7ea739c92942b37f60158bdbdec517596ce33fcc0113766e8f2a8fff2044', 'board/identity/model_store.py': '310b4f3290fdf9d07b47800477e8ceb4c7631fbb9e622fac0f8c547a0d1563da', 'board/identity/sface_calibration.py': '23a5c619b483e65c7dd152e5a225df55763ac2936dbf5ae717c6ec998fb19e5c', 'board/identity/sface_producer.py': '663ae00fa98888767959c528c3d479a2ba9952d3975ef1a17b897623b3274a8e', 'board/identity/sface_shadow.py': '69ae50d51ec325b79e264dc49f61e70d7d578fb1ed4f43f4fcc32235382059b5', 'board/vision/dpu_sface.py': '7bff1b22eaa7e9fd5334c28f210664942f43ba4592ec32cc0750f32f1b239b0b', 'board/vision/dpu_vision_runtime.py': '5c4b97d4a616daa880ad3268e39c484474a08e71b7128b2cacfb8963b04b8277', 'board/vision/dpu_vision_schedule.py': 'acfbe653141d7098e3d87baabfbf7f530efc4309a417babfc76983ad9530dbb2', 'board/vision/pipeline_metrics.py': 'd9ce314b6998f8074777b666c2358522b0b1eb663293847d2eda2a7f7930e3b2', 'board/vision/ui_camera_service.py': 'd0f8251f0310ba67668e23eb60aba06805cebcea8afdd0e29893cc567c56ac50'}

import sys

BOOT='215c4292-ce84-4828-9827-83c32ba66564'
ORIGINAL_BUNDLE_SHA='0dd98eee68320ec7fbf5e60832f88360a88272ffa0ff21423eead8bfccee9d33'
MODEL=Path('/home/root/aura-dpu-vision-20261021/staging/03580d3216661ba0/kit/sface_public_int8.xmodel')
MODEL_MANIFEST=MODEL.with_name('sface-manifest.json')
MODEL_MANIFEST_SHA='d52e4343910f7d3c775405c161e3fdf16db27396891dc617b0e5defdb878841b'

def checked_read(archive,name,expected):
    item=archive.getmember(name)
    assert item.isfile() and item.size<=131072
    raw=archive.extractfile(item).read();assert digest_bytes(raw)==expected
    if name.endswith('.py'):ast.parse(raw.decode(),filename=name)
    return raw

def pinned():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert digest(UNIT)==UNIT_SHA
    for name,sha in BASELINE.items():assert digest(BASE/'aura'/name)==sha,name
    assert digest(MODEL)==MODEL_SHA and digest(MODEL_MANIFEST)==MODEL_MANIFEST_SHA
    before=camera();healthy(before);single_owner(before['pid']);ui_idle()
    assert runtime_for(before['pid'])==(BASE/'aura',BASE/'board_camera_ui.json')
    assert before.get('shadow') is None
    return before

def verify_sources(prepared):
    for variant in ('A','B'):
        hashes=MERGED_HASHES if variant=='A' else RETRY_HASHES
        for name,sha in hashes.items():assert digest(Path(prepared[variant]['runtime'])/name)==sha,name
        assert digest(prepared[variant]['config'])==prepared[variant]['config_sha256']
        assert digest(prepared[variant]['identity'])==prepared[variant]['identity_sha256']
        assert digest(prepared[variant]['unit'])==prepared[variant]['unit_sha256']
    for name,sha in prepared['protected'].items():assert digest(name)==sha,name
    for name,pid in prepared['unit_pids'].items():
        assert service('show',name,'-p','MainPID','--value').strip()==pid

def prepare(source,key,root):
    before=pinned()
    root.mkdir(parents=True,exist_ok=False)
    identity=json.loads((BASE/'board_identity.json').read_text())
    assert identity['face_backend']['kind']=='dpu_yunet'
    assert identity['feature_backend']=={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}
    assert 'dpu_sface_shadow' not in identity and 'dpu_sface_producer' not in identity
    for field in ('model','manifest'):
        assert digest(identity['face_backend'][field])==identity['face_backend'][field+'_sha256']
    for name in [identity['database']]+([identity['enrollment_photos']['directory']] if identity.get('enrollment_photos') else []):
        assert (BASE/'aura').resolve() not in Path(name).expanduser().resolve().parents
    protected_paths=[BASE/'board_camera_ui.json',BASE/'board_identity.json',
        Path('/home/root/aura-speech-motion-20261021/de989bf024a9/startup/config.json'),
        Path('/home/root/.local/share/aura/handsfree_dialogue.json')]
    for name in ('aura-avatar-ui.service','xserver-nodm.service'):
        fragment=Path(service('show',name,'-p','FragmentPath','--value').strip())
        assert fragment.is_absolute() and fragment.is_file()
        protected_paths.append(fragment)
    protected={str(p):digest(p) for p in protected_paths}
    prepared={'scope':'PREPARED_ONLY_NOT_DEPLOYED','source':str(source),'source_sha256':digest(source),
        'root':str(root),'boot':BOOT,'original_unit_sha256':UNIT_SHA,'protected':protected,
        'unit_pids':{name:service('show',name,'-p','MainPID','--value').strip()
             for name in ('aura-avatar-ui.service','xserver-nodm.service')},'camera_before':before}
    original=UNIT.read_bytes();(root/'camera.service.original').write_bytes(original)
    original_bundle=Path('/home/root/aura-dpu-vision-20261021/staging')/ORIGINAL_BUNDLE_SHA[:16]/'bundle.tar.gz'
    delta=Path('/home/root/aura-dpu-vision-20261021/staging')/DELTA_SHA[:16]/'bundle.tar.gz'
    assert digest(original_bundle)==ORIGINAL_BUNDLE_SHA and digest(delta)==DELTA_SHA
    a=root/'A';a.mkdir();a_runtime=a/'aura'
    shutil.copytree(BASE/'aura',a_runtime,ignore=shutil.ignore_patterns('__pycache__','*.sqlite*','*.db'))
    with tarfile.open(original_bundle,'r:gz') as archive:
        assert set(archive.getnames())==set(MERGED_HASHES)|{'candidate-manifest.json'}
        for name,sha in MERGED_HASHES.items():
            target=a_runtime/name;target.parent.mkdir(parents=True,exist_ok=True)
            assert not target.is_symlink();target.write_bytes(checked_read(archive,name,sha))
    b=root/'B';b.mkdir();b_runtime=b/'aura'
    shutil.copytree(a_runtime,b_runtime)
    tests=root/'tests';tests.mkdir()
    with tarfile.open(delta,'r:gz') as archive:
        assert set(archive.getnames())==set(DELTA_FILES)
        for name,sha in DELTA_FILES.items():
            raw=checked_read(archive,name,sha)
            target=b_runtime/name if name.startswith('board/') else root/name
            assert not target.is_symlink();target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    for variant in ('A','B'):
        folder=root/variant;runtime=folder/'aura'
        value=json.loads(json.dumps(identity))
        value['dpu_sface_shadow']={'enabled':True,'model':str(MODEL),'manifest':str(MODEL_MANIFEST),
            'model_sha256':MODEL_SHA,'manifest_sha256':MODEL_MANIFEST_SHA,
            'max_source_age_ms':1000,'interval_ms':1000,'compare_cosine':False}
        value['dpu_sface_producer']={'enabled':True,'interval_ms':500}
        if variant=='B':value['dpu_sface_shadow']['slot_retry']={'backoff_ms':25,'max_retries':3}
        assert {k:v for k,v in value.items() if k not in ('dpu_sface_shadow','dpu_sface_producer')}==identity
        new_identity=folder/'board_identity.json';new_identity.write_text(json.dumps(value,indent=2)+'\n')
        config=json.loads((BASE/'board_camera_ui.json').read_text());config['identity']['config']=str(new_identity)
        new_config=folder/'board_camera_ui.json';new_config.write_text(json.dumps(config,indent=2)+'\n')
        updated=original.decode().replace(str(BASE/'aura'),str(runtime)).replace(str(BASE/'board_camera_ui.json'),str(new_config))
        assert updated.count('[Service]\n')==1
        updated=updated.replace('[Service]\n','[Service]\nEnvironment="AURA_PIPELINE_METRICS=1"\nEnvironment="AURA_DPU_DIAGNOSTICS=1"\n').encode()
        new_unit=folder/'camera.service.candidate';new_unit.write_bytes(updated)
        prepared[variant]={'runtime':str(runtime),'config':str(new_config),'identity':str(new_identity),
            'unit':str(new_unit),'unit_sha256':digest(new_unit),'config_sha256':digest(new_config),
            'identity_sha256':digest(new_identity),'slot_retry_enabled':variant=='B'}
    verify_sources(prepared)
    environment=dict(os.environ,PYTHONPATH=str(b_runtime)+':'+str(tests))
    result=subprocess.run(['/usr/bin/python3','-B','-m','unittest','-v','test_slot_retry'],
        cwd=str(tests),env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=25)
    output=result.stdout.decode(errors='replace');(root/'synthetic-tests.txt').write_text(output)
    assert result.returncode==0,output[-4000:]
    assert 'Ran 11 tests' in output and '\nOK\n' in output
    prepared.update(synthetic_test_count=11,synthetic_tests_passed=True,
        synthetic_tests_forbid_dpu_bindings_and_database=True,device_jobs_during_prepare=0)
    verify_sources(prepared);after=pinned()
    assert before['pid']==after['pid'] and after['detected_frames']>before['detected_frames']
    prepared['camera_after']=after
    (root/'prepared.json').write_text(json.dumps(prepared,indent=2)+'\n')
    print(json.dumps({'prepared':True,'root':str(root),'source':str(source),'source_sha256':digest(source),
        'synthetic_tests':11,'production_unchanged':True,'camera_pid':after['pid']}),flush=True)

def rollback_program(prepared):
    return """import fcntl,os,subprocess
from pathlib import Path
root=Path(ROOT_VALUE)
lock=(root/'rollback.lock').open('a+')
fcntl.flock(lock,fcntl.LOCK_EX)
unit=Path('/etc/systemd/system/aura-camera-ui.service')
old=(root/'camera.service.original').read_bytes()
allowed=(old,(root/'camera.service.A').read_bytes(),(root/'camera.service.B').read_bytes())
assert unit.read_bytes() in allowed,'Unrelated unit; refusing overwrite'
subprocess.run(['systemctl','stop','aura-camera-ui.service'],check=True,timeout=40)
assert unit.read_bytes() in allowed,'Unrelated unit while stopping'
temp=unit.with_name(unit.name+'.ab-rollback-'+str(os.getpid()))
with temp.open('xb') as f:f.write(old);f.flush();os.fsync(f.fileno())
os.replace(str(temp),str(unit))
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],check=True,timeout=15)
"""

def run_ab(source,key,root):
    prepared=json.loads((root/'prepared.json').read_text())
    assert prepared['source_sha256']==digest(source) and prepared['synthetic_tests_passed']
    before=pinned();verify_sources(prepared)
    work=root/'runs'/str(os.getpid());work.mkdir(parents=True,exist_ok=False)
    original=(root/'camera.service.original').read_bytes();assert UNIT.read_bytes()==original
    (work/'camera.service.original').write_bytes(original)
    for variant in ('A','B'):(work/('camera.service.'+variant)).write_bytes(Path(prepared[variant]['unit']).read_bytes())
    (work/'rollback.py').write_text(rollback_program(prepared).replace('ROOT_VALUE',repr(str(work))))
    report={'scope':'REAL_FACE_A_B_60S_EACH_ORIGINAL_VS_BOUNDED_SLOT_RETRY',
        'boot':BOOT,'root':str(work),'prepared_root':str(root),'passed':False,'complete':False,
        'phase':'PRECHECK','variants':{},'camera_before':before,'source_sha256':digest(source),
        'original_unit_sha256':UNIT_SHA,'variant_source_sha256':{'A':MERGED_HASHES,'B':RETRY_HASHES},
        'identity_backend_changed':False,'templates_requested':False,'audio_changed':False,
        'min_yolo_hz':9.,'target_yunet_hz':2.,'target_sface_hz':.5,
        'hard_optional_cap_ms':30,'guard_ms':5,'independent_rollback_seconds':420}
    def save():atomic(work/'deployment-result.json',(json.dumps(report,indent=2)+'\n').encode())
    def preserved():
        assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
        verify_sources(prepared);ui_idle()
    def restore():
        result=command(['/usr/bin/python3','-B',str(work/'rollback.py')],timeout=70)
        deadline=time.monotonic()+35;latest=None
        while time.monotonic()<deadline:
            try:
                latest=camera();report['latest_restoration_state']=latest
                healthy(latest)
                if runtime_for(latest['pid'])==(BASE/'aura',BASE/'board_camera_ui.json'):break
            except Exception:pass
            time.sleep(.4)
        else:raise RuntimeError('Original retained camera restoration not verified')
        assert UNIT.read_bytes()==original and latest.get('shadow') is None
        single_owner(latest['pid']);preserved()
        for name,sha in BASELINE.items():assert digest(BASE/'aura'/name)==sha
        return latest
    cursor=kernel_cursor();report['kernel_cursor']=cursor;time.sleep(5)
    assert audio_warnings(cursor)==0,'Baseline has new MCP01 warnings; do not deploy'
    preserved();assert face_count()==1,'One actual face is required before A/B start'
    timer='aura-sface-ab-rollback-'+str(os.getpid());report['timer']=timer
    command(['systemd-run','--unit='+timer,'--on-active=420s','/usr/bin/python3','-B',str(work/'rollback.py')])
    armed=True
    try:
        for variant in ('A','B'):
            stage={'variant':variant,'slot_retry':None if variant=='A' else {'backoff_ms':25,'max_retries':3},
                'complete':False,'functional_passed':False,'samples':[]}
            report['variants'][variant]=stage;report['phase']='STARTING_'+variant;save()
            preserved();assert UNIT.read_bytes()==original
            service('stop','aura-camera-ui.service');assert UNIT.read_bytes()==original
            updated=Path(prepared[variant]['unit']).read_bytes()
            atomic(UNIT,updated);service('daemon-reload');service('start','--no-block','aura-camera-ui.service')
            deadline=time.monotonic()+35;last_error=''
            while time.monotonic()<deadline:
                try:
                    state=camera();stage['latest_camera_seen']=state
                    healthy(state,True)
                    if runtime_for(state['pid'])==(Path(prepared[variant]['runtime']),Path(prepared[variant]['config'])):break
                except Exception as exc:last_error=type(exc).__name__+': '+str(exc)[:180]
                time.sleep(.4)
            else:raise RuntimeError('Variant '+variant+' startup failed: '+last_error)
            single_owner(state['pid']);stage['pid']=state['pid']
            deadline=time.monotonic()+15
            while face_count()!=1:
                if time.monotonic()>=deadline:raise RuntimeError('Actual face unavailable after startup')
                state=camera();healthy(state,True);time.sleep(.3)
            first=camera();healthy(first,True)
            stage['first']=first;started=time.monotonic();first_cpu=cpu()
            report['phase']='OBSERVING_'+variant;save()
            for index in range(13):
                state=camera();stage['latest_camera_seen']=state;save()
                healthy(state,True);assert state['pid']==first['pid']
                assert state['producer']['ready'] and not state['producer']['failures']
                assert state['pipeline_metrics']['enabled']
                assert state['pipeline_metrics']['optional_diagnostics']['enabled']
                state['face_count']=face_count();state['elapsed_s']=time.monotonic()-started
                stage['samples'].append(state);stage['elapsed_s']=state['elapsed_s'];save()
                assert audio_warnings(cursor)==0,'New MCP01 warning during '+variant
                preserved()
                if index<12:time.sleep(max(0,started+(index+1)*5-time.monotonic()))
            elapsed=time.monotonic()-started;last=state;stage['last']=last
            stage['observed_seconds']=elapsed;stage['cpu_window']=cpu_delta(first_cpu,cpu())
            stage['observed_yolo_hz']=(last['detected_frames']-first['detected_frames'])/elapsed
            stage['observed_capture_hz']=(last['capture_frames']-first['capture_frames'])/elapsed
            stage['observed_yunet_hz']=(last['dpu_schedule']['optional']['yunet']['calls']-first['dpu_schedule']['optional']['yunet']['calls'])/elapsed
            stage['sface_completed_window']=last['shadow']['execution']['completed']-first['shadow']['execution']['completed']
            stage['sface_accepted_window']=last['shadow']['accepted']-first['shadow']['accepted']
            stage['sface_hz']=stage['sface_completed_window']/elapsed
            stage['prepared_crops_window']=last['producer']['prepared']-first['producer']['prepared']
            stage['one_face_samples']=sum(s['face_count']==1 for s in stage['samples'])
            stage['source_coverage_ok']=stage['one_face_samples']==13 and stage['prepared_crops_window']>=60
            stage['usb_warnings']=audio_warnings(cursor)
            diagnostic=last['pipeline_metrics']['optional_diagnostics']
            assert elapsed>=60 and stage['observed_yolo_hz']>=9.
            assert not diagnostic['fault_events'] and not diagnostic['diagnostic_errors']
            assert last['shadow']['same_crop_cosine']['count']==0 and last['shadow']['templates_written']==0
            stage['functional_passed']=True;stage['complete']=True
            stage['stage_targets_met']=stage['source_coverage_ok'] and stage['sface_hz']>=.5 and stage['observed_yunet_hz']>=2.
            report['phase']='RESTORING_AFTER_'+variant;save()
            stage['restored']=restore();stage['rollback_verified']=True;save()
            if not stage['source_coverage_ok']:raise RuntimeError('Insufficient eligible face coverage in '+variant)
        a,b=report['variants']['A'],report['variants']['B']
        report['completion_rate_ratio']=b['sface_hz']/a['sface_hz'] if a['sface_hz'] else None
        report['source_coverage_comparable']=a['source_coverage_ok'] and b['source_coverage_ok']
        report['retry_target_met']=b['stage_targets_met']
        report['passed']=report['source_coverage_comparable'] and b['stage_targets_met']
        report['conclusion']='SHORT_AB_TARGET_MET_NOT_LONG_STABILITY' if report['passed'] else 'SHORT_AB_TARGET_NOT_MET'
    except Exception as exc:
        report['error']=type(exc).__name__+': '+str(exc)[:500];report['conclusion']='AB_FAILED_OR_INCOMPLETE'
        try:report['fault_camera_snapshot']=camera()
        except Exception as snapshot_error:report['fault_snapshot_error']=type(snapshot_error).__name__
        save()
    finally:
        report['phase']='FINAL_RESTORATION';save()
        try:
            report['restored']=pinned() if UNIT.read_bytes()==original else restore()
            preserved();report['rollback_verified']=True
            service('stop',timer+'.timer');armed=False
        except Exception as exc:
            report['passed']=False;report['rollback_verified']=False
            report['rollback_error']=type(exc).__name__+': '+str(exc)[:500]
        report['rollback_timer_left_armed']=armed;report['complete']=True;report['phase']='FINISHED';save()
    (root/'latest-run.json').write_text(json.dumps({'root':str(work),'report':str(work/'deployment-result.json'),
        'complete':True,'passed':report['passed'],'rollback_verified':report['rollback_verified']},indent=2)+'\n')
    print(json.dumps({'root':str(work),'passed':report['passed'],'complete':True,
        'rollback_verified':report['rollback_verified'],'conclusion':report.get('conclusion')}),flush=True)

if __name__=='__main__':
    source=Path(sys._getframe().f_code.co_filename).resolve();key=digest(source)[:16]
    root=Path('/home/root/aura-dpu-vision-20261021/sface-retry-ab')/key
    mode=os.environ.get('AURA_SFACE_AB_MODE','prepare')
    if mode=='prepare':prepare(source,key,root)
    elif mode=='run':
        try:run_ab(source,key,root);value={'finished':True}
        except Exception as exc:value={'finished':True,'error':type(exc).__name__+': '+str(exc)[:500]}
        (root/'launch-result.json').write_text(json.dumps(value,indent=2)+'\n')
    else:raise ValueError('Unknown A/B helper mode')
