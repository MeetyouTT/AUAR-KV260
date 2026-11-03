import json,os,subprocess,time,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
def cmd(args):return subprocess.check_output(args,timeout=10).decode()
def cpu():
    v=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));ps={}
    for p in Path('/proc').glob('[0-9]*'):
        try:
            a=(p/'stat').read_text().split(') ')[1].split()
            ps[p.name]=(int(a[11])+int(a[12]),int(a[19]),(p/'comm').read_text().strip())
        except (OSError,IndexError):pass
    return sum(v),v[3]+v[4],ps
cursor=next(x.split(': ',1)[1] for x in cmd(['journalctl','-k','-n','0','--show-cursor','--no-pager']).splitlines() if x.startswith('-- cursor: '))
first=cpu();start=time.monotonic();time.sleep(5);end=cpu();elapsed=time.monotonic()-start
rows=[json.loads(x) for x in cmd(['journalctl','-k','--after-cursor='+cursor,'-o','json','--no-pager','-n','5000']).splitlines() if x.strip()]
warn=[r for r in rows if "HC couldn't access mem fast enough" in r.get('MESSAGE','')]
top=[]
for pid,p in end[2].items():
    old=first[2].get(pid)
    if old and p[1]==old[1]:top.append({'pid':int(pid),'name':p[2],'cpu_percent_board':100*(p[0]-old[0])/os.sysconf('SC_CLK_TCK')/elapsed/os.cpu_count()})
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as f:s=json.load(f)
out={'read_only':True,'window_s':elapsed,'journal_rows':len(rows),'window_complete':len(rows)<5000,
 'warning_count':len(warn),'warning_samples':[r.get('MESSAGE') for r in warn[-3:]],
 'cpu_percent_board':100*(1-(end[1]-first[1])/(end[0]-first[0])),
 'top_processes':sorted(top,key=lambda x:x['cpu_percent_board'],reverse=True)[:5],
 'ui':{k:s.get(k) for k in ('phase','playing','paused','audio_output_state')},
 'recording_state':s.get('local_recording',{}).get('state'),
 'transcription_pending':s.get('local_transcription',{}).get('service',{}).get('pending')}
print(json.dumps(out))
