"""Independent one-shot recovery; only this owned CPU portrait service."""
import json,subprocess,time
from pathlib import Path
H=Path(__file__).resolve().parent
time.sleep(8)
r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(H/'start_host.ps1')],
 capture_output=True,timeout=70,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
(H/'host_recovery.json').write_text(json.dumps(dict(status='READY' if r.returncode==0 else 'FAILED',code=r.returncode,
 out=r.stdout.decode('utf-8','replace')[-1000:],error=r.stderr.decode('utf-8','replace')[-1000:]),indent=2),encoding='utf-8')
