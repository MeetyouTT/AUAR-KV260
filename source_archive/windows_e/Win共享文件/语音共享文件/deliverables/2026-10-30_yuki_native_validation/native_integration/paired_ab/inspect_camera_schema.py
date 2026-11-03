"""Schema names and aggregate numeric cadence only; no identity values."""
import json,urllib.request
from pathlib import Path
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=2) as response:data=json.load(response)
allowed=('camera','capture','video','detector','detection','tracking','tracker','identity','face','recognition','dpu','yolox','stats','health','status','runtime','metrics','performance','pipeline','worker','native','counters','source')
result={'root_schema_keys':list(data),'container_schema_keys':{key:list(data[key]) for key in allowed if isinstance(data.get(key),dict)}}
p=Path('/home/root/aura-yuki-validation-20261030/native_integration/paired_ab/camera-schema.json');p.write_text(json.dumps(result,indent=2));print(json.dumps(result))
