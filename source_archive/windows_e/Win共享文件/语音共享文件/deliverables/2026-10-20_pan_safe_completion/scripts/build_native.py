"""Compile a candidate transport, never load it or access board hardware."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cross-cc', required=True)
parser.add_argument('--host-cc', default='cc')
parser.add_argument('--out', required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
commands = []


def run(command, expect_success=True):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    commands.append(dict(argv=command, returncode=result.returncode, output=result.stdout))
    if (result.returncode == 0) != expect_success:
        raise RuntimeError('Unexpected compiler/test result: '+result.stdout)


flags = ['-Wall', '-Wextra', '-Werror', '-std=c11', '-O2']
run([args.host_cc]+flags+['-I', str(root/'native'), str(root/'tests/test_protocol.c'), '-o', str(out/'test_protocol')])
run([str(out/'test_protocol')])
# A zero/unassigned build ID must not silently produce a working library.
run([args.host_cc]+flags+['-DVSRV_BUILD_ID=0', '-I', str(root/'native'),
    '-fsyntax-only', str(root/'tests/test_protocol.c')], expect_success=False)
run([args.cross_cc]+flags+['-fPIC', '-shared', str(root/'native/vsrv_mmio.c'), '-o', str(out/'libvsrv2.so')])
data = (out/'libvsrv2.so').read_bytes()
assert data[:6] == b'\x7fELF\x02\x01' and int.from_bytes(data[18:20], 'little') == 183
sha = lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
result = dict(status='AARCH64_COMPILE_AND_HOST_PROTOCOL_PASS_NO_MMIO',
              native_library_executed=False, board_accessed=False,
              elf_machine='AArch64', library_sha256=sha(out/'libvsrv2.so'),
              sources={str(p.relative_to(root)):sha(p) for p in [root/'native/vsrv_mmio.c', root/'native/vsrv_protocol.h', root/'tests/test_protocol.c']},
              commands=commands)
(out/'native-build.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({key:result[key] for key in ('status', 'elf_machine', 'library_sha256')}))
