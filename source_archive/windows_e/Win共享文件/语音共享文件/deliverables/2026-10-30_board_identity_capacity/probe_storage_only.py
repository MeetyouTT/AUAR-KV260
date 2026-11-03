"""Complete unaffected SQLite test without importing the failing native runtime."""
import ast,datetime,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
sys.path[:0]=[str(P/'deliverables/2026-10-18_board_dialogue'),str(P/'deliverables/2026-10-29_audio_animation_polish')]
from board_ssh import ssh
from board_guard import capture,same
tree=ast.parse((H/'probe_storage_runtime.py').read_text(encoding='utf-8'))
remote=next(node.value.value for node in tree.body if isinstance(node,ast.Assign)
 and any(isinstance(t,ast.Name) and t.id=='REMOTE' for t in node.targets))
start=remote.index('runtime={}');end=remote.index("parent=Path('/home/root')")
replacement='''runtime=dict(importable=False,native_import_attempt='FAILED_IN_PREVIOUS_ISOLATED_PROCESS',
 error="std::runtime_error: Can't add new modules after the interpreter has been initialized")
try:runtime['package_metadata_version']=importlib.metadata.version('onnxruntime')
except importlib.metadata.PackageNotFoundError:runtime['package_metadata_version']=None
'''
remote=remote[:start]+replacement+remote[end:]
remote=remote.replace("os.nice(19)","os.nice(19)\nresource.setrlimit(resource.RLIMIT_CORE,(0,0))")
assert 'import onnxruntime' not in remote and 'InferenceSession' not in remote
report=dict(status='CHECKING',host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 original_runtime_import_failure_preserved='storage_runtime_probe.json',native_import_retried=False)
try:
 before=capture();assert before['safe'] and not before['mismatches']
 report.update(json.loads(ssh('python3 -B -',remote,timeout=20)))
 after=capture();same(before,after);report['board_safe_unchanged']=True
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'storage_only_probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)
