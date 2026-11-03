"""Check the current boot's DT against the sealed, board-tested joint platform."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parent
INVENTORY = ROOT/'evidence/20261020T070400.448367Z-axis-activation-inventory'
BUNDLE = Path('/home/ghmd/kv260-visual-servo-20261007/evidence/20261008T102632.391041Z-candidate-bundle/bundle')
OUT = ROOT/'axis-current-dt-audit'


def tree(path):
    data = path.read_bytes()
    header = struct.unpack('>10I', data[:40])
    assert header[0] == 0xd00dfeed and header[1] == len(data)
    pos, strings, reserve = header[2:5]
    reservations = []
    while True:
        row = struct.unpack_from('>2Q', data, reserve)
        reserve += 16
        if row == (0, 0):
            break
        reservations.append(row)
    nodes, paths, properties = [], set(), {}
    while True:
        token = struct.unpack_from('>I', data, pos)[0]
        pos += 4
        if token == 1:
            end = data.index(0, pos)
            nodes.append(data[pos:end].decode())
            paths.add('/'.join(nodes))
            pos = (end+4)&~3
        elif token == 2:
            nodes.pop()
        elif token == 3:
            size, offset = struct.unpack_from('>2I', data, pos)
            pos += 8
            end = data.index(0, strings+offset)
            name = '/'.join(nodes)+'/'+data[strings+offset:end].decode()
            assert name not in properties
            properties[name] = data[pos:pos+size]
            pos = (pos+size+3)&~3
        elif token == 4:
            pass
        elif token == 9:
            assert not nodes
            break
        else:
            raise ValueError(token)
    return header, reservations, paths, properties


def main():
    OUT.mkdir(exist_ok=True)
    old = BUNDLE/'provenance/current-base.dtb'
    current = INVENTORY/'base-fdt.dtb'
    old_h, old_r, old_n, old_p = tree(old)
    new_h, new_r, new_n, new_p = tree(current)
    # Layout offsets/size can change across boot exports; semantic contents cannot.
    assert old_h[5:8] == new_h[5:8], 'FDT version/last-compatible-version/boot CPU changed'
    assert old_r == new_r and old_n == new_n and old_p == new_p
    overlay = BUNDLE/'lib/firmware/xilinx/aura-visual-servo-b4096-v1/aura-visual-servo-b4096-v1.dtbo'
    assert hashlib.sha256(overlay.read_bytes()).hexdigest() == '82febf56e97811db67b4ddd16dfcf44ff2322221a9c6f43e2b1aa67a4ca9e5cc'
    dtc_root = Path('/home/ghmd/kv260-dpu41-control-20261001/dependencies/dtc-1.7.2')
    env = dict(os.environ, LD_LIBRARY_PATH=str(dtc_root/'libfdt'))
    merged = OUT/'current-joint-merged.dtb'
    subprocess.run([str(dtc_root/'fdtoverlay'), '-i', str(current), '-o', str(merged), str(overlay)], env=env, check=True, capture_output=True)
    _, _, _, merged_p = tree(merged)
    assert merged_p['/fpga-full/firmware-name'] == b'aura-visual-servo-b4096-v1.bit.bin\0'
    report = {'status': 'CURRENT_DT_EXACT_SEMANTIC_MATCH_AND_OVERLAY_MERGE_PASS',
              'base_fdt_sha256': hashlib.sha256(current.read_bytes()).hexdigest(),
              'audited_base_sha256': hashlib.sha256(old.read_bytes()).hexdigest(),
              'properties_compared': len(new_p), 'nodes_compared': len(new_n),
              'reservations_equal': True, 'header_versions_and_boot_cpu_equal': True,
              'ignored_properties': [], 'overlay_sha256': hashlib.sha256(overlay.read_bytes()).hexdigest(),
              'merged_sha256': hashlib.sha256(merged.read_bytes()).hexdigest(),
              'scope': 'CONTROLLED_BENCH_NO_PWM; not formal platform qualification'}
    (OUT/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
