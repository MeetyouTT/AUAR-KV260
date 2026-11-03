"""Package a portable cached GTK runtime or a small, no-playback native probe."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import uuid
import zipfile

AURA = Path(__file__).resolve().parents[1]
SHARED = AURA.parent
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

PROBE_FILES = ('tools/gstreamer_audio_engine.py', 'tools/gstreamer_audio_worker.py',
    'tools/gstreamer_audio.py', 'tools/realtime_audio.py', 'tools/check_gstreamer_clock.py',
    'tools/pillow_compat.py', 'tools/board_avatar_gtk.py', 'config/board_avatar_gtk.json',
    'tests/framework/test_gstreamer_audio.py')
STAGE_TOOLS = ('demo_script.py', 'demo_stage.py', 'mouth_compositor.py', 'facial_layers.py',
    'selected_voice_demo.py', 'selected_voice_service.py', 'realtime_controller.py',
    'realtime_facials.py', 'realtime_metrics.py', 'realtime_bridge.py', 'board_avatar_preflight.py',
    'package_board_avatar.py', 'board_ui_settings.py', 'x11_foreground.py', 'board_screen_capture.py',
    'board_avatar_worker.py', 'board_camera_preview.py', 'board_recording.py', 'board_audio_capture.py',
    'configure_board_asr.py', 'asr_server.py')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def collect(profile):
    files = {AURA/name for name in PROBE_FILES}
    if profile == 'native-probe':
        return sorted(files)
    files.add(AURA/'docs/BOARD_AVATAR_GTK.md')
    files.add(AURA/'docs/BOARD_UI_SETTINGS.md')
    files.add(AURA/'docs/BOARD_TOUCH_UI_DESIGN.md')
    files.add(AURA/'docs/BOARD_CAMERA_UI.md')
    files.add(AURA/'docs/BOARD_YOLO.md')
    files.add(AURA/'docs/BOARD_TRACKING.md')
    files.add(AURA/'docs/BOARD_AUDIO_CAPTURE.md')
    files.add(AURA/'docs/BOARD_ASR.md')
    for name in ('host/__init__.py','host/model_service/__init__.py','host/model_service/protocol.py',
                 'tests/framework/test_audio_capture.py','tests/framework/test_board_recording.py',
                 'tests/framework/test_transcription.py',
                 'tests/framework/test_stage_bridge.py'):
        files.add(AURA/name)
    files.add(AURA/'config/board_ui_services.json')
    files.add(AURA/'config/board_camera_ui.json')
    files.add(AURA/'config/board_camera_ui.cpu_yunet.json')
    files.add(AURA/'config/board_camera_ui.yolo_iou.json')
    files.add(AURA/'models/dpu/yolox_nano_person.prototxt')
    files.add(AURA/'board/vision/bytetrack/LICENSE')
    files.add(AURA/'board/vision/bytetrack/upstream_manifest.json')
    files.add(AURA/'tests/framework/test_person_bytetrack.py')
    files.add(AURA/'board/vision/native/yolox_bridge.cpp')
    files.add(AURA/'board/vision/native/libaura_yolox.so')
    files.add(AURA/'tests/framework/test_yolo_dpu.py')
    files.add(AURA/'tests/fixtures/vision/person_bus.jpg')
    files.add(AURA/'tests/fixtures/vision/README.md')
    files.add(AURA/'scripts/board_camera_ui/aura-camera-ui.service')
    files.add(AURA/'tests/framework/test_camera_ui_service.py')
    files.add(AURA/'tests/framework/test_camera_device.py')
    files.add(AURA/'tests/framework/test_board_avatar_worker.py')
    files.add(AURA/'tests/framework/test_local_camera_preview.py')
    files.add(AURA/'tests/framework/test_board_ui_services.py')
    files.add(AURA/'tests/framework/test_board_ui_settings.py')
    files.add(AURA/'README.md')
    for root in ('board', 'common'):
        files.update((AURA/root).rglob('*.py'))
    for name in STAGE_TOOLS:
        files.add(AURA/'tools'/name)
    for root in ('ui', 'common/schemas'):
        files.update((AURA/root).rglob('*.json'))
    for root in ('tools', 'tests', 'tests/framework'):
        init = AURA/root/'__init__.py'
        if init.is_file():
            files.add(init)
    # Formal PNGs and their source manifests/SOPs; RGB565 is unused by GTK.
    files.update(p for p in (AURA/'assets/avatar').rglob('*') if p.is_file() and p.suffix in ('.png', '.json'))
    files.update(p for p in (AURA/'assets/fonts').iterdir() if p.is_file())
    reuse = SHARED/'deliverables/2026-10-06_avatar_reuse'
    files.update((reuse/'preview_script.py', reuse/'emotion_profile.json'))
    files.update((reuse/'candidates').rglob('*.png'))
    blink = SHARED/'deliverables/2026-10-06_voice_blink'
    files.add(blink/'blink_profile.json')
    profile_data = json.loads((blink/'blink_profile.json').read_text(encoding='utf-8-sig'))
    for target in profile_data['targets'].values():
        files.update(blink/row['file'] for row in target['layers'])
    voice = SHARED/'deliverables/2026-10-06_voice_selected_soft_young'
    selection = json.loads((voice/'selection.json').read_text(encoding='utf-8-sig'))
    files.update((voice/'selection.json', voice/'base_model_verification.json', voice/selection['reference_audio']))
    live = SHARED/'deliverables/2026-10-06_xilan_live'
    files.update((live/'index.html', live/'player.js'))
    from board.runtime.character import DEMO_LINES
    from board.runtime.audio.selected_voice import SelectedVoiceSynthesizer
    # Packaging validates existing caches directly; it never needs a live
    # speech worker and cannot start synthesis when a cache is missing.
    cache = SelectedVoiceSynthesizer(live/'cache', voice_root=voice)
    for line in DEMO_LINES:
        record = cache.cached(line['text'])
        if record is None:
            raise RuntimeError('Required board demo audio cache is missing or invalid')
        files.add(Path(record['path']))
        files.add(live/'cache'/(record['key']+'.json'))
    for path in files:
        path.resolve(strict=True).relative_to(SHARED.resolve())
    return sorted(files)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('runtime', 'native-probe'), default='runtime')
    parser.add_argument('--out', type=Path, default=AURA/'artifacts/releases')
    args = parser.parse_args(argv)
    files = collect(args.profile)
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError('Missing deployment files: '+', '.join(missing))
    rows = [{'path':path.relative_to(SHARED).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)} for path in files]
    manifest = {'schema_version':'aura-board-avatar-gtk-1','profile':args.profile,
        'created_at_utc':datetime.now(timezone.utc).isoformat(), 'files':rows,
        'entry':'aura/tools/board_avatar_gtk.py' if args.profile=='runtime' else 'aura/tools/check_gstreamer_clock.py',
        'no_gpu_model_included':True,'camera_model_included':False,
        'camera_adapter_requires_existing_pinned_backend':True,'hardware_or_ui_acceptance_implied':False,
        'scope':'FULL_CACHED_GTK_RUNTIME_REQUIRES_TARGET_LIBRARIES_AND_REAL_DEVICE_ACCEPTANCE' if args.profile=='runtime'
                else 'SOURCE_FOR_NATIVE_NO_AUDIO_DEVICE_PROBES_NOT_COMPLETE_AVATAR_RUNTIME'}
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = args.out/('aura-board-avatar-gtk-'+args.profile+'-'+stamp+'-'+uuid.uuid4().hex[:6]+'.zip')
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for file,row in zip(files,rows):
            archive.write(file,row['path'])
        archive.writestr('runtime_manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(path) as archive:
        assert set(archive.namelist()) == {row['path'] for row in rows}|{'runtime_manifest.json'}
        assert json.loads(archive.read('runtime_manifest.json')) == manifest
        for row in rows:
            raw = archive.read(row['path'])
            assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], row['path']
    result = {'archive':str(path),'bytes':path.stat().st_size,'sha256':digest(path),'profile':args.profile,
              'verified_payload_files':len(rows),'manifest_verified':True,'hardware_or_ui_acceptance_implied':False}
    record = path.with_suffix('.verification.json')
    with record.open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
