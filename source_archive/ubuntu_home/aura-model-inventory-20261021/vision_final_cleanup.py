import json,os,time,urllib.request,subprocess
from pathlib import Path
t=Path('/sys/kernel/tracing');op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def frames():
 with op.open('http://127.0.0.1:8790/health',timeout=4) as r:h=json.load(r)
 return {'pid':h['pid'],'detected_frames':h['detected_frames']}
cu=Path('/sys/devices/platform/axi/axi:zyxclmm_drm/CU.3.auto/stat')
a={'mono':time.monotonic(),'stat':[int(n) for n in cu.read_text().split()],'camera':frames()}
time.sleep(1.5)
b={'mono':time.monotonic(),'stat':[int(n) for n in cu.read_text().split()],'camera':frames()}
probes=[row for row in (t/'uprobe_events').read_text().splitlines() if any(n in row for n in ('aura_optional_','aura_iso_','aura_vart_'))]
instances=[p.name for p in (t/'instances').iterdir() if p.name.startswith(('aura_optional_','aura_iso_','aura_vart_'))]
units=['aura-optional-phase-'+token+'.service' for token in ('ebc84a088a13cd29','f236f677f64d800b','952891a76bc5a46a','28df49bc28aaf09f')]
units+=['aura-optional-phase-cleanup-'+token+'.timer' for token in ('ebc84a088a13cd29','f236f677f64d800b','952891a76bc5a46a','28df49bc28aaf09f')]
states={u:subprocess.check_output(['systemctl','show',u,'-p','ActiveState','--value'],text=True).strip() for u in units}
pid=b['camera']['pid'];nice={p.name:os.getpriority(os.PRIO_PROCESS,int(p.name)) for p in (Path('/proc')/str(pid)/'task').iterdir()}
stopped=(a['stat'][0]==b['stat'][0] and a['camera']['pid']==b['camera']['pid'] and b['camera']['detected_frames']-a['camera']['detected_frames']>=5)
print(json.dumps({'read_only':True,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mono_ns':time.monotonic_ns(),
 'own_uprobe_definitions':probes,'own_instances':instances,'diagnostic_unit_states':states,'thread_nice':nice,
 'cu_statistics_stopped_while_real_frames_progress':stopped,'cu_stop_evidence':{'before':a,'after':b},
 'passed':not probes and not instances and stopped and all(v=='inactive' for v in states.values()) and all(v==0 for v in nice.values())}))
