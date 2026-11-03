"""Read pinned public dialogue source only; no project imports/devices/private IO."""
import hashlib
import json
from pathlib import Path

STAGE = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
AURA = STAGE / 'runtime/aura'
EXPECTED_STARTUP = '3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
EXPECTED_UI = 'fc21e6f2ef831442b08966957fa7aeb744a9b74124ee8778edc40397285626cd'
EXPECTED_BOOT = '903cfade-b93c-48fa-804e-379be1967313'
NEW = {'board/runtime/audio/board_dialogue_jobs.py', 'board/runtime/board_dialogue.py',
       'common/profile_access.py', 'tools/realtime_bridge.py'}
PIN_ONLY = {'board/runtime/board_business.py', 'board/runtime/board_speaker_business.py',
            'tools/production_board_business_gui.py', 'tools/board_business_gui.py',
            'tools/production_listening.py', 'tools/board_avatar_gtk.py',
            'tools/voice_first_recording.py', 'tools/handsfree_recording.py',
            'tools/streaming_controller.py', 'tools/formal_yuki.py',
            'tools/production_output_format.py', 'tools/face_pan_controls.py'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


boot = Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()
assert boot == EXPECTED_BOOT
startup_raw = (STAGE / 'startup/config.json').read_bytes()
assert digest(startup_raw) == EXPECTED_STARTUP
startup = json.loads(startup_raw)
pins = startup['component_sha256']
assert len(pins) == 380
ui_raw = (AURA / 'config/board_avatar_gtk.json').read_bytes()
assert digest(ui_raw) == EXPECTED_UI == pins['config/board_avatar_gtk.json']
ui = json.loads(ui_raw)
files = {}
for relative in sorted(NEW | PIN_ONLY):
    path = AURA / relative
    assert path.resolve().is_relative_to(AURA.resolve()) and not path.is_symlink()
    raw = path.read_bytes()
    assert len(raw) < 1024 * 1024 and digest(raw) == pins[relative]
    item = dict(path=str(path), relative=relative, bytes=len(raw), sha256=digest(raw), current_startup_pinned=True)
    if relative in NEW:
        item['text'] = raw.decode('utf-8')
    files[relative] = item
assert (STAGE / 'startup/config.json').read_bytes() == startup_raw
business = ui['board_business']
print(json.dumps(dict(
    schema='aura-current-dialogue-source-readonly-1', boot_id=boot,
    startup_sha256=EXPECTED_STARTUP, startup_component_count=len(pins),
    gui_configuration_sha256=EXPECTED_UI, files=files,
    configuration=dict(
        handsfree_dialogue=ui.get('handsfree_dialogue'), automatic_turns=ui.get('automatic_turns'),
        audio_device=ui.get('audio_device'), entry_mode=business.get('entry_mode'),
        asr_variant=business.get('asr_variant'), asr_threads=business.get('asr_threads'),
        frontend_optimization=business.get('frontend_optimization'), frontend_threads=business.get('frontend_threads'),
        frontend_process=business.get('frontend_process'), frontend_capture_process=business.get('frontend_capture_process'),
        capture_priority_nice=business.get('capture_priority_nice'),
        dialogue_output_format=business.get('dialogue_output_format'),
        data_origin=business.get('data_origin'), retention_enabled=business.get('retention_enabled'),
        resume_saved_conversation=business.get('resume_saved_conversation'),
        speaker_enabled=business.get('speaker', {}).get('enabled'),
        anonymous_speaker_enabled=business.get('speaker', {}).get('anonymous_config', {}).get('enabled')),
    database_opened=False, project_imported=False, device_opened=False,
    model_request_sent=False, gui_or_motion_action_sent=False, board_file_modified=False),
    ensure_ascii=True, indent=2))
