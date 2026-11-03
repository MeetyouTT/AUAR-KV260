import ast,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
source=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_audio_recover_once.py').read_text()
begin=source.index('def sample(seconds):')
end=source.index('\ndef save(value):',begin)
sample='''def sample(seconds):
    # Bounded journal query; avoid the previous high-rate /dev/kmsg observer.
    text=run(['journalctl','-k','-n','1','--show-cursor','--no-pager'],timeout=6)
    cursor=next(x.split(': ',1)[1] for x in text.splitlines() if x.startswith('-- cursor: '))
    before=cpu();started=time.monotonic();time.sleep(seconds);end=cpu()
    duration=time.monotonic()-started;total=end[0]-before[0];processes=[]
    for pid,v in end[2].items():
        old=before[2].get(pid)
        if old and old[1]==v[1]:processes.append({'pid':int(pid),'name':v[2],
            'cpu_pct_board':100*(v[0]-old[0])/os.sysconf('SC_CLK_TCK')/duration/os.cpu_count()})
    raw=run(['journalctl','-k','--after-cursor='+cursor,'-o','json','--no-pager','-n','5000'],timeout=10)
    rows=[]
    for line in raw.splitlines():
        try:rows.append(json.loads(line))
        except ValueError:pass
    count=sum("HC couldn't access mem fast enough for slot 4 ep 3" in x.get('MESSAGE','') for x in rows)
    return {'seconds':duration,'cpu_pct_board':100*(1-(end[1]-before[1])/float(total)),
        'xhci_warning_count':count,'journal_query_complete':len(rows)<5000,
        'count_scope':'Bounded after-cursor journal window; lower bound if5000 entries reached; no /dev/kmsg reader',
        'processes':sorted(processes,key=lambda x:x['cpu_pct_board'],reverse=True)[:10],
        'camera':camera(),'playback_pcm_status':Path('/proc/asound/card1/pcm0p/sub0/status').read_text().strip()}
'''
source=source[:begin]+sample+source[end:]
source=source.replace("out['after']['kmsg_overruns']==0","out['after']['journal_query_complete']")
source=source.replace("out={'complete':False,'phase':'PREFLIGHT'", "out={'recurrence':'MCP01 fault returned during/after failed three-model long run; cause not attributed','complete':False,'phase':'PREFLIGHT'")
ast.parse(source)
out=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_audio_recover_20261022.py')
if out.exists():assert out.read_text()==source
else:out.write_text(source)
print(json.dumps({'source':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))
