import json,os,time
from pathlib import Path
pids=(450525,450593,450597,450598,450662)
def sample():
    out={}
    for pid in pids:
        proc=Path('/proc')/str(pid)
        try:
            for t in (proc/'task').iterdir():
                s=(t/'stat').read_text().rsplit(') ',1)[1].split()
                out[int(t.name)]={'pid':pid,'name':(t/'comm').read_text().strip(),'ticks':int(s[11])+int(s[12])}
        except OSError:pass
    return out
a=sample();start=time.monotonic();time.sleep(3);b=sample();elapsed=time.monotonic()-start
rows=[]
for tid,row in b.items():
    if tid in a:
        rows.append({'pid':row['pid'],'tid':tid,'name':row['name'],
                     'one_core_percent':100*(row['ticks']-a[tid]['ticks'])/os.sysconf('SC_CLK_TCK')/elapsed})
roles={}
for pid in pids:
    parts=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
    roles[str(pid)]=[Path(x.decode()).name for x in parts if x.endswith(b'.py')]
print(json.dumps({'scope':'THREE_SECOND_GUI_THREAD_LOCALIZATION_NOT_BENCHMARK','duration':elapsed,
                  'roles':roles,'threads':sorted(rows,key=lambda r:-r['one_core_percent'])[:16]}))
