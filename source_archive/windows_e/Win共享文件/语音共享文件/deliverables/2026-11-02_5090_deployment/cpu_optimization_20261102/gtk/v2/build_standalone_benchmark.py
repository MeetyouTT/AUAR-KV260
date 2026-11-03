import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
bundle={
    'contract':(HERE/'original/board/interaction/ui_contract.py').read_text(encoding='utf-8'),
    'original_services':(HERE/'original/board/interaction/ui_services.py').read_text(encoding='utf-8'),
    'candidate_services':(HERE/'candidate/board/interaction/ui_services.py').read_text(encoding='utf-8'),
    'original_preview':(HERE/'original/tools/board_camera_preview.py').read_text(encoding='utf-8'),
    'candidate_preview':(HERE/'candidate/tools/board_camera_preview.py').read_text(encoding='utf-8')}
support=(HERE/'projection_support.py').read_text(encoding='utf-8')
benchmark=(HERE/'benchmark_projection.py').read_text(encoding='utf-8')
benchmark=benchmark.replace('from projection_support import client,snapshot\n','')
code='SOURCE_BUNDLE = '+repr(bundle)+'\n'+support+'\n'+benchmark
compile(code,'<public-projection-cpu-benchmark>','exec')
target=HERE/'projection_public_benchmark_standalone.py'
with target.open('x',encoding='utf-8') as stream:stream.write(code)
print(json.dumps({'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'sha256_lf':hashlib.sha256(code.encode()).hexdigest(),'bytes':target.stat().st_size}))
