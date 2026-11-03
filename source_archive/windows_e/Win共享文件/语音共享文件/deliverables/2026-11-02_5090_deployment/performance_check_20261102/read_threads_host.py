import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
helper = HERE.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('threads_transport',helper)
transport = importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
code = r'''
import datetime,json,os,time
from pathlib import Path
PIDS=(79866,97312,97335,138556,205409)
HZ=os.sysconf('SC_CLK_TCK')
def read():
    result={}
    for pid in PIDS:
        root=Path('/proc')/str(pid)
        try:
            stat=(root/'stat').read_text().rsplit(')',1)[1].split()
            parts=(root/'cmdline').read_bytes().split(b'\0')
            entries=[]
            for part in parts:
                try:part=part.decode()
                except UnicodeDecodeError:continue
                if part.startswith('/home/root/aura') and part.endswith('.py'):entries.append(Path(part).name)
                elif part.startswith(('tools.','board.')) and len(part)<120:entries.append(part)
            threads={}
            for task in (root/'task').iterdir():
                try:
                    raw=(task/'stat').read_text().rsplit(')',1)[1].split()
                    threads[task.name]={'birth':int(raw[19]),'ticks':int(raw[11])+int(raw[12]),'name':(task/'comm').read_text().strip()}
                except (OSError,ValueError):continue
            result[str(pid)]={'birth':int(stat[19]),'entry_names':entries,'threads':threads}
        except (OSError,ValueError):continue
    return result
start=time.monotonic();before=read();time.sleep(10);after=read();duration=time.monotonic()-start
rows=[]
for pid,last in after.items():
    first=before.get(pid)
    if not first or first['birth']!=last['birth']:continue
    threads=[]
    for tid,new in last['threads'].items():
        old=first['threads'].get(tid)
        if old and old['birth']==new['birth']:
            threads.append({'tid':int(tid),'name':new['name'],'average_percent_one_core':(new['ticks']-old['ticks'])/HZ/duration*100})
    rows.append({'pid':int(pid),'birth_ticks':last['birth'],'entry_names':last['entry_names'],'top_threads':sorted(threads,key=lambda r:r['average_percent_one_core'],reverse=True)[:8]})
hwmon=[]
for root in Path('/sys/class/hwmon').glob('hwmon*'):
    for temp in root.glob('temp*_input'):
        try:hwmon.append({'sensor':temp.name,'celsius':int(temp.read_text())/1000})
        except (OSError,ValueError):continue
print(json.dumps({'duration_seconds':duration,'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'processes':rows,'hwmon_temperatures':hwmon,'read_only':True,'model_audio_motion_requests':False}))
'''
value=json.loads(transport.ssh('/usr/bin/python3 -B -I -S -',code,timeout=20))
output=HERE/'THREAD_ATTRIBUTION_0918.json'
with output.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(value))
