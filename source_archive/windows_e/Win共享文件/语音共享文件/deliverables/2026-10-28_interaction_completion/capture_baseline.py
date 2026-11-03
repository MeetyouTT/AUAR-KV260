"""Read-only baseline from the effective systemd root; no configuration copies."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
script=r'''
import base64,hashlib,json,re,shlex,subprocess,urllib.request
from pathlib import Path
effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)
args=shlex.split(re.search(r'argv\[\]=(.*?);',effective).group(1))
config=Path(args[args.index('--config')+1]);cfg=json.loads(config.read_text());root=Path(cfg['runtime'])/'aura'
sources={}
for area in ('tools','common','board','tests'):
 for p in (root/area).rglob('*.py'):
  if p.is_symlink() or 'sync-conflict' in p.name:continue
  b=p.read_bytes()
  if len(b)>500000:continue
  sources[p.relative_to(root).as_posix()]=base64.b64encode(b).decode()
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:s=json.load(f)
# Do not copy user utterances, identity gallery or credentials.
summary={k:s.get(k) for k in ('phase','audio_output_state','avatar_renderer','avatar_display','portrait_offload')}
summary['avatar_renderer'].pop('command_results',None)
summary['mechanical']={k:s.get('manual_pan',{}).get(k) for k in ('state','pulse_us','automatic_following')}
summary['listening']=s.get('handsfree_dialogue',{}).get('enabled')
summary['microphone']=s.get('handsfree_dialogue',{}).get('microphone_open')
print(json.dumps(dict(runtime=str(root.parent),startup=str(config.parent),boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
effective=effective,config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),component_sha256=cfg.get('component_sha256',{}),
state=summary,sources=sources)))
'''
v=json.loads(ssh('python3 -B -',script,timeout=40));sources=v.pop('sources')
manifest={}
for name,raw in sources.items():
 p=HERE/'baseline'/name;b=base64.b64decode(raw);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);manifest[name]=hashlib.sha256(b).hexdigest()
v['source_sha256']=manifest
(HERE/'baseline.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
print(json.dumps(dict(runtime=v['runtime'],boot=v['boot'],source_files=len(sources),state=v['state'])))

