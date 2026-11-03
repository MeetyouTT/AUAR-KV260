"""Read-only package integrity check. Python 3.8+, standard library only."""
from pathlib import Path
import hashlib
import json
import zipfile

root=Path(__file__).resolve().parent.parent
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest=root/'sha256sums.txt'
checked=0
for line in manifest.read_text().splitlines():
    digest,name=line.split('  ',1)
    path=(root/name).resolve()
    if root not in path.parents:
        raise SystemExit('FAIL: unsafe manifest path')
    if not path.is_file() or sha(path.read_bytes())!=digest:
        raise SystemExit('FAIL: '+name)
    checked+=1
rows=[json.loads(l) for l in (root/'conversations_full.jsonl').read_text().splitlines()]
for row in rows:
    if sha(row['text'].encode())!=row['export_text_sha256']:
        raise SystemExit('FAIL: exported message '+row['item_id'])
sources=json.loads((root/'source_index.json').read_text())['entries']
for entry in sources:
    if entry.get('snapshot') and sha((root/entry['snapshot']).read_bytes())!=entry['snapshot_sha256']:
        raise SystemExit('FAIL: snapshot '+entry['evidence_id'])
with zipfile.ZipFile(root/'ai_collaboration_record.docx') as doc:
    if doc.testzip():raise SystemExit('FAIL: DOCX CRC')
print('PASS: %d files, %d exported messages, %d indexed sources'%(checked,len(rows),len(sources)))
