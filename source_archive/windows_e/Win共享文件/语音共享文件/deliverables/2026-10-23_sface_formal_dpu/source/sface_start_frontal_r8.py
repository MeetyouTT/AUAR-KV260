import hashlib,json
from pathlib import Path
root=Path('/home/root/aura-sface-formal-20261023/00b792619ce222d2')
report=json.loads((root/'report.json').read_text())
assert report['phase']=='WAITING_OPERATOR_FRONTAL_START' and not report['complete'] and not report['accepted']
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()==report['unit_sha256']
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
ack={'boot':boot,'helper_sha256':'00b792619ce222d28011008ebd369a1efbe37e8b3cf5025300d4b4188f215a83',
     'user_frontal_ready':True,'basis':'user confirmed enrolled identity and readiness; start announced after camera and GUI ready'}
with (root/'operator-frontal-ready.json').open('x') as stream:json.dump(ack,stream)
print(json.dumps({'operator_start_recorded':True,'phase_before_start':report['phase'],'unit_sha256':report['unit_sha256']}))
