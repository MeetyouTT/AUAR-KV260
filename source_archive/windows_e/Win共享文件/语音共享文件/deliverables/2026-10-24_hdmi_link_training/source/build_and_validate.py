"""Fail closed on compiler, build, export or kernel-version mismatches."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
WORK = Path('/home/ghmd/aura-display-sequence-20261024/native-retrain-v2')
SOURCE = Path('/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux')
BUILD = ROOT.with_name('native-retrain') / 'kernel-build'
PREFIX = '/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-'


def main():
    assert Path(PREFIX + 'gcc').is_file()
    # Even a copy in the shared source folder builds ELF only in private work.
    for name in ('aura_dp_retrain_candidate.c', 'Makefile'):
        assert (WORK / name).read_bytes() == (ROOT / name).read_bytes()
    with (ROOT / 'build-verified.log').open('w') as out:
        subprocess.run(['make', '-C', str(SOURCE), 'O=' + str(BUILD),
            'M=' + str(WORK), 'ARCH=arm64', 'CROSS_COMPILE=' + PREFIX, 'modules'],
            stdout=out, stderr=subprocess.STDOUT, check=True)
    module = WORK / 'aura_dp_retrain_candidate.stripped.ko'
    subprocess.run([PREFIX + 'strip', '--strip-debug', '-o', str(module),
                    str(WORK / 'aura_dp_retrain_candidate.ko')], check=True)
    raw = module.read_bytes()
    vermagic = '5.15.36-xilinx-v2022.2 SMP mod_unload aarch64'
    assert ('vermagic=' + vermagic).encode() in raw
    symbols = subprocess.check_output([PREFIX + 'nm', '-u', str(module)], text=True)
    undefined = [row.split()[-1] for row in symbols.splitlines()]
    exports = {row.split()[1] for row in (BUILD / 'Module.symvers').read_text().splitlines()
               if len(row.split()) >= 2}
    missing = sorted(set(undefined) - exports)
    assert not missing, missing
    result = dict(scope='compile/link and local matching kernel export validation only',
        source_sha256=hashlib.sha256((ROOT / 'aura_dp_retrain_candidate.c').read_bytes()).hexdigest(),
        module_sha256=hashlib.sha256(raw).hexdigest(), module_bytes=len(raw),
        vermagic=vermagic, undefined_symbols=undefined, missing_exports=missing,
        default_enable_action=False, unbind_invalidation=True, active_output_check=True, passed=True)
    (ROOT / 'build-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
