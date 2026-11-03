from pathlib import Path
import subprocess,json,os,time
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent.parent
command=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ServerAliveInterval=15','aura-kv260','python3 -u -']
with (ROOT/'data'/'board_numeric.jsonl').open('wb') as out,(ROOT/'data'/'board_ssh_stderr.log').open('wb') as err:
 p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 p.stdin.write((ROOT/'scripts'/'board_monitor.py').read_bytes());p.stdin.close()
receipt={'pid':p.pid,'utc':datetime.now(timezone.utc).isoformat(),'board_writes':False,'model_inference_triggered':False,'command':command,'scope':'Direct human instruction to monitor joint three-minute acceptance; passive only'}
(ROOT/'MONITOR_LAUNCH.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(receipt))
