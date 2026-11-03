"""Read-only verification of visible preview, own overlay and stopped motion."""
import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/463c9307');N=R/'gui-face-edge-v5'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def health():
 h=get(8790,'/health');s=h['dpu_schedule']
 return dict(pid=h['pid'],detection_hz=h['detection_hz'],primary=s['primary_period_overruns'],
  optional={k:dict(overruns=s['optional'][k]['overruns'],recovery=s['optional'][k]['recovery']) for k in ('yunet','sface')},fenced=s['owner_fenced'])
before=health();rows=[]
for _ in range(25):
 u=get(8783,'/api/state');v=u['ui_runtime']['preview_metrics'];m=u['manual_pan']
 rows.append(dict(visible=v['frame_visible'],frame=v['frame_reference']['frame_id'],preview_error=v['error'],
  page=u['ui_page'],flags=m['readback']['flags'],lease=m['readback']['lease_left_ms'],width=m['readback']['width_us']))
 time.sleep(.2)
after=health();cfg=json.loads((N/'startup/config.json').read_text())
pins={n:hashlib.sha256((Path(cfg['runtime'])/'aura'/n).read_bytes()).hexdigest()==h for n,h in cfg['component_sha256'].items()}
editor=subprocess.check_output(['systemctl','show','aura-face-zone-editor.service','-p','ActiveState','-p','MainPID','-p','ExecMainStatus'],text=True)
log=subprocess.run(['journalctl','-u','aura-face-zone-editor.service','-n','30','--no-pager','-o','cat'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True).stdout
print(json.dumps(dict(status='READ_ONLY_FINAL_CHECK',before=before,after=after,
 primary_delta=after['primary']-before['primary'],optional_delta={k:after['optional'][k]['overruns']-before['optional'][k]['overruns'] for k in before['optional']},
 camera_same=before['pid']==after['pid'],samples=len(rows),visible=sum(r['visible'] is True for r in rows),
 unique_frames=len({r['frame'] for r in rows}),preview_errors=sum(bool(r['preview_error']) for r in rows),
 stopped_all=all(r['flags']==0 and r['lease']==0 for r in rows),last=rows[-1],
 pins_verified=sum(pins.values()),pins_count=len(pins),pins_mismatch=[n for n,ok in pins.items() if not ok],
 editor=editor,editor_error_lines=[x for x in log.splitlines() if any(t in x for t in ('Traceback','Error:','converter','CRITICAL'))],
 zone=json.loads((R/'face-zone-settings.json').read_text()),motor_writes=0),sort_keys=True))
