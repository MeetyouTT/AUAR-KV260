"""Download only the two small official C++ reference sources for comparison."""
import hashlib,json,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
folder=HERE/'official_reference';folder.mkdir(exist_ok=True)
manifest={}
for name in ('face_detect.cpp','face_recognize.cpp'):
 url='https://raw.githubusercontent.com/opencv/opencv/4.6.0/modules/objdetect/src/'+name
 with urllib.request.urlopen(url,timeout=20) as response:raw=response.read(100001)
 assert 100<len(raw)<=100000
 (folder/name).write_bytes(raw)
 manifest[name]={'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
(folder/'sources.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest))
