"""Host-only read-only SSH and public-source materialization for this review."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1]
PROJECT = OUT.parents[1]
TRANSPORT = PROJECT / 'deliverables/2026-10-18_board_dialogue/board_ssh.py'
OLD = OUT / 'parallel_platform/gui_startup_review/installed_source'
script = HERE / 'collect_current_dialogue_sources.py'
spec = importlib.util.spec_from_file_location('dialogue_review_readonly_ssh', TRANSPORT)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
start = datetime.now(timezone.utc).isoformat()
result = json.loads(transport.ssh('python3 -B -', script.read_text(encoding='utf-8'), timeout=60))
receipt = dict(host_start_utc=start, host_end_utc=datetime.now(timezone.utc).isoformat(),
               script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
               transport_sha256=hashlib.sha256(TRANSPORT.read_bytes()).hexdigest(), board_result=result)
path = HERE / 'current_source_receipt.json'
with path.open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
index = []
for relative, item in result['files'].items():
    raw = item['text'].encode('utf-8') if 'text' in item else (OLD / relative).read_bytes()
    assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256']
    target = HERE / 'current_source' / relative
    assert target.resolve().is_relative_to((HERE / 'current_source').resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
    index.append(dict(path=str(target), board_path=item['path'], bytes=len(raw), sha256=item['sha256'], current_startup_pinned=True))
(HERE / 'source_index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(status='CURRENT_3FD_SOURCE_PINS_VERIFIED', source_files=len(index),
                     receipt=str(path), configuration=result['configuration'], board_mutations=False),
                 ensure_ascii=True, indent=2))
