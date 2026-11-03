import ast
import base64
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
review=json.loads((HERE/'INDEPENDENT_REVIEW.json').read_text(encoding='utf-8'))
tests=json.loads((HERE/'PURE_TESTS.json').read_text(encoding='utf-8'))
assert tests['status']=='PASS' and tests['tests_run']==31 and not tests['failures'] and not tests['errors']
assert review['status']=='STATIC_SOURCE_PASS_PENDING_PURE_TESTS_NOT_PUBLISHED'
changes={};expected={}
for record in review['records']:
    name=record['file'];data=(HERE/'candidate'/name).read_bytes()
    assert hashlib.sha256(data).hexdigest()==record['after']
    expected[name]={k:record[k] for k in ('before','after')}
    if not record['unchanged']:changes[name]=base64.b64encode(data).decode('ascii')
assert len(changes)==3 and len(expected)==25
template=(HERE/'apply_left40_right45.template.py').read_text(encoding='utf-8')
source=template.replace('PAYLOAD_BASE64',base64.b64encode(json.dumps(changes).encode()).decode('ascii')).replace(
    'EXPECTED_BASE64',base64.b64encode(json.dumps(expected).encode()).decode('ascii'))
ast.parse(source)
destination=HERE/'apply_left40_right45.prepared.py'
assert not destination.exists()
destination.write_text(source,encoding='utf-8')
intent=dict(action='versioned_original_follower_publish_then_original_ui_start_once',
    tests_sha256=hashlib.sha256((HERE/'PURE_TESTS.json').read_bytes()).hexdigest(),
    publication_script_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
    changed_sources=sorted(changes),left_target=.4,right_target=.45,
    requires_fresh_exact_boot_fdt_owners_startup_zone_and_closed_380_25=True)
(HERE/'PUBLICATION_INTENT.json').write_text(json.dumps(intent,indent=2)+'\n',encoding='utf-8')
print(json.dumps(intent,indent=2))
