import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'performance_candidate.json').read_text())
remote="import base64,json\nfrom pathlib import Path\np=Path(%r)\nprint(json.dumps({n:base64.b64encode((p/n).read_bytes()).decode() for n in ['IDLE.png','SPEAKING_NEUTRAL.png','resized.png']}))"%c['stage']
images=json.loads(ssh('python3 -B -',remote,timeout=20));folder=HERE/'verification_images';folder.mkdir(exist_ok=True)
for name,value in images.items():(folder/name).write_bytes(base64.b64decode(value))
print(json.dumps({'files':list(images)}))
