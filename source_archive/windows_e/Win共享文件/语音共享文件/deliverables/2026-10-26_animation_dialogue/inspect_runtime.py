"""Read source and metadata only; never export dialogue text, pictures or audio."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
SCRIPT=r'''
import hashlib,json,subprocess,urllib.request
from pathlib import Path
pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
args=Path('/proc/%d/cmdline'%pid).read_bytes().decode().split('\0')
config_path=Path(args[args.index('--config')+1]);config=json.loads(config_path.read_text())
root=Path(config['runtime']).resolve();assert str(root).startswith('/home/root/')
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as r:state=json.load(r)
names=['tools/streaming_controller.py','tools/motion_queue.py','board/runtime/audio/voice_channel.py',
       'tools/board_avatar_worker.py','tools/realtime_controller.py','tools/realtime_facials.py',
       'tools/idle_body_compositor.py','tools/render_performance.py','tools/board_avatar_gtk.py',
       'config/board_avatar_gtk.json']
files={n:(root/'aura'/n).read_text() for n in names if (root/'aura'/n).is_file()}
workers=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        parts=(p/'cmdline').read_bytes().decode().split('\0')
        for part in parts:
            if part.endswith(('/entry.py','/run_face_motion.py','/board_camera_motion.py','/gstreamer_audio_worker.py')):
                workers.append({'pid':int(p.name),'script':part})
    except (OSError,UnicodeError):pass
hf=state.get('handsfree_dialogue',{});barge=state.get('voice_barge_in',{})
public={k:state.get(k) for k in ('phase','audio_output_state','error','playing','streaming_reply','cached_only')}
public.update(handsfree={k:hf.get(k) for k in ('enabled','state','microphone_open')},
              barge={k:barge.get(k) for k in ('listening','continuation_listening')},
              renderer=state.get('avatar_renderer',{}).get('presentation',{}))
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'ui_pid':pid,'runtime':str(root),'startup_config':str(config_path),'state':public,'workers':workers,
    'files':files,'sha256':{n:hashlib.sha256(t.encode()).hexdigest() for n,t in files.items()}}))
'''
value=json.loads(ssh('python3 -B -',SCRIPT,timeout=20))
for name,text in value.pop('files').items():
    path=HERE/'board_before'/name;path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError('Preserve original snapshot')
    path.write_text(text,encoding='utf-8')
(HERE/'runtime_before.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value))
