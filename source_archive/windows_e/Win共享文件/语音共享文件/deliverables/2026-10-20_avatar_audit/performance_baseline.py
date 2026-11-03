"""Read current deployment and interval CPU/RSS; never capture camera pixels."""
import hashlib,json,os,re,subprocess,time,urllib.request
from pathlib import Path
def get(port,path):
    return json.load(urllib.request.urlopen('http://127.0.0.1:%d%s'%(port,path),timeout=4))
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
config_path=Path(re.search(r'--config (\S+)',unit).group(1))
config=json.loads(config_path.read_text());root=Path(config['runtime'])
names=['aura/tools/facial_layers.py','aura/tools/realtime_facials.py','aura/tools/board_avatar_worker.py',
       'aura/board/interaction/avatar_player.py','aura/tools/board_avatar_gtk.py',
       'deliverables/2026-10-06_avatar_reuse/preview_script.py','aura/tools/pillow_compat.py',
       'aura/scripts/board_ui_startup/launcher.py']
sources={n:(root/n).read_text() for n in names if (root/n).is_file()}
def processes():
    out={}
    for path in Path('/proc').glob('[0-9]*'):
        try:
            stat=(path/'stat').read_text().rsplit(')',1)[1].split()
            cmd=(path/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
            if not cmd:continue
            out[path.name]={'ticks':int(stat[11])+int(stat[12]),'rss_bytes':int(stat[21])*os.sysconf('SC_PAGE_SIZE'),
                            'threads':int(stat[17]),'command':cmd[:500]}
        except (OSError,ValueError):pass
    return out
def compact(s):
    r=s.get('avatar_renderer',{})
    return {**{k:s.get(k) for k in ('phase','asset','index','visual_time','ui_tick_ms')},
            'renderer':{k:r.get(k) for k in ('sequence','render_ms','frame_age_ms')},
            'automatic_enabled':s.get('automatic_conversation',{}).get('enabled')}
camera=get(8790,'/health');before=processes();started=time.monotonic();rows=[]
for _ in range(36):
    try:rows.append(compact(get(8783,'/api/state')))
    except OSError:pass
    time.sleep(.25)
elapsed=time.monotonic()-started;after=processes();hz=os.sysconf('SC_CLK_TCK');cpu=[]
for pid,p in after.items():
    if pid in before:
        cpu.append(dict(p,pid=int(pid),cpu_percent=round((p['ticks']-before[pid]['ticks'])/hz/elapsed*100,2)))
cpu.sort(key=lambda p:p['cpu_percent'],reverse=True)
print(json.dumps({'runtime':str(root),'startup_config':config,'startup_config_path':str(config_path),'unit':unit,
 'sources':sources,'source_hashes':{n:hashlib.sha256(t.encode()).hexdigest() for n,t in sources.items()},
 'launcher':config_path.with_name('launcher.py').read_text(),
 'avatar_config':json.loads((root/'aura/config/board_avatar_gtk.json').read_text()),
 'cpu_interval_seconds':elapsed,'cpu':cpu[:14],'rows':rows,'camera_health':camera,
 'memory':Path('/proc/meminfo').read_text(),'loadavg':Path('/proc/loadavg').read_text(),
 'thermal':{str(p):p.read_text() for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')},
 'cpu_freq':{str(p):p.read_text() for p in Path('/sys/devices/system/cpu').glob('cpu*/cpufreq/scaling_cur_freq')}},ensure_ascii=True))
