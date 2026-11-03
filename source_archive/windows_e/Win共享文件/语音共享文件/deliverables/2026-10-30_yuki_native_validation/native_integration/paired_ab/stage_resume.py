"""Stage the explicit public-source delta; no production paths or services."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time,zipfile
from fixture_identity import process_identity

ab=Path(__file__).parent;phase=ab.parent;base=phase.parent
sys.path.insert(0,str(base));import board_ops
state=json.loads((ab/'isolated-host-state.json').read_text())
assert process_identity(state['pid'])==state['identity']
ready=Path(state['ready_file']);deadline=time.monotonic()+15
while not ready.exists() and time.monotonic()<deadline:time.sleep(.2)
assert ready.exists(),'Independent fixture did not become ready; inspect its own log'
proof=json.loads(ready.read_text());assert proof['pid']==state['pid'] and proof['status']=='READY_INDEPENDENT_PROCESS'
assert proof['isolated_port'] not in (8796,proof['production_port'])
proof['windows_process_identity']=state['identity']
(ab/'isolated-server-proof.json').write_text(json.dumps(proof,indent=2))
grant=base.parent/'2026-10-30_board_owner/coordination/runtime_windows.json'
boot=json.loads((ab/'fresh-baseline.json').read_text())['boot_id']
subprocess.run([sys.executable,str(ab/'seal_resume_plans.py'),'--boot-id',boot,'--grant',str(grant)],check=True)
files=['board_source/manifest.json','paired_ab/fresh-baseline.json','paired_ab/isolated-server-proof.json',
       'paired_ab/paired_renderer_harness.py','paired_ab/old_renderer_harness.py','paired_ab/old_harness_support.py',
       'paired_ab/telemetry.py','paired_ab/run_suite.py','paired_ab/prepare_yuki_root.py',
       'paired_ab/resource-window-grant-resume.json','paired_ab/harness-delivery-nojpeg-v2.json',
       'paired_ab/suite-control-pilot-resume-v2.json','paired_ab/suite-formal-resume-v2.json']
archive=ab/'resume-v2-source-delta.zip';hashes={}
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
    for relative in files:
        data=(phase/relative).read_bytes();name='native_integration/'+relative
        hashes[name]=hashlib.sha256(data).hexdigest();output.writestr(name,data)
    output.writestr('resume-v2-source-delta-sha256.json',json.dumps(hashes,indent=2))
remote=board_ops.REMOTE
board_ops.copy_file(str(archive),'root@192.168.50.2:'+remote+'/resume-v2-source-delta.zip')
script=f'''from pathlib import Path
import hashlib,json,zipfile
root=Path({remote!r}).resolve(strict=True)
with zipfile.ZipFile(root/'resume-v2-source-delta.zip') as archive:
 hashes=json.loads(archive.read('resume-v2-source-delta-sha256.json'))
 for name,h in hashes.items():
  assert name.startswith('native_integration/') and '..' not in Path(name).parts
  target=(root/name).resolve(strict=False);assert target.is_relative_to(root/'native_integration')
  data=archive.read(name);assert hashlib.sha256(data).hexdigest()==h
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
print(json.dumps(dict(status='ISOLATED_SOURCE_DELTA_VERIFIED',files=len(hashes),production_modified=False)))
'''
print(board_ops.ssh('python3 -',script,timeout=20))
print(json.dumps(dict(fixture_pid=proof['pid'],isolated_port=proof['isolated_port'],boot_id=boot,staged_files=len(files),archive_bytes=archive.stat().st_size)))
