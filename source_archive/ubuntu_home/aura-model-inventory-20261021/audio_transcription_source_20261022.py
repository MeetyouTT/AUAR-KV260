import base64,gzip,hashlib,json
from pathlib import Path
config=Path('/home/root/aura-speech-motion-20261021/de989bf024a9/startup/config.json')
assert hashlib.sha256(config.read_bytes()).hexdigest()=='6c47003c4d020066a3ba4c9daa8f905101d633c4cf507951bea3ac3ca86a161d'
root=Path(json.loads(config.read_text())['runtime'])/'aura'
p=root/'board/runtime/audio/transcription.py';raw=p.read_bytes();assert len(raw)<100000
print(json.dumps({'relative_path':'board/runtime/audio/transcription.py','root':str(root),
 'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'gzbase64':base64.b64encode(gzip.compress(raw)).decode()}))
