"""Distinguish a daemon-reloaded next-start unit from the running process entry."""
import json
from recovery_common import H,read,save,ssh,board
current=board();assert current['preflight_ready'];initial=read('baseline.json')['board']
assert current['boot']==initial['boot'] and current['actual_runtime']==initial['actual_runtime']
assert current['pins']==initial['pins'] and current['pan']==initial['pan']
script=r'''
import hashlib,json
from pathlib import Path
pid=PID;args=Path('/proc/'+pid+'/cmdline').read_bytes().decode().split('\0')
assert '--config' in args
path=Path(args[args.index('--config')+1]);config=json.loads(path.read_text())
root=Path(config['runtime'])
bad=[name for name,digest in config['component_sha256'].items() if hashlib.sha256((root/'aura'/name).read_bytes()).hexdigest()!=digest]
print(json.dumps({'pid':pid,'process_arguments':args,'running_config':str(path),
 'running_config_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
 'running_runtime':str(root),'running_pins':config['component_sha256'],'hash_mismatches':bad,
 'read_only':True}))
'''.replace('PID',repr(current['ui_service']['MainPID']))
running=json.loads(ssh('python3 -B -',script,timeout=20));assert not running['hash_mismatches']
assert running['running_runtime']==initial['actual_runtime'] and running['running_pins']==initial['pins']
save('running_entry.json',running);save('validation_board.json',current)
print(json.dumps({'configured_next_start':current['actual_config'],'running_config':running['running_config'],
 'runtime':running['running_runtime'],'pins':len(running['running_pins']),
 'same_runtime_components':True,'board_restart_performed':False,'pan':current['pan'],
 'portrait_offload':current['portrait_offload'],'display':current['display']},ensure_ascii=True))
