import json,subprocess,time
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021/sface-retry-ab/331f485bd54678ae')
latest=root/'latest-run.json';assert latest.is_file()
info=json.loads(latest.read_text());assert info['complete']
report=json.loads(Path(info['report']).read_text());assert report['complete']
logs=subprocess.check_output(['journalctl','-k','-n','2000','-o','json','--no-pager'],timeout=5).decode();rows=[json.loads(line) for line in logs.splitlines() if line.strip()]
warnings=[x for x in rows if "WARN: HC couldn't access mem fast enough" in x.get('MESSAGE','')]
print(json.dumps({'report':report,'prepared':json.loads((root/'prepared.json').read_text()),'synthetic_test_output':(root/'synthetic-tests.txt').read_text(),'launch':json.loads((root/'launch-result.json').read_text()) if (root/'launch-result.json').exists() else None,'prior_no_face_launch':json.loads((root/'launch-result-before-r2.json').read_text()),'b_only_launch':json.loads((root/'b-only-launch-result.json').read_text()) if (root/'b-only-launch-result.json').exists() else None,'b_only_v2_launch':json.loads((root/'b-only-v2-launch-result.json').read_text()) if (root/'b-only-v2-launch-result.json').exists() else None,'kernel':{'read_mono':time.monotonic(),'first_mono_us':rows[0].get('__MONOTONIC_TIMESTAMP') if rows else None,'last_warning_mono_us':warnings[-1].get('__MONOTONIC_TIMESTAMP') if warnings else None}}))
