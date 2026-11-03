"""Audit saved UART responses and the pinned module, without accessing hardware."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    verified = []
    for name in ['20261009T135654.695352Z-inspect', '20261009T140429.187412Z-inspect',
                 '20261009T141504.357541Z-inspect', '20261009T143817.658151Z-inspect']:
        p = ROOT/'evidence'/name
        status = read(p/'status.json')
        assert status['complete'] and status['console_echo_restored']
        for row in status['results']:
            f = p/(row['name']+'.output')
            assert row['exit_code'] == 0 and f.stat().st_size == row['bytes'] and sha(f) == row['sha256']
            verified.append({'response':str(f),'bytes':row['bytes'],'sha256':row['sha256']})
    for name, expected in [('20261009T140918.791930Z-module-load',False),
                           ('20261009T142502.870425Z-module-load',True)]:
        p = ROOT/'evidence'/name
        status = read(p/'status.json')
        assert status['complete'] is expected and status['console_echo_restored']
        for row in status['commands']:
            f = p/(row['name']+'.output')
            assert f.stat().st_size == row['bytes'] and sha(f) == row['sha256']
            assert row['exit_code'] == (1 if not expected and row['name']=='verified-load' else 0)
            verified.append({'response':str(f),'bytes':row['bytes'],'sha256':row['sha256'],
                             'exit_code':row['exit_code']})
    build = read(ROOT/'module_build_validation.json')
    module = Path(build['module'])
    assert build['complete'] and module.stat().st_size == build['bytes'] and sha(module) == build['sha256']
    for path,digest in build['inputs'].items():
        assert sha(Path(path)) == digest
    load = read(ROOT/'evidence/20261009T142502.870425Z-module-load/status.json')['result']
    assert load['module_loaded'] and load['driver_registered'] and not load['forced_load']
    assert load['sha256'] == build['sha256'] and load['vermagic'] == build['vermagic']
    assert load['kernel_loader_resolved_symbols'] == 38 and load['visible_required_function_names'] == 37
    post = read(ROOT/'evidence/20261009T143817.658151Z-inspect/post_load.json')
    assert post['module_loaded'] and post['driver_registered'] and post['vision_process_alive']
    assert not post['stage_errors'] and not post['ui']['error'] and post['ui']['ui_settings']['available']
    assert post['boot_id'] == load['boot_id'] == 'c2753755-e758-4ab6-a4b6-2929271aa723'
    assert post['touch_devices'] == []
    result = {'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'software_driver_repair_verified':True,'physical_touch_verified':False,
              'physical_touch_device_detected':False,'persistent_driver_install':False,
              'module':{k:build[k] for k in ['module','bytes','sha256','vermagic']},
              'load':load,'post_load':post,'uart_responses_verified':len(verified),'responses':verified,
              'limitations':['Screen model/revision and physical wiring remain unknown.',
                             'USB touchscreen is absent from the enumerated devices; finger input and coordinates unverified.',
                             'Driver is loaded for the current boot only; no boot image or module autoload files changed.']}
    (ROOT/'validation_final.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['software_driver_repair_verified','physical_touch_verified',
                                         'persistent_driver_install','uart_responses_verified']}))


if __name__=='__main__':
    main()
