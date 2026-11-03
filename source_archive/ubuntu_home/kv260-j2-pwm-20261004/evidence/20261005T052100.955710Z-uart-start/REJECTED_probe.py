#!/usr/bin/env python3
"""Diagnostic client for the exact standalone PWMT bench image, after loading."""
import argparse
import json
import mmap
import os
from pathlib import Path
import struct
import time

parser = argparse.ArgumentParser(description=__doc__)
action = parser.add_mutually_exclusive_group()
action.add_argument('--start', action='store_true', help='request exactly 50 pulses, then wait for hardware expiration')
action.add_argument('--stop', action='store_true', help='truncate the current bench burst')
args = parser.parse_args()
# Check Linux's loaded-image identity before touching the AXI window. Reading
# an absent AXI slave can hang a board, even when the client only reads.
if os.uname().machine != 'aarch64':
    raise RuntimeError('Run only on the KV260 aarch64 board; no MMIO accessed')
firmware_names = [p.read_bytes().rstrip(b'\x00').decode() for p in
                  Path('/sys/firmware/devicetree/base').rglob('firmware-name')]
if firmware_names != ['aura_pwm_probe.bit.bin']:
    raise RuntimeError('Loaded firmware is not aura_pwm_probe.bit.bin; no MMIO accessed')
if Path('/sys/class/fpga_manager/fpga0/state').read_text().strip() != 'operating':
    raise RuntimeError('FPGA manager is not operating; no MMIO accessed')
write = args.start or args.stop
fd = os.open('/dev/mem', (os.O_RDWR if write else os.O_RDONLY) | os.O_SYNC)
mem = mmap.mmap(fd, 4096, flags=mmap.MAP_SHARED,
                prot=mmap.PROT_READ | (mmap.PROT_WRITE if write else 0), offset=0x80080000)

def read(offset):
    return struct.unpack_from('<I', mem, offset)[0]

def command(key):
    struct.pack_into('<I', mem, 0x10, key)

try:
    if read(0) != 0x50574D54 or read(4) != 0x10000:
        raise RuntimeError('PWMT bench identity/ABI mismatch; no writes performed')
    if args.stop:
        command(0x53544F50)
    elif args.start:
        expected_build = int(json.loads((Path(__file__).resolve().parents[1] /
            'evidence/source_identity.json').read_text())['build_id'], 16)
        expected = {8: expected_build, 0x14: 1999980, 0x18: 149999,
                    0x20: 99999001, 0x24: 50, 0x28: 1500}
        if any(read(k) != v for k, v in expected.items()) or read(0x0c) != 4:
            raise RuntimeError('Build/configuration/idle state mismatch; no START performed')
        command(0x53544152)
        deadline = time.monotonic() + 2.0
        try:
            if not read(0x0c) & 1:
                raise RuntimeError('START did not enter busy state')
            while read(0x0c) & 1:
                if time.monotonic() > deadline:
                    raise RuntimeError('Hardware expiration was not observed in time')
                time.sleep(0.01)
        finally:
            command(0x53544F50)
        if read(0x0c) & 3 or read(0x1c):
            raise RuntimeError('Output did not return to disabled state')
    print(json.dumps({'ip_id': hex(read(0)), 'abi': hex(read(4)), 'build_id': hex(read(8)),
        'status': read(0x0c), 'period_ticks': read(0x14), 'pulse_ticks': read(0x18),
        'frames_left': read(0x1c), 'clock_hz': read(0x20), 'run_frames': read(0x24),
        'pulse_us': read(0x28)}, indent=2))
finally:
    mem.close()
    os.close(fd)
