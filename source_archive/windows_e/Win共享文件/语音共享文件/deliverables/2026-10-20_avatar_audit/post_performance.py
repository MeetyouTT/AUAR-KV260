"""Measure actual optimized UI, without injecting a dialogue or changing motion."""
import json,os,subprocess,time,urllib.request
from pathlib import Path
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:%d%s'%(port,path),timeout=4))
def processes():
 out={}
 for path in Path('/proc').glob('[0-9]*'):
  try:
   fields=(path/'stat').read_text().rsplit(')',1)[1].split()
   cmd=(path/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
   if cmd:out[path.name]={'ticks':int(fields[11])+int(fields[12]),'rss_bytes':int(fields[21])*os.sysconf('SC_PAGE_SIZE'),'command':cmd[:500]}
  except (OSError,ValueError):pass
 return out
rows=[];before=processes();started=time.monotonic()
for _ in range(100):
 s=get(8783,'/api/state')
 rows.append({k:s.get(k) for k in ('phase','asset','index','visual_time','ui_tick_ms','avatar_renderer','avatar_display','handsfree_dialogue')})
 time.sleep(.25)
elapsed=time.monotonic()-started;after=processes();hz=os.sysconf('SC_CLK_TCK');cpu=[]
for pid,p in after.items():
 if pid in before:cpu.append(dict(p,pid=int(pid),cpu_percent=round((p['ticks']-before[pid]['ticks'])/hz/elapsed*100,2)))
cpu.sort(key=lambda p:p['cpu_percent'],reverse=True)
first,last=rows[0],rows[-1];span=last['visual_time']-first['visual_time']
fps=(last['avatar_renderer']['sequence']-first['avatar_renderer']['sequence'])/span
display_span=last['avatar_display']['at']-first['avatar_display']['at']
display_fps=(last['avatar_display']['frames']-first['avatar_display']['frames'])/display_span
print(json.dumps({'rows':rows,'render_fps':fps,'gtk_submit_fps':display_fps,'interval_seconds':elapsed,'cpu':cpu[:10],
 'memory':Path('/proc/meminfo').read_text(),'camera_health':get(8790,'/health'),
 'unit':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ActiveState,MainPID,ExecStart'],text=True)},ensure_ascii=True))
