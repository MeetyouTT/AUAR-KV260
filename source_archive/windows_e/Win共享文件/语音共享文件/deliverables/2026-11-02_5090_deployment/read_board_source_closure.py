"""Read-only installed GUI source closure and fixed startup-failure indicators."""
import hashlib
import json
import re
from pathlib import Path

business = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
config_path = business / 'startup/config.json'
raw = config_path.read_bytes()
config = json.loads(raw)
runtime = Path(config['runtime'])
components = config.get('component_sha256', {})
issues = []
for relative, expected in components.items():
    path = (runtime / 'aura' / relative).resolve()
    if not path.is_relative_to((runtime / 'aura').resolve()) or path.suffix in ('.sqlite', '.sqlite3', '.db'):
        raise RuntimeError('Unexpected source-closure target')
    try:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        issues.append(dict(path=relative, error=type(error).__name__))
        continue
    if actual != expected:
        issues.append(dict(path=relative, error='sha256_differs'))
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
failure_flags = {}
trace_metadata = {}
try:
    launch = json.loads((runtime / 'launch.json').read_bytes())
    log = Path(launch['log']).resolve()
    if launch['boot_id'] == boot and log.is_relative_to((runtime / 'managed-runs').resolve()):
        with log.open('rb') as stream:
            stream.seek(max(0, log.stat().st_size - 16000))
            tail = stream.read(16000).decode('utf-8', errors='replace')
        failure_flags = {phrase: phrase.lower() in tail.lower() for phrase in
            ('MCP01', 'audio hardware', 'not ready', 'clock', 'rollback',
             'model_inference', 'Connection refused', 'Traceback', 'ImportError')}
        trace_metadata = dict(
            exception_classes=re.findall(r'(?m)^([A-Za-z_]\w*(?:Error|Exception)):', tail),
            frames=[dict(path=path, line=int(line), function=function) for path, line, function in
                    re.findall(r'File "(/[^"\n]+)", line (\d+), in ([A-Za-z_]\w*)', tail)])
except (OSError, ValueError, KeyError):
    pass
print(json.dumps(dict(boot_id=boot, startup_config_sha256=hashlib.sha256(raw).hexdigest(),
    runtime=str(runtime), components_checked=len(components), issues=issues,
    source_closure_passed=len(components) == 380 and not issues,
    current_boot_startup_failure_indicators=failure_flags,
    current_boot_trace_metadata=trace_metadata,
    database_opened=False, services_changed=False, audio_or_motion_requested=False)))
