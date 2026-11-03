"""Build an isolated board test bundle, never a production camera deployment."""
import base64,hashlib,io,json,zipfile
from pathlib import Path

job=Path(__file__).resolve().parent
aura=Path('/home/ghmd/Win共享文件/语音共享文件/aura')
names=['common/motion_observation.py','board/motion/__init__.py','board/motion/camera_feed.py',
       'board/motion/follow.py','board/motion/vsrv_driver.py','tools/board_camera_motion.py',
       'tools/board_pan_follow.py','config/pan_follow.shadow.json','tests/framework/test_pan_follow.py']
buffer=io.BytesIO();manifest=[]
with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as archive:
 for name in names:
  raw=(aura/name).read_bytes();archive.writestr(name,raw)
  manifest.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
payload=buffer.getvalue();digest=hashlib.sha256(payload).hexdigest()
source=r'''
import base64,contextlib,hashlib,importlib,importlib.util,io,json,os,subprocess,sys,time,unittest,zipfile
from pathlib import Path
assert os.uname().machine=='aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
def pids():
 return {name:subprocess.check_output(['systemctl','show',name,'-p','MainPID','--value'],text=True).strip() for name in ['aura-camera-ui.service','aura-avatar-ui.service']}
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();before=pids()
firmware=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes()
working=Path(subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','WorkingDirectory','--value'],text=True).strip())
camera_source=working/'board/vision/ui_camera_service.py';camera_sha=hashlib.sha256(camera_source.read_bytes()).hexdigest()
data=base64.b64decode(PAYLOAD_VALUE);assert hashlib.sha256(data).hexdigest()==DIGEST_VALUE
root=Path('/home/root/aura-pan-follow-20261019')/('test-'+DIGEST_VALUE[:16]);root.mkdir(parents=True,exist_ok=True)
stage=root/'aura';stage.mkdir(exist_ok=True)
with zipfile.ZipFile(io.BytesIO(data)) as archive:
 for item in MANIFEST_VALUE:
  raw=archive.read(item['path']);assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
  path=stage/item['path'];path.parent.mkdir(parents=True,exist_ok=True)
  if path.exists():assert path.read_bytes()==raw
  else:
   with path.open('xb') as stream:stream.write(raw)
# Resolve the actual camera module; add only the new motion/contract namespaces.
# This is a separate test process, not an injection into the running service.
sys.path.insert(0,str(working))
import board,common
board.__path__=[str(stage/'board')]+list(board.__path__);common.__path__=[str(stage/'common')]+list(common.__path__)
import board.motion
board.motion.__path__=[str(stage/'board/motion')]+list(board.motion.__path__)
spec=importlib.util.spec_from_file_location('pan_test_suite',str(stage/'tests/framework/test_pan_follow.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert Path(sys.modules['board.vision.ui_camera_service'].__file__).resolve()==camera_source.resolve()
log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
run_root=root/('run-'+str(time.monotonic_ns()));run_root.mkdir()
(run_root/'board-tests.log').write_text(log.getvalue())
fixture=run_root/'replay.jsonl'
with fixture.open('x') as stream:
 for i in range(90):
  x=280. if i<15 or i>=75 else 120. if i<45 else 440.
  packet=module.packet(i+1,1000+i*100,x=x,source_kind='fixture')
  stream.write(json.dumps({'observation':packet,'received_mono_ms':1050+i*100})+'\n')
spec=importlib.util.spec_from_file_location('pan_shadow_cli',str(stage/'tools/board_pan_follow.py'))
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
sys.argv=['board_pan_follow.py','--config',str(stage/'config/pan_follow.shadow.json'),'--replay',str(fixture),
          '--boot-id','boot','--output',str(run_root/'shadow.jsonl')]
with contextlib.redirect_stdout(io.StringIO()):rc=cli.main()
summary=json.loads((run_root/'shadow.jsonl.summary.json').read_text())
assert result.wasSuccessful() and rc==0
assert before==pids() and boot==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert firmware==Path('/proc/device-tree/fpga-full/firmware-name').read_bytes()
assert camera_sha==hashlib.sha256(camera_source.read_bytes()).hexdigest()
report={'status':'PASS_BOARD_SOFTWARE_TESTS_NO_LIVE_MOTION_FEED_OR_PWM','tests_run':result.testsRun,
 'test_errors':len(result.errors),'test_failures':len(result.failures),'actual_camera_source_used':str(camera_source),
 'actual_camera_sha256':camera_sha,'production_pids_unchanged':before,'boot_id_unchanged':boot,
 'firmware_name_unchanged':firmware.rstrip(b'\0').decode(),'physical_actuation':False,
 'live_camera_feed_installed':False,'camera_opened_by_test':False,'fixture_replay':summary,'run_root':str(run_root)}
(run_root/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
'''
source=source.replace('PAYLOAD_VALUE',repr(base64.b64encode(payload).decode())).replace('DIGEST_VALUE',repr(digest)).replace('MANIFEST_VALUE',repr(manifest))
path=job/'board_pan_software_suite.py';path.write_text(source)
(job/'pan-source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'helper':str(path),'source_files':len(manifest),'zip_bytes':len(payload),'sha256':digest}))
