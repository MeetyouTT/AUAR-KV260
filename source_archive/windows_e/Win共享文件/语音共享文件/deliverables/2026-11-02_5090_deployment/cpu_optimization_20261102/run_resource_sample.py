"""Reuse the reviewed passive CPU observer for each named optimization stage."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--stage',choices=('before','gtk_after','combined_after','joint'),required=True)
parser.add_argument('--seconds',type=int,choices=(40,120),default=40)
parser.add_argument('--owners',type=Path)
parser.add_argument('--label',help='Unique output label for a new boot or repeated controlled run')
args=parser.parse_args()
label=args.label or args.stage
assert re.fullmatch('[a-z][a-z0-9_]{0,39}',label)
if args.label:assert args.owners is not None,'Fresh owner receipt required for labelled runs'
source=(HERE.parent/'performance_check_20261102/collect_board_performance.py').read_text(encoding='utf-8')
assert 'for index in range(21):' in source and 'INTERVAL = 2.0' in source
if args.seconds==120:source=source.replace('for index in range(21):','for index in range(61):')
if args.owners:
    expected=json.loads(args.owners.read_text(encoding='utf-8'))
else:
    handoff=json.loads((HERE/'AXIS_COORDINATION_HANDOFF.json').read_text(encoding='utf-8'))
    owners=handoff['owners']
    expected={'camera_pid':owners[2]['pid'],'gui_pid':owners[0]['pid'],'gtk_pid':owners[1]['pid']}
assert set(expected)=={'camera_pid','gui_pid','gtk_pid'} and all(type(x) is int and x>0 for x in expected.values())
code='EXPECTED = '+repr(expected)+'\n'+source
helper=HERE.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('resource_sample_transport',helper)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
output=HERE/('RESOURCE_'+label+'.json');assert not output.exists()
host_started=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=json.loads(module.ssh('/usr/bin/python3 -B -I -S -',code,timeout=args.seconds+20))
with output.open('x',encoding='utf-8') as stream:
    json.dump({'stage':args.stage,'run_label':label,'host_started_utc':host_started,
        'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'time_basis':'Host UTC for chronology; board monotonic for durations; board wall-clock UTC may be unsynchronised',
        'collector_sha256_lf':hashlib.sha256(code.encode()).hexdigest(),'board_result':result},stream,indent=2)
    stream.write('\n')
print(json.dumps({'stage':args.stage,'run_label':label,'output':str(output),'duration_s':result['duration_seconds'],
    'startup_sha256':result['startup_before_sha256'],
    'startup_unchanged':result['startup_before_sha256']==result['startup_after_sha256']}))
