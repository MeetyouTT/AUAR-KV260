"""Promote only an exact successful regression receipt and unchanged sources."""
import hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent
root=ET.parse(H/'tests_r9.xml').getroot();suites=list(root.iter('testsuite'))
assert sum(int(s.attrib['tests']) for s in suites)==355
assert not any(int(s.attrib.get(k,0)) for s in suites for k in ('failures','errors','skipped'))
plan=json.loads((H/'source_plan_r9.json').read_text(encoding='utf-8'));assert plan['status']=='TESTING'
for name,entry in plan['files'].items():
 assert hashlib.sha256((H/'candidate_r9_source'/name).read_bytes()).hexdigest()==entry['candidate'],name
plan.update(status='READY_WINDOWS_ONLY',tests_passed=355)
(H/'source_plan_r9.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print('355 tests passed; unchanged r9 candidate ready for guarded Windows deployment')
