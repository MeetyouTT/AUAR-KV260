#!/usr/bin/env python3
"""Verify saved, real-board touch evidence without contacting the board."""
import base64
import datetime
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SHA = 'fce568b070bbc0e9210bc6417b39e1c57637d9d24d9fdebc4cb913603505417b'
MODULE = '/lib/modules/5.15.36-xilinx-v2022.2/extra/aura/hid-multitouch.ko'


def main():
    records, evidence = {}, {}
    for phase in ('display', 'start', 'settings-page', 'observe', 'report',
                  'persist-driver', 'verify-final', 'window'):
        paths = sorted((ROOT/'evidence').glob('*-'+phase+'/status.json'))
        path = paths[-1]
        status = json.loads(path.read_text())
        assert status['phase'] == phase
        assert status['complete'] and status['exit_code'] == 0
        assert status['console_echo_restored']
        response = (path.parent/'response.output').read_bytes()
        assert len(response) == status['bytes']
        assert hashlib.sha256(response).hexdigest() == status['sha256']
        result = json.loads(response)
        if phase == 'window':
            data = base64.b64decode(result.pop('jpeg_base64'), validate=True)
            assert len(data) == result['bytes']
            assert hashlib.sha256(data).hexdigest() == result['sha256']
            assert data == (path.parent/'board-window.jpg').read_bytes()
        assert result == json.loads((path.parent/'result.json').read_text())
        records[phase] = result
        evidence[phase] = {'path': str(path.parent), 'bytes': len(response),
                           'sha256': status['sha256']}

    final = records['verify-final']
    start = records['start']
    assert final['launch'] == start
    assert final['processes']['gui'] == [start['pid']]
    assert records['display']['edid_sha256'] == '727d3e1893df759c757c35232f9465b670a64d6de2011b586de48c6446e17c35'
    assert 'DP-1 connected primary 1024x600+0+0' in final['display']
    assert final['hid'] and all(h['driver'] == 'hid-multitouch' for h in final['hid'])
    assert final['state']['touch_devices'] == [{'event': 'event5', 'name': 'WaveShare WS170120'}]
    assert 'Touch mode: direct' in final['touch_classes']
    assert 'Max number of touches: 5' in final['touch_classes']

    observed = records['observe']
    assert observed['method'] == 'READ_ONLY_REAL_EVDEV_NO_GRAB_NO_SYNTHETIC_EVENTS'
    assert observed['physical_device'] == '/sys/class/input/event5'
    assert observed['event_counts']['3:53'] > 0 and observed['event_counts']['3:54'] > 0
    assert observed['event_counts']['1:330'] > 0
    buttons = {e['value'] for e in observed['events'] if e['type'] == 1 and e['code'] == 330}
    assert buttons == {0, 1}
    ui_events = records['report']['input_events']
    touches = {(e['button'], e['event']) for e in ui_events if e['kind'] == 'touch'}
    activations = {e['button'] for e in ui_events if e['kind'] == 'activation'}
    for label in ('音量', '互动', '设置'):
        assert (label, 'touch-begin') in touches and (label, 'touch-end') in touches
    assert {'page_main', 'page_settings'} <= activations
    assert observed['before']['ui_settings']['volume'] != observed['after']['ui_settings']['volume']
    assert not records['report']['errors']
    ui = final['state']['ui_settings']
    saved = final['saved_settings']['values']
    assert ui['available'] and not ui['pending'] and not ui['error']
    assert ui['requested_version'] == ui['applied_version']
    for key in ('volume', 'muted', 'fullscreen', 'economy'):
        assert saved[key] == ui[key]
    percentages = [int(v) for v in re.findall(r'\[(\d+)%\]', final['alsa'])]
    assert percentages and all(v == saved['volume'] for v in percentages)
    assert ('[off]' if saved['muted'] else '[on]') in final['alsa']

    persist = records['persist-driver']
    assert persist['sha256'] == final['module_sha256'] == SHA
    assert persist['module'] == MODULE and not persist['boot_tested']
    assert final['autoload_config'] == 'hid-multitouch\n'
    assert final['checks']['module_resolution']['returncode'] == 0
    assert MODULE in final['checks']['module_resolution']['output']
    service = final['checks']['autoload_service']
    assert service['returncode'] == 0 and 'Result=success' in service['output']
    assert 'LoadState=loaded' in service['output']

    result = {
        'verified_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'response_integrity_verified': len(evidence), 'evidence': evidence,
        'boot_id': start['boot_id'], 'gui_pid': start['pid'],
        'real_touch_events': observed['events_total'],
        'physical_evdev_verified': True,
        'physical_gtk_slider_and_tabs_verified': True,
        'physical_plus_minus_buttons_verified': {'volume_less', 'volume_more'} <= activations,
        'volume_and_saved_settings_verified': True, 'saved_settings': saved,
        'persistent_driver_configuration_verified': True,
        'reboot_tested': False, 'ui_autostart_configured_this_work': False,
        'multitouch_stress_tested': False, 'edge_coordinate_calibration_tested': False,
        'vision_pids': final['processes']['vision'],
        'report_note': 'preferences in the UI report retain startup audio values; current ALSA, ui_settings and saved_settings agree.',
    }
    target = ROOT/'touch_connection_validation.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
