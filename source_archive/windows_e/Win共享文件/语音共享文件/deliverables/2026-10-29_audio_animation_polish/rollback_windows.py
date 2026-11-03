"""Restore only this recorded source transaction and its owned CPU renderer."""
import hashlib,json,os,subprocess,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
r=json.loads((H/'source_installation.json').read_text(encoding='utf-8'))
for name,item in r['files'].items():
    path=(P/name).resolve();path.relative_to(P.resolve())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==item['after'],('Concurrent source change',name)
if (H/'host_process.json').exists():
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(H/'stop_owned_portrait.ps1')],check=True)
for name,item in r['files'].items():
    path=P/name
    if item['before'] is None:path.unlink()
    else:
        raw=(H/'source_backup'/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==item['before']
        temporary=path.with_name(path.name+'.restore-'+uuid.uuid4().hex);temporary.write_bytes(raw);os.replace(temporary,path)
subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(H.parent/'2026-10-27_windows_portrait/start_host.ps1')],check=True)
(H/'windows_rollback.json').write_text(json.dumps({'status':'RESTORED','files':len(r['files']),'only_owned_portrait_restarted':True},indent=2),encoding='utf-8')
