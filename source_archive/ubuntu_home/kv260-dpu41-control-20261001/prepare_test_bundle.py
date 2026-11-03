#!/usr/bin/env python3
"""Build an isolated host bundle; this script never accesses a board device."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
REFERENCE = Path('/home/ghmd/kv260-reference-2022.2-20260930')
READONLY = Path('/home/ghmd/AMD_Smart/logs/fpga/2026-09-30-kv260-readonly')
APP = 'kv260-benchmark-b4096-dpu41'
FDT_BIN = Path('/home/ghmd/petalinux/2022.2/components/yocto/buildtools_extended/sysroots/x86_64-petalinux-linux/usr/bin')
VITIS_BIN = Path('/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin')
DTC_HOST = ROOT / 'dependencies/dtc-1.7.2'
BUNDLE = ROOT / 'test_bundle'
RUNTIME = BUNDLE / 'lib/firmware/xilinx' / APP
PROVENANCE = BUNDLE / 'provenance'
SD_CARD = ROOT / 'src/kv260/overlays/examples/benchmark/binary_container_1/sd_card'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, log, env=None):
    with log.open('w') as output:
        result = subprocess.run([str(a) for a in args], stdout=output, stderr=subprocess.STDOUT, env=env)
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {args}; log={log}')


def dtbo():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    PROVENANCE.mkdir(parents=True, exist_ok=True)
    baseline = REFERENCE / 'evidence/deployment_review/compatibility_diagnosis/baseline_image_files/kv260-benchmark-b4096.dtbo'
    assert sha(baseline) == '36338937904e5ec988566d7341f6504edba34c01bd7e2e3f2025ab0069337e35'
    original = PROVENANCE / 'baseline-kv260-benchmark-b4096.dtbo'
    shutil.copy2(baseline, original)
    base = PROVENANCE / 'baseline-system.dtb'
    shutil.copy2(READONLY / 'baseline-host-image-boot/system.dtb', base)
    output = RUNTIME / f'{APP}.dtbo'
    shutil.copy2(original, output)
    run([FDT_BIN / 'fdtput', '-t', 's', output, '/fragment@0/__overlay__', 'firmware-name', f'{APP}.bit.bin'], ROOT / 'logs/dtbo_rename.log')
    merge_env = os.environ.copy()
    merge_env['LD_LIBRARY_PATH'] = str(DTC_HOST / 'libfdt')
    run([DTC_HOST / 'fdtoverlay', '-i', base, '-o', PROVENANCE / 'host-merged-system.dtb', output], ROOT / 'logs/dtbo_host_merge_v172.log', env=merge_env)
    run([VITIS_BIN / 'dtc', '-I', 'dtb', '-O', 'dts', '-o', PROVENANCE / 'candidate.decompiled.dts', output], ROOT / 'logs/dtbo_decompile.log')
    firmware = subprocess.check_output([str(FDT_BIN / 'fdtget'), '-t', 's', str(output), '/fragment@0/__overlay__', 'firmware-name'], text=True).strip()
    assert firmware == f'{APP}.bit.bin'
    properties = subprocess.check_output([str(FDT_BIN / 'fdtget'), '-p', str(output), '/fragment@0/__overlay__'], text=True).splitlines()
    assert 'fpga-config-from-dmabuf' in properties
    def decompiled(path):
        return subprocess.run([str(VITIS_BIN / 'dtc'), '-I', 'dtb', '-O', 'dts', str(path)], check=True, capture_output=True, text=True).stdout
    assert decompiled(original).replace('kv260-benchmark-b4096.bit.bin', firmware) == decompiled(output)
    merged_firmware = subprocess.check_output([str(FDT_BIN / 'fdtget'), '-t', 's', str(PROVENANCE / 'host-merged-system.dtb'), '/fpga-full', 'firmware-name'], text=True).strip()
    assert merged_firmware == firmware
    shell = {'shell_type': 'XRT_FLAT', 'num_slots': '1'}
    (RUNTIME / 'shell.json').write_text(json.dumps(shell, indent=4) + '\n')
    manifest = {
        'application': APP,
        'baseline_dtbo_sha256': sha(original),
        'candidate_dtbo_sha256': sha(output),
        'baseline_system_dtb_sha256': sha(base),
        'firmware_name': firmware,
        'fpga_config_from_dmabuf': True,
        'host_fdtoverlay_merge': 'PASS',
        'host_fdtoverlay_version': 'upstream DTC 1.7.2, isolated local build',
        'legacy_fdtoverlay_result': 'PetaLinux native DTC 1.6.1-dirty fails both unmodified baseline and candidate; phandle overwrite diagnosed; baseline and candidate both pass with DTC 1.7.2',
        'dtbo_origin': 'reused original PetaLinux 2022.2 image DTBO, firmware-name changed only',
        'only_semantic_change': 'firmware-name',
        'semantic_diff_verified': True,
        'merged_fpga_firmware_name': merged_firmware,
        'merged_fpga_node': '/fpga-full',
        'board_load_test': 'NOT RUN',
    }
    (ROOT / 'evidence/dtbo_validation.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


def hardware():
    hw = PROVENANCE / 'hardware'
    hw.mkdir(parents=True, exist_ok=True)
    bit = SD_CARD / 'kv260_ispMipiRx_vcu_DP_wrapper.bit'
    hwh = SD_CARD / 'kv260_ispMipiRx_vcu_DP.hwh'
    arch = SD_CARD / 'arch.json'
    xclbin = SD_CARD / 'dpu.xclbin'
    assert json.loads(arch.read_text())['fingerprint'] == '0x101000056010407'
    for source in [bit, hwh, arch]:
        shutil.copy2(source, hw / source.name)
    shutil.copy2(xclbin, RUNTIME / f'{APP}.xclbin')
    bif = PROVENANCE / 'candidate_bit.bif'
    copied_bit = hw / bit.name
    bif.write_text('all:\n{\n    [destination_device = pl] ' + str(copied_bit) + '\n}\n')
    generated = PROVENANCE / 'candidate-full-bootgen.bin'
    source_record = PROVENANCE / 'candidate-full-bootgen-input-bit.sha256'
    bit_hash = sha(copied_bit)
    if generated.exists():
        assert source_record.exists() and source_record.read_text().strip() == bit_hash, 'Existing BIN has a different BIT source'
    else:
        run([VITIS_BIN / 'bootgen', '-arch', 'zynqmp', '-image', bif, '-o', generated], ROOT / 'logs/bootgen_full_image.log')
        source_record.write_text(bit_hash + '\n')
    baseline_bin = ROOT / 'evidence/baseline-kv260-benchmark-b4096.bit.bin'
    assert sha(baseline_bin) == '7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f'
    assert generated.open('rb').read(64) == baseline_bin.open('rb').read(64), 'BIN header differs from original image format'
    shutil.copy2(generated, RUNTIME / f'{APP}.bit.bin')
    files = sorted(p for p in BUNDLE.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
    (BUNDLE / 'SHA256SUMS').write_text(''.join(sha(p) + '  ' + p.relative_to(BUNDLE).as_posix() + '\n' for p in files))
    print(f'Prepared {len(files)} candidate bundle files; no board load performed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['dtbo', 'hardware'])
    stage = parser.parse_args().stage
    (dtbo if stage == 'dtbo' else hardware)()
