"""Board-side staging and atomic installation of the four verified runtime files."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

base = Path('/home/root/kv260-test-20261001')
archive = base / 'kv260-benchmark-b4096-dpu41-runtime.tar.gz'
stage = base / 'candidate-stage'
target = Path('/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41')
prefix = 'lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/'
expected = {
    prefix + 'kv260-benchmark-b4096-dpu41.bit.bin': '4d2fd04adc41cafc46ac6edcc7050f2edc9283d28aacfffc85e380a7ff1aebbf',
    prefix + 'kv260-benchmark-b4096-dpu41.dtbo': 'd19426602f7b4873eb8151099066e280313999cd58b5fbdc7fe89301f68ed39d',
    prefix + 'kv260-benchmark-b4096-dpu41.xclbin': '4d9fae142e0a952ea1d1fd1f75395afbb2d485c1b66f507aa9d4cb317532894b',
    prefix + 'shell.json': 'a13dbd0a508de4656c3ba22aa9f8a41494a5082bcd585589fc366a56cc5ba1c1',
}
if Path('/sys/block/mmcblk1/device/cid').read_text().strip() != '0353445345333247805558c00401a100':
    raise SystemExit('Unexpected SD card')
if hashlib.sha256(archive.read_bytes()).hexdigest() != '74470f03231a21ddd4b4525f299688b498910c23b3e85f658791c9b34ee3c80d':
    raise SystemExit('Archive hash mismatch')
if os.path.lexists(str(stage)) or os.path.lexists(str(target)):
    raise SystemExit('Refusing existing stage/target')
with tarfile.open(str(archive), 'r:gz') as tf:
    members = tf.getmembers()
    if len(members) != 5 or set(m.name for m in members) != set(expected) | {'SHA256SUMS'}:
        raise SystemExit('Unexpected archive members')
    if not all(m.isfile() for m in members):
        raise SystemExit('Unexpected archive object type')
    stage.mkdir()
    for member in members:
        data = tf.extractfile(member).read()
        if member.name in expected and hashlib.sha256(data).hexdigest() != expected[member.name]:
            raise SystemExit('Runtime file hash mismatch: ' + member.name)
        dest = stage / member.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        dest.chmod(0o644)
subprocess.run(['sha256sum', '-c', 'SHA256SUMS'], cwd=str(stage), check=True)
source = stage / prefix
shell = json.loads((source / 'shell.json').read_text())
if shell.get('shell_type') != 'XRT_FLAT' or shell.get('num_slots') != '1':
    raise SystemExit('Unexpected shell metadata: ' + repr(shell))
candidate_bin = (source / 'kv260-benchmark-b4096-dpu41.bit.bin').read_bytes()
baseline_bin = Path('/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.bit.bin').read_bytes()
if candidate_bin[:64] != baseline_bin[:64]:
    raise SystemExit('Bootgen header differs from official runtime')
if os.path.lexists(str(target)):
    raise SystemExit('Target appeared during staging')
os.rename(str(source), str(target))
print('CANDIDATE_INSTALLED', str(target), flush=True)
print('BASELINE_DIRECTORY_PRESERVED', flush=True)
