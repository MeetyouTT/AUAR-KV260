#!/usr/bin/env python3
"""Run the hash-verified AArch64 32-bit accessor for the exact PWMT bench."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
action = parser.add_mutually_exclusive_group()
action.add_argument('--start', action='store_true', help='output continuous 50 Hz, 1.5 ms PWM on J2.3 until explicit STOP or reset')
action.add_argument('--stop', action='store_true', help='drive J2.3 low')
action.add_argument('--scratch', action='store_true', help='verify full-width scratch writes without producing PWM')
args = parser.parse_args()
if os.uname().machine != 'aarch64':
    raise RuntimeError('Run only on the KV260 aarch64 board; no MMIO accessed')
root = Path(__file__).resolve().parents[1]
binary = root / 'board/mmio32'
identity = json.loads((root / 'evidence/accessor_identity.json').read_text())
if hashlib.sha256(binary.read_bytes()).hexdigest() != identity['binary_sha256']:
    raise RuntimeError('Accessor hash mismatch; no MMIO accessed')
mode = 'start' if args.start else 'stop' if args.stop else 'scratch' if args.scratch else 'inspect'
completed = subprocess.run([str(binary), mode], check=True, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, timeout=8)
values = json.loads(completed.stdout)
print(json.dumps(values, indent=2))
