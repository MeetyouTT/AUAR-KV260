"""Read the GUI startup once; wait outside the UART helper if still starting."""
import json,subprocess,urllib.request
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
unit='aura-avatar-ui.service';props=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','SubState','-p','Result'],text=True)
try:
 u=get(8783,'/api/state');m=u['manual_pan'];h=get(8790,'/health')
 value={'phase':'READY' if m['state']=='READY' else 'API_WITH_MANUAL_'+m['state'],'unit':props,'manual':m,'page':u['ui_page'],
  'preview':u['ui_runtime'].get('preview_metrics'),'camera_pid':h['pid'],'identity_ready':h['identity']['ready'],
  'primary':h['dpu_schedule']['primary_period_overruns'],'optional':{k:h['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')}}
except Exception as exc:value={'phase':'WAITING_GUI_STARTUP','unit':props,'reason':type(exc).__name__}
print(json.dumps(value))
