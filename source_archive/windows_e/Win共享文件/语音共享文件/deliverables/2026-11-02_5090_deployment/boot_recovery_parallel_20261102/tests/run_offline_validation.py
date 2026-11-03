"""Run only this task's public, synthetic, device-free regression suite."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import unittest

HERE = Path(__file__).resolve().parents[1]


def main():
    (HERE / 'test_work').mkdir(exist_ok=True)
    (HERE / 'validation').mkdir(exist_ok=True)
    source = HERE / 'tests/test_boot_recovery.py'
    spec = importlib.util.spec_from_file_location('boot_recovery_offline_regression', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    with (HERE / 'validation/unittest_final.log').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    files = list((HERE / 'candidate').rglob('*')) + [source]
    hashes = {p.relative_to(HERE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
    receipt = dict(schema='aura-boot-recovery-offline-validation-1',
                   updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   status='PASS_OFFLINE_ONLY' if result.wasSuccessful() else 'FAIL',
                   python=platform.python_version(), host_platform=platform.system(),
                   tests_run=result.testsRun, failed=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
                   original_saved_client_reply_fixture_tested=True,
                   source_sha256=hashes, log='validation/unittest_final.log',
                   coverage=['DFX/default startup dependency order and queued start jobs',
                             'existing hardware owners, incomplete scans and no owner replacement',
                             'once-only durable dispatch, unknown outcome and same-job observation/resume',
                             'exact original replies plus dynamic overlay/ZOCL/render/VART checks',
                             'fresh final owner, consumed/c6c8 rejection and original-bootstrap gate binding',
                             'selected-source drift, full startup drift and preservation of identity/GTK fields',
                             'READY progression, mechanically locked UI and no personal data projection',
                             'exact-byte rollback, newer publication conflicts and unknown backups'],
                   board_calls=0, hardware_or_model_loads=0, real_databases_opened=0,
                   audio_images_or_private_keys_opened=0, deployed=False, cold_boot_accepted=False,
                   limitations=['Windows synthetic metadata execution; Linux/systemd and real client execution not performed',
                                'Python 3.9 syntax parsed; actual board interpreter/ABI not exercised',
                                'Saved source evidence belongs to its original boot, never a fresh device handback'])
    (HERE / 'validation/LOCAL_VALIDATION.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'], tests_run=result.testsRun, failed=len(result.failures),
                          errors=len(result.errors), deployed=False, cold_boot_accepted=False)))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
