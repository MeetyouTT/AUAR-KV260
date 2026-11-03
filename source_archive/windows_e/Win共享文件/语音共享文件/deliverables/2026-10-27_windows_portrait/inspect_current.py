"""Read the effective UI and small source baseline before building a candidate."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
names=['tools/realtime_controller.py','tools/streaming_controller.py','tools/board_avatar_worker.py','tools/board_avatar_gtk.py',
       'tools/demo_script.py','board/runtime/fsm.py','board/interaction/avatar_player.py','tools/facial_layers.py',
       'tools/native_video.py','tools/native_pixels.py','tools/native_pixels.cpp','config/board_avatar_gtk.json']
script=r'''
import hashlib,json,re,shlex,subprocess,urllib.request
from pathlib import Path
effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths','-p','MainPID','-p','ActiveState'],text=True)
args=shlex.split(re.search(r'argv\[\]=(.*?);',effective).group(1))
config=Path(args[args.index('--config')+1]);cfg=json.loads(config.read_text());root=Path(cfg['runtime'])
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5) as f:s=json.load(f)
sources={n:(root/'aura'/n).read_text() for n in NAMES}
cameras=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        a=(p/'cmdline').read_bytes().decode().split('\0')
        if any('face-source-' in x and x.endswith('/entry.py') for x in a):cameras.append(int(p.name))
    except (OSError,UnicodeError):pass
v={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'effective':effective,'runtime':str(root),
   'startup_config':str(config),'startup_launcher':config.with_name('launcher.py').read_text(),'startup_values':cfg,
   'sources':sources,'source_text_sha256':{n:hashlib.sha256(t.encode()).hexdigest() for n,t in sources.items()},
   'state':{k:s.get(k) for k in ('phase','state','audio_output_state','error','handsfree_dialogue','avatar_display','manual_pan','native_canvas')},
   'camera_pids':sorted(cameras)}
print(json.dumps(v))
'''.replace('NAMES',repr(names))
v=json.loads(ssh('python3 -B -',script,timeout=30))
assert v['state']['phase']=='IDLE' and v['state']['audio_output_state']=='IDLE_READY'
assert v['state']['handsfree_dialogue']['enabled'] is False
for name,source in v.pop('sources').items():
    path=HERE/'original/aura'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(source,encoding='utf-8',newline='\n')
path=HERE/'original/startup';path.mkdir(parents=True,exist_ok=True)
(path/'launcher.py').write_text(v.pop('startup_launcher'),encoding='utf-8')
(path/'config.json').write_text(json.dumps(v['startup_values'],indent=2),encoding='utf-8')
(HERE/'baseline.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:x for k,x in v.items() if k not in ('startup_values','effective','source_text_sha256')}))
