import cv2, json, os, shutil, subprocess
from pathlib import Path
def run(args):
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=12)
        return {'rc':p.returncode, 'output':p.stdout[:5000]}
    except Exception as e:
        return {'error':str(e)}
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'opencv':cv2.__version__, 'api':{x:hasattr(cv2,x) for x in ['FaceDetectorYN','FaceDetectorYN_create','FaceRecognizerSF','FaceRecognizerSF_create']},
    'numpy':__import__('numpy').__version__, 'tools':{x:shutil.which(x) for x in ['curl','wget','scp','sshd','python3']},
    'commands':{' '.join(a):run(a) for a in [['ip','-j','addr'],['ip','-j','route'],['systemctl','is-active','sshd']]},
    'models':[{ 'path':str(p),'bytes':p.stat().st_size} for root in ['/home/root','/usr/share'] for p in Path(root).rglob('*.onnx')][:30]
},indent=2))
