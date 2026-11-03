#!/usr/bin/env python3
"""Create a small, checked staging archive for this exact accepted Linux package."""
import datetime
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
identity = json.loads((ROOT / 'evidence/source_identity.json').read_text())
accessor = json.loads((ROOT / 'evidence/accessor_identity.json').read_text())
assert accessor['build_id'] == identity['build_id']
assert accessor['mode'] == 'alternating_continuous' and accessor['duty_percent'] == [7.0,8.0]
for key, relative in [('binary_sha256', 'board/mmio32'),
                      ('source_sha256', 'board/mmio32.c'),
                      ('configuration_sha256', 'board/bench_config.h')]:
    assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == accessor[key]
package = json.loads((ROOT / 'CURRENT_LINUX_PACKAGE.json').read_text())
assert package['complete'] and not package['board_accessed']
evidence = Path(package['evidence'])
runtime = evidence / 'lib/firmware/xilinx/aura-pin3-sweep'
members = {str(p.relative_to(evidence)): p for p in runtime.iterdir() if p.is_file()}
members['board/probe.py'] = ROOT / 'board/probe.py'
members['board/mmio32'] = ROOT / 'board/mmio32'
members['evidence/source_identity.json'] = ROOT / 'evidence/source_identity.json'
members['evidence/accessor_identity.json'] = ROOT / 'evidence/accessor_identity.json'
assert set(members) == {
    'lib/firmware/xilinx/aura-pin3-sweep/aura_pin3_sweep.bit.bin',
    'lib/firmware/xilinx/aura-pin3-sweep/aura_pin3_sweep.dtbo',
    'lib/firmware/xilinx/aura-pin3-sweep/shell.json',
    'board/probe.py', 'board/mmio32', 'evidence/source_identity.json',
    'evidence/accessor_identity.json'}
for rel, path in members.items():
    assert path.is_file() and not path.is_symlink()
    if path.parent == runtime:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == package['artifacts'][path.name]['sha256']
tag = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
stage = ROOT / 'evidence' / (tag + '-pwm-board-stage')
stage.mkdir(parents=True, exist_ok=False)
manifest = {rel: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
            for rel, p in sorted(members.items())}
manifest_data = (json.dumps(manifest, indent=2) + '\n').encode()
archive = stage / 'aura-pin3-sweep-stage.tar.gz'
with tarfile.open(archive, 'w:gz', compresslevel=9) as tar:
    for rel, path in sorted(members.items()):
        info = tarfile.TarInfo(rel)
        data = path.read_bytes()
        info.size = len(data)
        info.mode = 0o755 if rel == 'board/mmio32' else 0o644
        tar.addfile(info, io.BytesIO(data))
    info = tarfile.TarInfo('manifest.json')
    info.size = len(manifest_data)
    info.mode = 0o644
    tar.addfile(info, io.BytesIO(manifest_data))
with tarfile.open(archive, 'r:gz') as tar:
    assert set(tar.getnames()) == set(members) | {'manifest.json'}
    for entry in tar:
        assert entry.isfile() and not Path(entry.name).is_absolute() and '..' not in Path(entry.name).parts
        expected = manifest if entry.name == 'manifest.json' else manifest[entry.name]
        data = tar.extractfile(entry).read()
        if entry.name == 'manifest.json':
            assert json.loads(data) == expected
        else:
            assert len(data) == expected['bytes'] and hashlib.sha256(data).hexdigest() == expected['sha256']
status = {'phase': 'board-stage-archive', 'complete': True, 'board_accessed': False,
          'archive': str(archive), 'bytes': archive.stat().st_size,
          'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'files': manifest, 'source_package': str(evidence)}
(stage / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
(ROOT / 'CURRENT_STAGE.json').write_text(json.dumps(status, indent=2) + '\n')
print(json.dumps({'archive': str(archive), 'bytes': status['bytes'], 'sha256': status['sha256']}))
