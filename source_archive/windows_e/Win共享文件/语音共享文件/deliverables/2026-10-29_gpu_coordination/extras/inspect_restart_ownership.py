"""Read-only parent helper; never calls ensure(), starts models or stops a PID."""
import hashlib,json,types,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[2]
path=H/'candidate/deliverables/2026-10-18_board_dialogue/project_ollama.py'
module=types.ModuleType('read_only_startup_inspector')
module.__file__=str(P/'deliverables/2026-10-18_board_dialogue/project_ollama.py')
exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),module.__dict__)
owner=module.inspect_ownership();exe=Path(owner['executable'])
with urllib.request.urlopen(module.HOST+'/api/ps',timeout=2) as response:ps=json.load(response)
report={'status':'READ_ONLY_CAPTURED','ownership':owner,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
 'api_version':module.read_version(),'project_residency':ps,
 'process_started_stopped_or_reloaded':False,'configuration_applied':False,
 'notice':'Capture again immediately before parent-controlled restart; PID alone is not ownership evidence'}
(H/'restart_ownership.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='project_residency'}))
