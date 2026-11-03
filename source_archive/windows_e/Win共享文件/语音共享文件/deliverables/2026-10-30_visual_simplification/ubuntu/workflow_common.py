"""Concurrency guards shared by staging and the owned UI deployment transaction."""
import hashlib
import json
import os
from pathlib import Path

from board_state import capture


def projection(value):
    keys = ('boot','actual_config','actual_launcher','actual_runtime','config_sha256',
            'actual_launcher_sha256','pending_config','pending_launcher',
            'pending_config_sha256','pending_launcher_sha256','prior_overrides',
            'mechanical_sha256','settings','firmware','fdt_sha256','vart','ui','camera')
    result = {key:value[key] for key in keys}
    for key in ('actual_proc','camera_proc'):
        result[key] = {k:value[key][k] for k in ('pid','argv','start_ticks')}
    result['camera_epoch'] = value['state']['camera_epoch']
    result['pan'] = {k:value['pan'][k] for k in ('state','pulse_us','target_us','automatic_following')}
    return result


def signature(value):
    return hashlib.sha256(json.dumps(projection(value),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def require_idle(value, expected):
    assert value['safe'] and not value['mismatches'], 'Idle/mic/motion/component gate failed'
    assert value['state']['ui_link'] == 'READY', 'Camera/UI link unavailable'
    assert not value['detected_deployment_processes'], 'Another deployment process exists'
    assert signature(value) == expected, 'Concurrent entry/config/environment update'


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name+'.tmp-'+str(os.getpid()))
    with temporary.open('x') as stream:
        json.dump(value,stream,ensure_ascii=True,indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(str(temporary),str(path))
