import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
assert hashlib.sha256((root/'gui_trial.py').read_bytes()).hexdigest()=='1ae8e61ac26be070315ba6bf855a01dd792c300396bd80f94d3b72929c08c32f'
sys.path.insert(0,str(root));from gui_trial import restore
args=sys.argv[1:];assert args in ([],['--check'],['--restore'],['--guard'])
print(json.dumps(restore(root,'manual' if args==['--restore'] else 'guard' if args==['--guard'] else 'check')))
