"""Read-only checks for the existing cached avatar baseline; no device playback."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import wave

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))
from board.interaction import avatar_assets
from board.runtime.character import DEMO_LINES
from tools.selected_voice_service import VoiceWorker


def fingerprint(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def inspect_resources(root):
    errors, assets, clips = [], [], []
    names = set(avatar_assets.STATE_ASSET.values())
    names.update(name for pool in avatar_assets.POOLS.values() for name in pool)
    for name in sorted(names):
        try:
            directory = avatar_assets.AVATAR_DIR / name
            manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8-sig'))
            frames = avatar_assets.list_frames(directory)
            assert frames, 'No frames'
            entries = manifest['entries']
            assert len(entries) == len(frames) == manifest['count'], 'Frame count differs'
            assert {e['file'] for e in entries} == {p.name for p in frames}, 'Frame list differs'
            total = 0
            for entry in entries:
                name_in_asset = entry['file']
                assert Path(name_in_asset).name == name_in_asset, 'Nonlocal frame name'
                info = fingerprint(directory / name_in_asset)
                assert info['sha256'] == entry['sha256'], 'Frame SHA mismatch: ' + name_in_asset
                assert info['bytes'] == entry['bytes'], 'Frame size mismatch: ' + name_in_asset
                total += info['bytes']
            assets.append({'asset': name, 'frames_verified': len(entries), 'png_bytes': total})
        except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
            errors.append({'component': 'asset:' + name, 'error': str(exc)})
    try:
        if not root.is_dir() or not (root / 'cache').is_dir():
            raise FileNotFoundError('Existing playback root/cache directory is required')
        worker = VoiceWorker(root, cached_only=True)
        for line in DEMO_LINES:
            try:
                result = worker.generate(line['text'])
                with wave.open(result['path'], 'rb') as stream:
                    assert stream.getnframes() > 0
                    duration = stream.getnframes() / stream.getframerate()
                    assert abs(duration - result['duration_seconds']) <= 1 / 24000, 'WAV duration mismatch'
                clips.append({'id': line['id'], 'key': result['key'], 'sha256': result['sha256'],
                              'duration_seconds': duration, 'cache_hit': True})
            except (OSError, ValueError, RuntimeError, AssertionError, wave.Error) as exc:
                errors.append({'component': 'clip:' + line['id'], 'error': str(exc)})
        assert worker.process is None and worker.synth.model is None
        worker.close()
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        errors.append({'component': 'selected_voice_reference', 'error': str(exc)})
    blink_layers = 0
    try:
        blink_root = AURA.parent / 'deliverables/2026-10-06_voice_blink'
        profile = json.loads((blink_root / 'blink_profile.json').read_text(encoding='utf-8-sig'))
        for name, target in profile['targets'].items():
            assert fingerprint(avatar_assets.AVATAR_DIR / name / '000000.png')['sha256'] == target['anchor_sha256']
            for record in target['layers']:
                relative = Path(record['file'])
                assert not relative.is_absolute() and '..' not in relative.parts
                assert fingerprint(blink_root / relative)['sha256'] == record['sha256']
                blink_layers += 1
        reuse = AURA.parent / 'deliverables/2026-10-06_avatar_reuse'
        assert (reuse / 'preview_script.py').is_file()
        json.loads((reuse / 'emotion_profile.json').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        errors.append({'component': 'facial_sources', 'error': str(exc)})
    return {'passed': not errors, 'formal_assets': assets, 'cached_clips': clips,
            'blink_layers_sha256_verified': blink_layers, 'errors': errors,
            'inference_model_loaded': False, 'device_accessed': False,
            'mouth_composition_and_real_playback_not_tested': True}


def module_exists(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def inventory_command(command):
    if shutil.which(command[0]) is None:
        return {'available': False, 'reason': 'COMMAND_NOT_FOUND'}
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
        return {'available': True, 'returncode': result.returncode,
                'output': result.stdout[-6000:], 'error': result.stderr[-2000:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'available': True, 'error': str(exc)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=AURA.parent / 'deliverables/2026-10-06_xilan_live')
    parser.add_argument('--resources-only', action='store_true')
    parser.add_argument('--probe-display-audio', action='store_true', help='Read xrandr/ALSA inventory without playing sound')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    resources = inspect_resources(args.root)
    result = {'schema_version': 'aura-board-avatar-preflight-1',
              'created_at_utc': datetime.now(timezone.utc).isoformat(), 'resources': resources,
              'scope': 'RESOURCE_INTEGRITY_AND_ENVIRONMENT_INVENTORY_NOT_BOARD_PLAYBACK_ACCEPTANCE'}
    if not args.resources_only:
        dependencies = {name: module_exists(name) for name in ('PIL', 'numpy', 'PySide6', 'PySide6.QtMultimedia')}
        machine = platform.machine()
        result['environment'] = {'machine': machine, 'python': platform.python_version(),
                                 'display': os.environ.get('DISPLAY', ''), 'dependencies': dependencies,
                                 'aarch64_candidate_not_board_identity_proof': machine in ('aarch64', 'arm64')}
        if args.probe_display_audio:
            result['environment']['display_inventory'] = inventory_command(['xrandr', '--current'])
            result['environment']['alsa_inventory'] = inventory_command(['aplay', '-l'])
        environment_ready = all(dependencies.values()) and bool(os.environ.get('DISPLAY'))
    else:
        environment_ready = True
    result['passed'] = resources['passed'] and environment_ready
    result['status'] = 'PASS' if result['passed'] else 'NOT_READY'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    summary = {'status': result['status'], 'formal_assets_verified': len(resources['formal_assets']),
               'frames_verified': sum(a['frames_verified'] for a in resources['formal_assets']),
               'cached_clips': resources['cached_clips'], 'blink_layers_sha256_verified': resources['blink_layers_sha256_verified'],
               'errors': resources['errors'], 'environment': result.get('environment'),
               'scope': result['scope']}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
