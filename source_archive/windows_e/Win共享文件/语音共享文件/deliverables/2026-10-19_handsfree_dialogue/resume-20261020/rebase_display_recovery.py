"""Read the active UI as a new baseline, preserving concurrent render fixes."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import base64,hashlib,json,re,subprocess,urllib.request
from pathlib import Path
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
config=Path(re.search(r'--config (\S+)',unit).group(1));cfg=json.loads(config.read_text());root=Path(cfg['runtime'])
state=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
rows=subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines()
pids=[int(row.split()[0]) for row in rows if str(root)+'/aura/tools/board_avatar_gtk.py' in row]
assert len(pids)==1,pids
pid=pids[0]
env=dict(v.split('=',1) for v in Path('/proc/%d/environ'%pid).read_bytes().decode().split('\0') if '=' in v)
home=Path(env.get('HOME',str(Path.home())))
names=['aura/tools/handsfree_recording.py','aura/tools/board_avatar_gtk.py','aura/board/runtime/audio/attention_gate.py',
 'aura/common/handsfree_settings.py','aura/tools/x11_display_activity.py','aura/tests/framework/test_handsfree_dialogue.py']
prefs={str(p):p.read_text() if p.exists() else None for p in {home/'.local/share/aura/handsfree_dialogue.json',Path('/home/root/.local/share/aura/handsfree_dialogue.json')}}
print(json.dumps({'runtime':str(root),'config':str(config),'ui_unit':unit,'ui_home':str(home),'ui_pid':pid,
 'files':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names if (root/n).exists()},
 'gui':base64.b64encode((root/'aura/tools/board_avatar_gtk.py').read_bytes()).decode(),
 'preferences':prefs,'handsfree':state.get('handsfree_dialogue'), 'renderer':state.get('avatar_renderer')}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=25));gui=base64.b64decode(r.pop('gui')).decode()
# Save exact pre-recovery evidence once; later candidate runs cannot erase it.
for name in ('candidate.json','active_verification.json','tests_log.log','tests_pc.log','smoke.json'):
 p=HERE/name;backup=HERE/('pre_black_screen_'+name)
 if p.exists() and not backup.exists():backup.write_bytes(p.read_bytes())
(HERE/'base_candidate.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
original="'common/handsfree_settings.py')"
assert gui.count(original)==1
gui=gui.replace(original,"'common/handsfree_settings.py','tools/x11_display_activity.py')")
# Initialize before either drawing backend starts.
# The font setup follows source hashes in both supported render versions.
lines=gui.splitlines(keepends=True)
index=next(i for i,l in enumerate(lines) if 'self.font_hash =' in l)
lines[index:index]=['        from tools.x11_display_activity import DisplayActivity\n','        self.display_activity=DisplayActivity()\n']
gui=''.join(lines)
anchor="        handsfree=state.get('handsfree_dialogue',{})"
assert gui.count(anchor)==1
gui=gui.replace(anchor,anchor+"\n        self.display_activity.tick(bool(handsfree.get('enabled') and handsfree.get('visual_bound')\n                                       or automatic.get('enabled') or state.get('playing')))")
target=HERE/'merged_sources/aura/tools/board_avatar_gtk.py';target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(gui,encoding='utf-8',newline='\n')
compile(gui,str(target),'exec')
print(json.dumps({k:r[k] for k in ('runtime','ui_home','ui_pid','preferences','handsfree')}))
