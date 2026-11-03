import base64,bisect,gzip,hashlib,json,subprocess
from pathlib import Path
path=Path('/usr/lib/python3.9/site-packages/vart.so');raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='dc6bff9be31b8dc349a72489e06237f8503175805d042025558694823f61de34'
root=Path('/home/root/aura-native-wait-20261023/external/216391c02cc6e719')
report=json.loads((root/'report.json').read_text());samples=json.loads((root/'numeric-samples.json').read_text())
trace=next(e for e in report['after']['fault_events'] if e['event_sequence']==5788)
rows=samples['targets']['2']['samples'];a=trace['execute_start_mono_ns'];b=trace['execute_return_mono_ns']
left=bisect.bisect_right([r[1] for r in rows],a)-1;right=bisect.bisect_left([r[0] for r in rows],b)
notes=subprocess.check_output(['readelf','-n',str(path)]).decode()
data={'vart_sha256':hashlib.sha256(raw).hexdigest(),'vart_size':len(raw),
 'build_id_lines':[line.strip() for line in notes.splitlines() if 'Build ID' in line],
 'vart_gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode(),
 'samples_sha256':hashlib.sha256((root/'numeric-samples.json').read_bytes()).hexdigest(),
 'sample_fields':samples['sample_fields'],'camera_pid':samples['pid'],'camera_birth_ticks':samples['birth_ticks'],
 'tid':samples['targets']['2']['tid'],'target_identity':report['targets']['2'],
 'trace':trace,'bracket_indices':[left,right],'left_raw_sample':rows[left],'right_raw_sample':rows[right]}
print(json.dumps(data))
