import hashlib,json
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
meta=json.loads((OPS/'meta.json').read_text());cfg=json.loads(Path(meta['candidate_config']).read_text());n=cfg['native_execution']
print(json.dumps({'candidate_root':meta['candidate_root'],'candidate_config':meta['candidate_config'],
 'native':{k:n[k] for k in ['library','library_sha256','source_manifest','source_manifest_sha256','source_unit_sha256','checkpoint_output']},
 'native_library_actual_sha256':hashlib.sha256(Path(n['library']).read_bytes()).hexdigest(),
 'gui_pid':Path('/proc/76636/stat').exists(),'source_boot':meta['source_boot']}))
