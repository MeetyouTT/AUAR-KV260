"""Run the reviewed read-only metadata probe against the current pinned board."""
import hashlib
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[4]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

if __name__=='__main__':
    label=sys.argv[1]
    assert re.fullmatch('[a-z][a-z0-9_]{0,40}',label)
    source=HERE.parent/'memory_health_collaboration/v14_validation_candidate/board_readonly_metadata_v14.py'
    raw=source.read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='2148f60f7ebdd2cad533dfc856099ef87e021f727578ba9aacbfa67bc561f55c'
    spec=json.loads((HERE.parent.parent/'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    prefix='import sys\nsys.argv='+repr(['board_readonly_metadata_v14.py',spec['startup_sha256']])+'\n'
    value=json.loads(ssh('python3 -B -',prefix+raw.decode('utf-8'),timeout=15))
    assert value['expected_startup_matches'] is True
    output=HERE/('actual_memory_'+label+'.json')
    with output.open('x',encoding='utf-8') as stream: json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps(value))
