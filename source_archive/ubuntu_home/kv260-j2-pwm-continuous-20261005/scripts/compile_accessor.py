#!/usr/bin/env python3
"""Compile and inspect word-wide accessor without touching hardware."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = Path('/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin')
evidence = ROOT / 'evidence'

def run(name, command):
    p = subprocess.run(list(map(str, command)), text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60)
    (evidence / name).write_text(p.stdout)
    if p.returncode:
        raise RuntimeError(p.stdout)
    return p.stdout

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

run('accessor-compile.log', [BIN/'aarch64-linux-gnu-gcc', '-std=c11', '-O2',
    '-Wall', '-Wextra', '-Werror', ROOT/'board/mmio32.c', '-o', ROOT/'board/mmio32'])
dis = run('mmio32.disassembly.txt', [BIN/'aarch64-linux-gnu-objdump', '-d', ROOT/'board/mmio32'])
read = dis.split('<mmio_read32>:', 1)[1].split('\n\n', 1)[0]
write = dis.split('<mmio_write32>:', 1)[1].split('\n\n', 1)[0]
assert re.search(r'\bldr\s+w0,\s*\[x0\]', read)
assert re.search(r'\bstr\s+w1,\s*\[x0\]', write)
assert 'dsb\tsy' in read and write.count('dsb\tsy') == 2
assert not re.search(r'\b(?:strb|strh|stp|sturb|sturh)\b', write)
elf = run('mmio32.elf.txt', [BIN/'aarch64-linux-gnu-readelf', '-h', '-l', '-V', ROOT/'board/mmio32'])
assert 'AArch64' in elf and '/lib/ld-linux-aarch64.so.1' in elf
identity = json.loads((evidence/'source_identity.json').read_text())
header = (ROOT/'board/bench_config.h').read_text()
assert '#define BENCH_BUILD_ID 0x'+identity['build_id']+'u' in header
assert '#define BENCH_RUN_FRAMES 0u' in header
probe = subprocess.run(['python3','-B',str(ROOT/'board/probe.py')],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
assert probe.returncode != 0 and 'Run only on the KV260 aarch64 board; no MMIO accessed' in probe.stderr
report = {'source_sha256':sha(ROOT/'board/mmio32.c'),
    'configuration_sha256':sha(ROOT/'board/bench_config.h'),
    'binary_sha256':sha(ROOT/'board/mmio32'), 'architecture':'aarch64',
    'build_id':identity['build_id'], 'run_frames':0, 'mode':'continuous',
    'read_instruction':'ldr w0, [x0]', 'write_instruction':'str w1, [x0]',
    'barrier':'dsb sy', 'offline_verified':True, 'board_verified':False}
(evidence/'accessor_identity.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
