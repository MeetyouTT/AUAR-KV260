"""Read the current native screen and UI state without changing pages or dialogs."""
import base64,hashlib,json,sys
from pathlib import Path
stage=Path('/home/root/aura-bytetrack-20261011/update-ea926df36eb116cd')
manifest=json.loads((stage/'payload/manifest.json').read_text())
assert hashlib.sha256((stage/'payload/board_probe.py').read_bytes()).hexdigest()==manifest['files']['board_probe.py']['sha256']
sys.path.insert(0,str(stage/'payload'))
from board_probe import api,report,screenshot
_,data=report();shot=screenshot(data,True)
blob=base64.b64decode(shot.pop('jpeg_base64'),validate=True)
print(json.dumps({'ui':api(),'geometry':data['ui_geometry'],'source_hashes_at_launch':data['source_hashes_at_launch'],
    'errors':data['errors'],'input_events':data['input_events'][-20:],'screenshot':shot,
    'artifacts':{'current-screen.jpg':{'base64':base64.b64encode(blob).decode(),'bytes':len(blob),
        'sha256':hashlib.sha256(blob).hexdigest()}}},ensure_ascii=False))
