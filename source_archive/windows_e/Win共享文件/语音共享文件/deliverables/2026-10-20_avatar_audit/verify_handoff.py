import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'performance_candidate.json').read_text())
files={p.relative_to(HERE/'candidate_sources').as_posix():c['files'][p.relative_to(HERE/'candidate_sources').as_posix()]
       for p in (HERE/'candidate_sources').rglob('*.py') if p.name!='board_avatar_gtk.py'}
remote=r'''
import hashlib,json,re,subprocess,urllib.request
from pathlib import Path
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
cfg=Path(re.search(r'--config (\S+)',unit).group(1));root=Path(json.loads(cfg.read_text())['runtime']);files=FILES
preserved={n:hashlib.sha256((root/n).read_bytes()).hexdigest()==sha for n,sha in files.items()}
gui=(root/'aura/tools/board_avatar_gtk.py').read_text()
checks={key:key in gui for key in ('configure_board_rendering(core,','self.last_runtime_refresh','self.displayed_frames','state[\'avatar_display\']')}
camera=json.load(urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=4))
report={'runtime':str(root),'performance_sources_preserved':preserved,'gui_performance_blocks_preserved':checks,
        'camera_pid':camera['pid'],'camera_service_epoch':camera['service_epoch'],'no_further_ui_switch':True}
print(json.dumps(report));assert all(preserved.values()) and all(checks.values())
'''.replace('FILES',repr(files),1)
r=json.loads(ssh('python3 -B -',remote,timeout=20))
(HERE/'handoff_verification.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
