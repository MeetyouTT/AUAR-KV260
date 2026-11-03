"""Capture X screen privately; no modeset or app commands."""
import base64,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='33d0dc5b-27f4-4060-ae25-d2e8e8ddabc3'
pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip())
args=Path('/proc/%d/cmdline'%pid).read_bytes().decode().split('\0')
config=json.loads(Path(args[args.index('--config')+1]).read_text())
source=Path(config['runtime'])/'aura/tools/board_screen_capture.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='263348f72cee511a071fd7582d87af7a8df4c2382fa070e11cc0df64f4c3fb89'
with tempfile.TemporaryDirectory(prefix='aura-display-audit-') as tmp:
    png=Path(tmp)/'screen.png';jpg=Path(tmp)/'screen.jpg'
    subprocess.run([sys.executable,'-B',str(source),str(png)],env=dict(os.environ,DISPLAY=config['display']),check=True,timeout=8)
    from PIL import Image
    with Image.open(png) as image:
        size=list(image.size);image.convert('RGB').save(jpg,quality=75)
    raw=jpg.read_bytes();assert len(raw)<140000
    value=dict(status='PRIVATE_X_SCREEN_CAPTURE_ONLY',size=size,physical_panel_verified=False,
               display_commands_sent=0,movement_commands_sent=0,permanent_files_modified=0,
               artifacts={'private-screen.jpg':dict(base64=base64.b64encode(raw).decode(),sha256=hashlib.sha256(raw).hexdigest())})
    print(json.dumps(value),flush=True)
