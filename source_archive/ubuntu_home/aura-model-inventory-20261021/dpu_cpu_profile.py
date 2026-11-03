"""Temporarily enable the XRT driver's CU statistics, sample, then disable them."""
import json,os,time,urllib.request,subprocess
from pathlib import Path
cu=Path('/sys/devices/platform/axi/axi:zyxclmm_drm/CU.3.auto')
assert (cu/'base_paddr').read_text().strip()=='0xa0010000'
assert 'DPUCZDX8G' in (cu/'cu_info').read_text()
def stat():
    t=time.monotonic();v=list(map(int,(cu/'stat').read_text().split()))
    assert len(v)==8
    return {'t':t,'raw':v}
def cpu():
    v=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));ps={}
    for pid in ['1017','1460','1160','1528']:
        try:
            a=Path('/proc/'+pid+'/stat').read_text().split(') ')[1].split();ps[pid]=int(a[11])+int(a[12])
        except OSError:pass
    return time.monotonic(),sum(v),v[3]+v[4],ps
def health():
    with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=2) as r:d=json.load(r)
    return {k:d.get(k) for k in ['pid','detection_hz','detected_frames','camera_error','detector_error']}
out={'cu':str(cu),'stat_field_order':['completed','completed_delta','in_flight','average_submitted_queue','max_submitted_queue','max_running','iops','idle_percent'],'health_before':health(),'stat_before':stat(),'samples':[]}
assert out['stat_before']['raw'][0]==0,'Existing statistics activity; do not replace another collector'
started=False
try:
    out['begin']=(cu/'stats_begin').read_text().strip();started=True
    time.sleep(1.1)
    out['warmup_discarded']=stat();first=cpu();laststat=out['warmup_discarded']
    for i in range(1,16):
        time.sleep(max(0,first[0]+i-time.monotonic()))
        s=stat();s['interval_s']=s['t']-laststat['t'];s['busy_percent']=100-s['raw'][7]
        assert 0<=s['raw'][7]<=100,s
        out['samples'].append(s);laststat=s
    last=cpu();dt=last[0]-first[0];total=last[1]-first[1]
    out['duration_s']=dt;out['cpu_busy_percent']=100*(total-last[2]+first[2])/total
    out['process_cpu_percent_of_board']={pid:100*(n-first[3][pid])/os.sysconf('SC_CLK_TCK')/dt/os.cpu_count() for pid,n in last[3].items() if pid in first[3]}
    out['dpu_busy_percent_weighted']=sum(s['busy_percent']*s['interval_s'] for s in out['samples'])/sum(s['interval_s'] for s in out['samples'])
    out['commands_completed']=laststat['raw'][0]-out['warmup_discarded']['raw'][0]
    out['cu_stat_after']=(cu/'cu_stat').read_text().strip('\0\n')
finally:
    if started:out['end']=(cu/'stats_end').read_text().strip()
out['health_after']=health();out['stat_after_end']=stat()
time.sleep(.25);out['stat_disabled_check']=stat()
out['stats_completion_counter_stopped']=out['stat_after_end']['raw'][0]==out['stat_disabled_check']['raw'][0]
print(json.dumps(out),flush=True)
