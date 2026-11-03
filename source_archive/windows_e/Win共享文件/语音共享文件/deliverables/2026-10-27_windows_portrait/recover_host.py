"""One-shot independent recovery for the owned renderer outage acceptance test."""
import json,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
if __name__=='__main__':
    time.sleep(8)
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(HERE/'start_host.ps1')],
        capture_output=True,timeout=70,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (HERE/'host_recovery.json').write_text(json.dumps({'status':'READY' if result.returncode==0 else 'FAILED',
        'code':result.returncode,'out':result.stdout.decode('utf-8','replace')[-1000:],'error':result.stderr.decode('utf-8','replace')[-1000:]},indent=2),encoding='utf-8')
