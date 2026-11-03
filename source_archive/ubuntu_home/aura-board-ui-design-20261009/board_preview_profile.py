"""Read-only profiling: no screenshot, camera restart, device or model changes."""
import json, os, statistics, subprocess, time, urllib.request
from pathlib import Path

root=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
info=json.loads((root/'launch.json').read_text())
def get(url):
    with urllib.request.urlopen(url,timeout=2) as s:return json.load(s)
health=get('http://127.0.0.1:8790/health')
pids={'gui':info['pid'],'camera':health['pid']}
def cpu():
    result={}
    for key,pid in pids.items():
        stat=(Path('/proc')/str(pid)/'stat').read_text().split(') ')[1].split()
        result[key]=int(stat[11])+int(stat[12])
    return result
before=cpu();start=time.monotonic();rows=[]
first_health=health
for _ in range(120):
    ui=get('http://127.0.0.1:8783/api/state');h=get('http://127.0.0.1:8790/health')
    view=ui['ui_runtime'];ref=view.get('frame_reference')
    rows.append({'t':time.monotonic(),'fid':ref['frame_id'] if ref else None,
        'ui_age_ms':int(time.monotonic()*1000)-ref['captured_mono_ms'] if ref else None,
        'capture_age_ms':h['capture_age_ms'],'inference_age_ms':h['observation_age_ms'],
        'displayed_frames':view.get('preview_metrics',{}).get('displayed_frames'),
        'preview_update_hz':view.get('preview_metrics',{}).get('update_hz'),
        'native_entry_age_ms':view.get('preview_metrics',{}).get('entry_age_ms'),
        'preview_error':view.get('preview_metrics',{}).get('error',''),
        'ui_tick_ms':ui.get('ui_tick_ms'),
        'ui_sequence':ui['sequence'],'frame_visible':view['frame_visible'],'ui_error':ui['error']})
    time.sleep(.05)
elapsed=time.monotonic()-start;after=cpu();hz=os.sysconf('SC_CLK_TCK')
out={'elapsed_s':elapsed,'rows':rows,'pids':pids,'cpu_percent_one_core':
    {k:round((after[k]-before[k])/hz/elapsed*100,1) for k in pids},'health':get('http://127.0.0.1:8790/health')}
def stats(values):
    return {'median':statistics.median(values),'p95':sorted(values)[int(.95*(len(values)-1))],
            'min':min(values),'max':max(values)}
out['ui_frame_age_ms']=stats([r['ui_age_ms'] for r in rows if r['ui_age_ms'] is not None])
seconds=rows[-1]['t']-rows[0]['t']
out['ui_publish_hz']=(rows[-1]['ui_sequence']-rows[0]['ui_sequence'])/seconds
if rows[-1]['displayed_frames'] is not None:
    out['preview_display_hz']=(rows[-1]['displayed_frames']-rows[0]['displayed_frames'])/seconds
out['capture_hz_measured']=(out['health']['capture_frames']-first_health['capture_frames'])/elapsed
out['detection_hz_measured']=(out['health']['detected_frames']-first_health['detected_frames'])/elapsed
if rows[-1]['native_entry_age_ms']:out['native_entry_age_ms']=rows[-1]['native_entry_age_ms']
if rows[-1]['ui_tick_ms'] is not None:out['ui_tick_ms']=stats([r['ui_tick_ms'] for r in rows])
files=sorted(Path(info['evidence']).glob('stage_*.json'),key=lambda p:p.stat().st_mtime_ns)
if files:
    log=json.loads(files[-1].read_text());values=[r['render_ms'] for r in log['samples'][-1000:]]
    out['prior_tick_render_ms']={'samples':len(values),'median':statistics.median(values),
        'p95':sorted(values)[int(.95*(len(values)-1))]}
out['plugins']={}
for name in ('shmsink','shmsrc','souphttpsrc','multipartdemux','jpegdec','ximagesink','appsink'):
    r=subprocess.run(['gst-inspect-1.0','--exists',name],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out['plugins'][name]=r.returncode==0
print(json.dumps(out))
