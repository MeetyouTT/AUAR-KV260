#!/usr/bin/env python3
"""Build a standalone PL_FLAT package from the accepted PWM XSA, without board access."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path(json.loads((ROOT / 'CURRENT_BUILD.json').read_text())['evidence'])
GENERATED = ROOT / 'evidence/linux-overlay-generated/pl.dtsi'
BASE_DTB = Path('/home/ghmd/kv260-m3-axilite-20261002/test_bundle_attempt02/provenance/baseline-system.dtb')
BOOTGEN = Path('/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin/bootgen')
DTC = Path('/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin/dtc')
FDTOVERLAY = Path('/home/ghmd/kv260-dpu41-control-20261001/dependencies/dtc-1.7.2/fdtoverlay')
FDTGET = Path('/home/ghmd/petalinux/2022.2/components/yocto/buildtools_extended/sysroots/x86_64-petalinux-linux/usr/bin/fdtget')
APP = 'aura-square10'
FIRMWARE = 'aura_square10.bit.bin'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(label, command, evidence):
    env = os.environ.copy()
    if command[0] == FDTOVERLAY:
        env['LD_LIBRARY_PATH'] = str(FDTOVERLAY.parent / 'libfdt')
    result = subprocess.run([str(x) for x in command], text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=90, env=env)
    (evidence / (label + '.log')).write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(label + ' failed: ' + result.stdout[-2000:])
    return result.stdout


def get(path, node, prop, evidence):
    return run('fdtget-' + node.strip('/').replace('/', '-') + '-' + prop,
               [FDTGET, '-t', 's', path, node, prop], evidence).strip()


def main():
    build = json.loads((ROOT / 'CURRENT_BUILD.json').read_text())
    assert build['complete'] and Path(build['evidence']) == BUILD
    assert json.loads((ROOT / 'FINAL_VERIFICATION.json').read_text())['passed']
    ident = json.loads((ROOT / 'evidence/source_identity.json').read_text())
    bit = BUILD / 'artifacts/aura_pwm_probe.bit'
    xsa = BUILD / 'artifacts/aura_pwm_probe.xsa'
    assert bit.is_file() and xsa.is_file() and GENERATED.is_file() and BASE_DTB.is_file()
    hwh = ET.parse(BUILD / 'project/pwm_bench.gen/sources_1/bd/pwm_bench/hw_handoff/pwm_bench.hwh')
    ps = hwh.getroot().find('.//MODULE[@INSTANCE="PS_0"]')
    params = {x.get('NAME'): x.get('VALUE') for x in ps.findall('./PARAMETERS/PARAMETER')}
    assert params['C_MAXIGP2_DATA_WIDTH'] == '32'
    assert params['PSU__CRL_APB__PL0_REF_CTRL__ACT_FREQMHZ'] == '99.999001'
    tag = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    evidence = ROOT / 'evidence' / (tag + '-linux-package')
    evidence.mkdir(parents=True, exist_ok=False)
    runtime = evidence / 'lib/firmware/xilinx' / APP
    runtime.mkdir(parents=True)
    report = {'phase': 'linux-package', 'evidence': str(evidence), 'complete': False,
              'board_accessed': False, 'pl_loaded': False, 'start_sent': False,
              'source_build': str(BUILD), 'sources': {'bit_sha256': sha(bit),
              'xsa_sha256': sha(xsa), 'generated_dtsi_sha256': sha(GENERATED),
              'base_dtb_sha256': sha(BASE_DTB), 'source_identity': ident}}
    try:
        vif = evidence / 'aura_pwm_probe.bif'
        vif.write_text('all:\n{\n    [destination_device = pl] ' + str(bit) + '\n}\n')
        run('bootgen', [BOOTGEN, '-arch', 'zynqmp', '-image', vif, '-o', runtime / FIRMWARE, '-w'], evidence)
        # The vendor generator derives AFI widths, clock assignments, reset and
        # AXI address from the accepted XSA. Add the property used by this board's
        # existing FPGA-manager path; otherwise preserve the generated design.
        generated = GENERATED.read_text()
        generated_firmware = 'aura_pwm_probe.bit.bin'
        assert generated.count('firmware-name = "' + generated_firmware + '";') == 1
        assert generated.count('resets = <&zynqmp_reset 116>;') == 1
        assert 'assigned-clock-rates = <99999001>;' in generated
        assert '<14 0xa00>, <15 0x000>' in generated
        assert 'reg = <0x0 0x80080000 0x0 0x1000>;' in generated
        source = generated.replace('firmware-name = "' + generated_firmware + '";',
                                   'firmware-name = "' + FIRMWARE + '";\n\t\t\tfpga-config-from-dmabuf;')
        assert source.count('fpga-config-from-dmabuf;') == 1
        (evidence / 'runtime-overlay.dts').write_text(source)
        dtbo = runtime / 'aura_square10.dtbo'
        run('dtc', [DTC, '-@', '-I', 'dts', '-O', 'dtb', '-o', dtbo,
                    evidence / 'runtime-overlay.dts'], evidence)
        merged = evidence / 'merged-baseline.dtb'
        run('fdtoverlay', [FDTOVERLAY, '-i', BASE_DTB, '-o', merged, dtbo], evidence)
        firmware_name = get(merged, '/fpga-full', 'firmware-name', evidence)
        assert firmware_name == FIRMWARE, firmware_name
        clock_hex = run('fdtget-clock-hex', [FDTGET, '-t', 'x', merged,
                   '/axi/clocking0', 'assigned-clock-rates'], evidence).strip()
        assert int(clock_hex, 16) == 99999001, clock_hex
        afi_hex = run('fdtget-afi-hex', [FDTGET, '-t', 'x', merged,
                  '/axi/afi0', 'config-afi'], evidence).split()
        afi_values = [int(x, 16) for x in afi_hex]
        assert len(afi_values) == 32
        assert afi_values[28:32] == [14, 0xa00, 15, 0]
        reg_hex = run('fdtget-reg-hex', [FDTGET, '-t', 'x', merged,
                  '/axi/aura_pwm_probe@80080000', 'reg'], evidence).split()
        assert [int(x, 16) for x in reg_hex] == [0, 0x80080000, 0, 0x1000]
        assert b'fpga-config-from-dmabuf\x00' in dtbo.read_bytes()
        (runtime / 'shell.json').write_text(json.dumps({'shell_type': 'PL_FLAT',
                                                        'num_pl_slots': 1}, indent=2) + '\n')
        report['artifacts'] = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)}
                               for p in sorted(runtime.iterdir())}
        report['dtb_check'] = {'firmware_name': firmware_name, 'clock_hz': 99999001,
                               'afi_14': 0xa00, 'afi_15': 0, 'reg': '0x80080000/0x1000'}
        report['complete'] = True
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        (evidence / 'status.json').write_text(json.dumps(report, indent=2) + '\n')
        (ROOT / 'CURRENT_LINUX_PACKAGE.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
