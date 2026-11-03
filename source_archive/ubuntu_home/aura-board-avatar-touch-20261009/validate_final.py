"""Read back saved evidence and write the final deployment audit on Ubuntu."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

WORK = Path(__file__).resolve().parent
REPO = Path('/home/ghmd/Win共享文件/共享文件夹/aura')
GTK = Path('/home/ghmd/aura-board-avatar-gtk-20261009/evidence')
ENV = Path('/home/ghmd/aura-board-avatar-baseline-20261009/evidence/20261009T133349.670700Z-board-environment')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, detail):
    if not condition:
        raise RuntimeError(detail)


evidence = []


def phase(name):
    directory = GTK / name
    status = read(directory / 'status.json')
    response = directory / 'response.output'
    require(status['complete'] and status['exit_code'] == 0, name + ': incomplete')
    require(status['console_echo_restored'], name + ': console echo')
    require(response.stat().st_size == status['bytes'], name + ': response size')
    require(sha(response) == status['response_sha256'], name + ': response SHA')
    evidence.append({'directory': str(directory), 'response_sha256': sha(response),
                     'bytes': response.stat().st_size, 'verified': True})
    return read(response)


base = phase('20261009T124242.018512Z-usb-runtime-deploy')
require(base['verified_payload_files'] == 871 and base['payload_readback_verified'], 'Original payload readback')
audio = phase('20261009T125936.206314Z-usb-runtime-audio-controls')
require(audio['complete'] and all(v['passed'] for v in audio['checks'].values()), 'MCP01 audio checks')
unmount = phase('20261009T130428.921412Z-usb-runtime-unmount-usb')
require(unmount['usb_safely_unmounted'] and unmount['runtime_archive_still_present'], 'USB unmount')
volume = phase('20261009T130615.739435Z-usb-runtime-volume-max')
require(volume['readback_verified'] and volume['microphone_unchanged'], 'Volume readback')
settings = phase('20261009T132550.101267Z-usb-runtime-ui-settings-check')
require(settings['complete'] and settings['input_method'] == 'XTEST_POINTER_NOT_PHYSICAL_TOUCH', 'Settings input scope')
require(settings['checks']['slider_drag_volume'] == 49, 'Slider drag')
for key in ('settings_tab', 'volume_minus', 'volume_plus', 'mute', 'unmute',
            'economy_toggle', 'fullscreen_exit', 'microphone_unchanged'):
    require(settings['checks'][key], 'UI setting ' + key)
playback = phase('20261009T132700.781496Z-usb-runtime-ui-pointer-playback')
require(playback['complete'] and all(playback[k] for k in ('play', 'resume', 'cancel')),
        'Native pointer playback')
require(playback['pause_frozen_seconds'] == 0, 'Pause position')
report = phase('20261009T133636.882945Z-usb-runtime-fetch-report')
defaults = {'volume': 100, 'muted': False, 'fullscreen': True, 'economy': False}
require(report['preferences'] == defaults and report['ui_page'] == 'settings', 'Final preferences and page')
require(report['ui_settings']['available'] and not report['ui_settings']['pending'], 'Final ALSA state')
require(report['ui_settings']['volume'] == 100 and not report['ui_settings']['muted'], 'Final volume')
require(not report['errors'], 'Saved UI errors')

screen_dir = GTK / '20261009T133208.806715Z-usb-runtime-fetch-window'
screen = phase(screen_dir.name)
picture = screen_dir / 'board-window.jpg'
require(picture.stat().st_size == screen['bytes'] and sha(picture) == screen['sha256'], 'Screenshot SHA')

update = read(WORK / 'update_validation.json')
require(sha(WORK / 'touch_settings_update.zip') == update['sha256'], 'Update ZIP SHA')
require((WORK / 'touch_settings_update.zip').stat().st_size == update['bytes'], 'Update ZIP size')
for item in update['files']:
    require(item['path'].startswith('aura/'), 'Update source prefix')
    path = REPO / item['path'][len('aura/'):]
    require(sha(path) == item['sha256'] and path.stat().st_size == item['bytes'], 'Current source: ' + str(path))
    relative = str(path.relative_to(REPO))
    if relative in report['source_hashes_at_launch']:
        require(report['source_hashes_at_launch'][relative] == item['sha256'], 'Running source: ' + relative)
require(update['tests'] == {'run': 70, 'failures': 0, 'errors': 0}, 'Host test record')
deployment_dir = WORK / 'evidence/20261009T131910.962991Z-deploy'
deployment = read(deployment_dir / 'status.json')
require(deployment['complete'] and deployment['console_echo_restored'], 'Update deployment')
for command in deployment['commands']:
    path = deployment_dir / (command['name'] + '.output')
    require(command['exit_code'] == 0, command['name'] + ': exit code')
    require(path.stat().st_size == command['bytes'] and sha(path) == command['sha256'],
            command['name'] + ': command response')
native_tests = (deployment_dir / 'native-settings-tests.output').read_text()
require('Ran 12 tests' in native_tests and '\nOK\n' in native_tests, 'Native tests')

env_status = read(ENV / 'status.json')
require(env_status['complete'] and env_status['console_echo_restored'], 'Final environment probe')
for item in env_status['results']:
    path = ENV / (item['id'] + '.output')
    require(item['exit_code'] == 0 and sha(path) == item['output_sha256']
            and path.stat().st_size == item['bytes'], 'Environment response: ' + item['id'])
identity = read(ENV / 'identity.json')
require(identity['boot_id'] == 'c2753755-e758-4ab6-a4b6-2929271aa723', 'Board boot identity')
processes = read(ENV / 'workloads_and_resources.json')['selected_processes']
require(any(p['pid'] == 16981 for p in processes), 'Existing vision process')
require(any(p['pid'] == 48503 for p in processes), 'Settings UI process')

package_path = REPO / 'artifacts/releases/aura-board-avatar-gtk-runtime-20261009T132845Z-c742c0.verification.json'
package = read(package_path)
archive = Path(package['archive'])
require(sha(archive) == package['sha256'] and archive.stat().st_size == package['bytes'], 'Final portable ZIP')
require(package['manifest_verified'] and package['verified_payload_files'] == 875, 'Portable package manifest')

result = {
    'checked_utc': datetime.now(timezone.utc).isoformat(),
    'complete': True,
    'scope': 'DEPLOYED_SETTINGS_UI_AND_NATIVE_POINTER_CHECKS; PHYSICAL_TOUCH_NOT_VERIFIED',
    'base_installation': base,
    'settings_update': update,
    'deployment_commands_verified': len(deployment['commands']),
    'native_settings_tests': {'run': 12, 'failures': 0, 'errors': 0},
    'settings_ui': settings,
    'pointer_playback_ui': playback,
    'final_ui': {k: report[k] for k in ('ui_page', 'ui_settings', 'preferences', 'touch_devices', 'stats', 'errors')},
    'screenshot': {'path': str(picture), 'bytes': picture.stat().st_size,
                   'sha256': sha(picture), 'visually_inspected': True},
    'final_environment': {'directory': str(ENV), 'boot_id': identity['boot_id'], 'processes': processes},
    'portable_runtime_package': package,
    'portable_runtime_package_deployed_as_whole': False,
    'verified_uart_responses': evidence,
    'limitations': ['No physical touchscreen is currently enumerated; finger input and coordinate mapping unverified.',
                    'XTest pointer checks do not verify physical touch.',
                    'Animation p95 render interval is approximately 473 ms with the existing vision workload.',
                    'Cached playback is verified; live ASR/VLM/TTS integration and final acoustic/system acceptance remain pending.',
                    'UI is running in the current session; no new boot autostart service was installed.']
}
(WORK / 'validation_final.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
(WORK / 'runtime_package_validation.json').write_text(json.dumps(package, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'complete': True, 'deployment_commands_verified': len(deployment['commands']),
                  'uart_phase_responses_verified': len(evidence), 'host_tests': 70, 'native_tests': 12,
                  'report': str(WORK / 'validation_final.json')}, ensure_ascii=False))
