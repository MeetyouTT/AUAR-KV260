#!/usr/bin/env python3
"""Verify UART output/archive/member hashes before extracting raw evidence."""
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parent
source=ROOT/'evidence/collect-final-compact.archive.output'
record=json.loads(source.read_text())
archive_bytes=base64.b64decode(record.pop('archive_base64'),validate=True)
assert len(archive_bytes)==record['archive_bytes']
assert hashlib.sha256(archive_bytes).hexdigest()==record['archive_sha256']
format_name=record.get('archive_format','tar.gz')
assert format_name in ['tar.gz','tar.xz']
archive_path=ROOT/('board_evidence.'+format_name)
directory=ROOT/'board_evidence'
assert not archive_path.exists() and not directory.exists()
with archive_path.open('xb') as stream:stream.write(archive_bytes)
directory.mkdir()
with tarfile.open(fileobj=io.BytesIO(archive_bytes)) as archive:
    members=archive.getmembers()
    assert len(members)==len(record['members'])
    assert {m.name for m in members}==set(record['members'])
    for member in members:
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        data=archive.extractfile(member).read()
        expected=record['members'][member.name]
        assert len(data)==expected['bytes']
        assert hashlib.sha256(data).hexdigest()==expected['sha256'],member.name
        path=directory/member.name
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(data)
(ROOT/'board_evidence_manifest.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'format':format_name,'bytes':len(archive_bytes),
    'members_verified':len(record['members']),'sha256':record['archive_sha256']}))
