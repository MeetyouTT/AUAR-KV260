import hashlib,os,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/attended-reference-1420/attended_follow_window.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='1cb4c9b6d0172814277f470bcc5b9b51eed674d1da5a4c575159db8d595315f4'
os.environ['AURA_ATTENDED_FACE_WINDOW']='30_SECONDS'
runpy.run_path(str(p),run_name='__main__')
