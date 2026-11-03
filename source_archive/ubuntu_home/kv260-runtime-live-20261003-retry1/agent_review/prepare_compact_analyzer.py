"""Prepare an additive archive-format-aware analyzer; preserve the frozen original."""
from pathlib import Path
import difflib
import hashlib

ROOT=Path('/home/ghmd/kv260-runtime-live-20261003-retry1/agent_review')
source=ROOT/'analyze_live.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='f20d8620ec2c2b3385f6c5d3e395f1f268d886962f11321df572b94be4ebcbdc'
original=source.read_text()
anchor="    archive=root/'board_evidence.tar.gz'\n"
assert original.count(anchor)==1
replacement="""    archive_format=manifest.get('archive_format','tar.gz')
    require(archive_format in ['tar.gz','tar.xz'],'Unsupported evidence archive format','integrity')
    archive=root/('board_evidence.tar.xz' if archive_format=='tar.xz' else 'board_evidence.tar.gz')
"""
updated=original.replace(anchor,replacement)
target=ROOT/'analyze_live_compact.py'
with target.open('x') as stream:stream.write(updated)
compile(target.read_bytes(),str(target),'exec')
patch=''.join(difflib.unified_diff(original.splitlines(True),updated.splitlines(True),
    fromfile='frozen/analyze_live.py',tofile='additive/analyze_live_compact.py'))
with (ROOT/'analyze_live_compact.patch').open('x') as stream:stream.write(patch)
assert source.read_text()==original
print(hashlib.sha256(target.read_bytes()).hexdigest())
