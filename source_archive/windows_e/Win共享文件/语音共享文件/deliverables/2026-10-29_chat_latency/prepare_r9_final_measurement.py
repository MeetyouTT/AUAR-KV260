"""Preserve the invalidated sample set; use a new exact-guarded measurement."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
data=json.loads((H/'voice_trimmed.json').read_text(encoding='utf-8'))
assert data['status']=='FAIL' and data['error']=='AssertionError: Model residency changed during measurement'
assert len(data['trials'])==8 and data['models_before']!=data['models_after']
source=(H/'benchmark_voice_r9.py').read_text(encoding='utf-8').replace("'trimmed'","'trimmed_final'")
compile(source,'benchmark_voice_r9_final.py','exec')
(H/'benchmark_voice_r9_final.py').write_text(source,encoding='utf-8')
print('Original eight functional replies retained as performance-invalid evidence; fresh exact residency guard unchanged')
