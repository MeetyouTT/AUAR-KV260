import json
import struct
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parent.parent
model_path = root / 'inputs/ems/yuk_0.ems.json'
resx_path = root / 'inputs/ems/yuk_0.ems.resx.json'
model = json.loads(model_path.read_text(encoding='utf-8-sig'))
resx = json.loads(resx_path.read_text(encoding='utf-8-sig'))
flat = resx['ExtraFlattenArrays']
identity = [value for y in range(4) for x in range(4) for value in (x/3, y/3)]
rows = []
def walk(value, path=''):
    if isinstance(value, dict):
        if isinstance(value.get('meshCombinator'), dict):
            controls = value['meshCombinator']['combinatorList']
            samples = []
            for index, control in enumerate(controls):
                variable = control['variable']
                key = control['rawMeshList'].removeprefix('#resource')
                raw = flat[key]
                assert len(raw) == variable['meshCount'] * 32
                values = [struct.unpack('<f', struct.pack('<f', float(v)))[0] for v in raw]
                neutral = control['neutralIndex']
                sample = values[neutral*32:(neutral+1)*32] if neutral >= 0 else None
                expected = identity if index == 0 else [0.0]*32
                samples.append({'variable': variable['key'], 'mesh_type': control['meshType'],
                    'mesh_count': variable['meshCount'], 'resource': key,
                    'range': [variable['rangeBegin'], variable['rangeEnd']],
                    'neutral_index': neutral,
                    'neutral_distance_from_first_absolute_or_later_delta':
                        max(abs(a-b) for a,b in zip(sample, expected)) if sample else None})
            rows.append({'path':path, 'label':value.get('label'), 'type':value.get('type'),
                'meshSyncChildMask':value.get('meshSyncChildMask'), 'meshCombine':value.get('meshCombine'),
                'controls':samples})
        for key, child in value.items():
            walk(child, path+'/'+str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk(child, path+'/'+str(index))
walk(model)
result = {'scope':'source resources only; not runtime/SDK certification',
    'layers':len(rows), 'controls':sum(len(r['controls']) for r in rows),
    'layer_types':dict(Counter(r['type'] for r in rows)),
    'mesh_types':dict(Counter(c['mesh_type'] for r in rows for c in r['controls'])),
    'maximum_neutral_distance':max(c['neutral_distance_from_first_absolute_or_later_delta']
        for r in rows for c in r['controls'] if c['neutral_distance_from_first_absolute_or_later_delta'] is not None),
    'rows':rows}
output = Path(__file__).parent/'mesh_source_layout.json'
output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({key:value for key,value in result.items() if key!='rows'}))
