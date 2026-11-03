"""Capture and measure X screen corners privately, with no display changes."""
import base64,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip())
args=Path('/proc/%d/cmdline'%pid).read_bytes().decode().split('\0')
config=json.loads(Path(args[args.index('--config')+1]).read_text())
source=Path(config['runtime'])/'aura/tools/board_screen_capture.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='263348f72cee511a071fd7582d87af7a8df4c2382fa070e11cc0df64f4c3fb89'
with tempfile.TemporaryDirectory(prefix='aura-corner-audit-') as tmp:
 png=Path(tmp)/'screen.png';jpg=Path(tmp)/'screen.jpg'
 subprocess.run([sys.executable,'-B',str(source),str(png)],env=dict(os.environ,DISPLAY=config['display']),check=True,timeout=8)
 from PIL import Image
 with Image.open(png) as original:
  screen=original.convert('RGB');w,h=screen.size;corners={}
  for name,(x,y) in {'top_left':(0,0),'top_right':(w-1,0),'bottom_left':(0,h-1),'bottom_right':(w-1,h-1)}.items():
   row={'pixel':list(screen.getpixel((x,y))),'regions':{}}
   for size in [8,32,80]:
    left=0 if x==0 else w-size;top=0 if y==0 else h-size
    pixels=[screen.getpixel((i,j)) for j in range(top,top+size) for i in range(left,left+size)]
    row['regions'][str(size)]={'dark_pixels':sum(max(p)<32 for p in pixels),'pixels':len(pixels)}
   corners[name]=row
  screen.save(jpg,quality=85)
 raw=jpg.read_bytes();assert len(raw)<160000
 value={'status':'PRIVATE_X_SCREEN_CAPTURE_ONLY','boot_id':boot,'supervisor_pid':pid,'size':[w,h],
  'corners':corners,'physical_panel_verified':False,'display_commands_sent':0,'movement_commands_sent':0,'permanent_files_modified':0,
  'artifacts':{'private-screen.jpg':{'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}}}
 print(json.dumps(value),flush=True)
