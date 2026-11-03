import hashlib,runpy,sys
from pathlib import Path
assert Path('/proc/asound/card1/usbid').read_text().strip().lower()=='17ef:a03b'
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/audio-queue-bound-v1/pcm_progress_readonly.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='04f9af4f1e8cba73899cc9a47cd31b4ee4abf63791ef62f2f9052c26be8567e2'
sys.argv=[str(p),'--pcm-root','/proc/asound/card1/pcm0p/sub0','--seconds','3']
runpy.run_path(str(p),run_name='__main__')
