#!/usr/bin/env python3
"""Prepare the paired, locally built FPGA deployment files in a new external directory."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'build'))
from bitstream_pairing import check_pairing


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hardware-dir', type=Path, required=True, help='directory containing this run BIT and XSA')
    parser.add_argument('--firmware-dir', type=Path, required=True, help='exported firmware payload directory')
    parser.add_argument('--out', type=Path, required=True, help='fresh external deployment directory')
    args = parser.parse_args()
    out = args.out.resolve()
    hardware = args.hardware_dir.resolve(strict=True)
    firmware = args.firmware_dir.resolve(strict=True)
    if out.exists() or out == ROOT or ROOT in out.parents or hardware in out.parents or firmware in out.parents:
        parser.error('choose a fresh directory outside the package and source artifacts')
    manifest = json.loads((ROOT/'board/bringup/artifact_manifest.json').read_text())
    sources = {'hardware': hardware, 'firmware': firmware}
    files = []
    for row in manifest['files']:
        name = row['file']
        if Path(name).name != name or name in ('.', '..'):
            raise ValueError('Invalid payload name')
        path = sources[row['source']]/name
        if sha(path) != row['sha256'] or path.stat().st_size != row['bytes']:
            raise ValueError('Artifact differs from measured build: '+name)
        files.append((name, path))
    with zipfile.ZipFile(hardware/'auar_source.xsa') as archive:
        bits = [n for n in archive.namelist() if n.lower().endswith('.bit')]
        if len(bits) != 1:
            raise ValueError('Expected one embedded bitstream')
        pairing = check_pairing((hardware/'auar_source.bit').read_bytes(), archive.read(bits[0]))
    if pairing['configuration_payload_sha256'] != manifest['configuration_payload_sha256']:
        raise ValueError('Configuration payload fingerprint differs')
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.auar-artifacts-', dir=str(out.parent)) as temporary:
        stage = Path(temporary)/'artifact'
        stage.mkdir()
        for name, path in files:
            shutil.copyfile(str(path), str(stage/name))
            if sha(stage/name) != sha(path):
                raise OSError('Copied artifact differs: '+name)
        result = dict(manifest, preparation_status='PASS', bit_xsa_pairing=pairing, board_verified=False,
                      scope='PAIRED_OFFLINE_FPGA_ARTIFACTS_PENDING_TARGET_BOARD_TEST')
        (stage/'manifest.json').write_text(json.dumps(result, indent=2)+'\n')
        (stage/'checksums.sha256').write_text(''.join(sha(stage/n)+'  '+n+'\n' for n,p in files))
        stage.rename(out)
    print('PASS', len(files), 'paired firmware/handoff files', out)


if __name__ == '__main__':
    main()

