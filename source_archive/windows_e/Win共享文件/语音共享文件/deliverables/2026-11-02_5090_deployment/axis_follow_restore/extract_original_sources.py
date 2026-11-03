"""Keep exact public source snapshots for line-based review; never execute them."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
value=json.loads((HERE/'original_axis_inventory_01.json').read_text(encoding='utf-8'))['board_result']
target=HERE/'original_sources';target.mkdir(exist_ok=True)
index={}
for path,item in value['sources'].items():
    if 'text' not in item:continue
    raw=item['text'].encode('utf-8')
    assert hashlib.sha256(raw).hexdigest()==item['sha256']
    output=target/(item['sha256'][:12]+'__'+Path(path).name)
    if output.exists():assert output.read_bytes()==raw
    else:output.write_bytes(raw)
    index[path]={'local_path':str(output),'sha256':item['sha256'],'bytes':len(raw)}
(HERE/'source_index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'snapshot_count':len(index),'argument_documents':value['argument_documents'],
    'maintenance':value['maintenance_roots']},ensure_ascii=False,indent=2))
