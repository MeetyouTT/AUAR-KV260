"""Seal completed local evidence; no deployment or runtime side effects."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[3]


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def json_write(name, value):
    (ROOT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    tests = json.loads((ROOT/'contract_tests.json').read_text())
    if not tests['success'] or tests['tests'] < 27:
        raise ValueError('Complete current synthetic contracts before sealing')
    spec = importlib.util.spec_from_file_location('yuki_source_review', ROOT/'review_candidate.py')
    review = importlib.util.module_from_spec(spec); spec.loader.exec_module(review)
    public = review.verify()
    json_write('public_preflight.json', public)
    manifest = json.loads((ROOT/'candidate/manifest.json').read_text(encoding='utf-8'))
    receipt = json.loads((ROOT/'build_receipt.json').read_text())
    aura = ROOT/'candidate/aura'
    pins = {path.relative_to(aura).as_posix(): digest(path) for path in sorted(aura.rglob('*')) if path.is_file()}
    json_write('component_pins.json', dict(schema_version=1, root='candidate/aura', pins=pins,
        merge_rule='Root publisher unions these explicit pins with the freshly verified actual-r3 non-Python resources; never drop existing protected pins or publish from this file alone.'))
    native = PROJECT/'deliverables/2026-10-30_yuki_native_validation/native_integration/replacement_planning'
    parent_pin = dict(
        path='/home/root/aura-board-owner-candidate-20261030/private-pin-8100a7fd-restored260102-20261030/face_gallery_readback.local.json',
        sha256='8c0d859d22bf723fb2afdf503b1e9c9a7eb858d784e68d85a3c71560bd1e1e6b')
    handoff = dict(schema_version=1, status='SOURCE_CANDIDATE_FROZEN_NOT_SELECTED',
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), owner='win_inference', hardware_publisher='root_only',
        scope='Independent candidate GTK/native/business hooks and builder; existing main/default/core/memory/modelhost untouched.',
        pair=dict(profile_version='xuefei-yuki-board-v1-candidate', display_name='雪妃', formal_name='御笠雪妃',
            romanized_name='YUKI MIKASA', render_profile_id='fuyukiss-yuki-freemote39-frame-mesh',
            render_source_profile_sha256='b7b71396c267db80a44c2b32df4ba53ded7920ac952b2fbbfebafba349f85f55',
            persona_config_sha256='33d2dbb87348591da9e288bb9867a8e246fa63a955c071236eeeb24688e2d536',
            prompt_utf8_bytes=978, prompt_sha256='11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e',
            review234byte_fragment_appended=False, startup_only=True, hot_switch=False),
        inputs=dict(business_source_fingerprint=manifest['source_business_fingerprint'], source_python_count=310,
            source_archive_sha256=manifest['source_archive_sha256'], fresh_runtime=manifest['fresh_runtime'],
            native_archive_files=527, native_archive_sha256=manifest['native_archive_sha256'],
            latest_gui_manifest_sha256=digest(ROOT.parent/'resume_runtime/gui_candidate_manifest.json'),
            fresh_source_manifest_sha256=digest(ROOT.parent/'resume_runtime/fresh_source/manifest.json'),
            persona_handoff_sha256=digest(PROJECT/'deliverables/2026-10-30_board_owner/character_persona_candidate/HANDOFF.json'),
            character_source_registry_sha256=digest(native/'source_registry.json'),
            character_replacement_plan_sha256=digest(native/'REPLACEMENT_PLAN.txt')),
        artifacts=dict(source_zip='yuki_business.source_candidate.zip', source_zip_sha256=receipt['zip_sha256'],
            source_zip_bytes=receipt['zip_bytes'], source_manifest='candidate/manifest.json',
            source_manifest_sha256=receipt['manifest_sha256'], candidate_files=receipt['files'],
            python_files=receipt['python_files'], patch='candidate/business_native.patch',
            component_pins='component_pins.json', review='REVIEW.txt'),
        safe_entry=dict(script='review_candidate.py', starts_gui=False, constructs_business_runtime=False,
            calls_service=False, reads_private_metadata=False, reads_identity_db=False, loads_native_library=False,
            note='Only public local byte/AST/pin/ELF checks; actual future GUI constructor is outside this safe preflight.'),
        composition=dict(gtk_widget_and_egl_child=1, target_fps=16, fallback8=False, portrait_offload=False,
            legacy_png_preload_and_composition=False, old_native_pixel_sink=False,
            board_factory_preserved=True, personal_profile_grants_rebuilt=False, identity_guide_preserved=True,
            original_full_pcm_ack_bridge=True, playback_rate=24000, playback_channels=1,
            pause_cancel_sample_clock_methods_inherited=True, private_namespace_binds_before_workers=True,
            shared_globals_mutated=False, microphone_starts_enabled=False,
            microphone_choice='RAM-only false; future explicit operator action required',
            render_ready='first successful local EGL swap, not merely CDLL/create',
            render_lost='invalidate jobs/audio generation; reject new ASR and background idle; no persona/fps fallback'),
        private_readback_future_parameter=dict(config_field='board_business.face_readback', value=parent_pin,
            source='Parent supplied actual_sameboot_written.json; metadata not read by this task',
            observed_parent_boot='8100a7fd-0c6a-46c4-82b8-f874988a1521', observed_parent_camera_pid=260102,
            observed_parent_camera_birth='784437', must_reverify_before_future_use=True, implicit_old_config_fallback=False),
        performance_baseline=dict(fft='original730de47cb unchanged', nice=0, raw_capture_queue_frames=8,
            bufferreuse_or_iobinding_diagnostic_monkeypatch=False, camera_period_changed=False,
            process_or_thread_priority_changed=False, source_only_no_new_performance_claim=True),
        dependencies=dict(native_elf=public['native'], ctypes_libraries=['libX11.so.6','libEGL.so.1'],
            gui='Existing GTK3/GdkX11/PyGObject on board, single publisher',
            assets='Fresh actual-r3 layout/font/service/settings/approved voice resources must be independently pinned by root; not a full non-Python runtime mirror',
            voice='Same existing27B/OmniVoice16/reference voice; no new model, steps, quantization or voice',
            new_greeting='New DEMO_LINES text is paired, but its cached_only demo audio has not been generated/accepted; do not relabel old audio',
            public_cues='Old-character self-introduction cue metadata is rejected. Root must review any new cue via the existing voice chain in a separately authorized step'),
        conflicts_and_gates=[
            'Do not overwrite newer business GTK with the old native package overlay; use generated patch only on the exact pinned source, otherwise rebase.',
            'Static default character/aliases remain byte-exact for the old default. This new instance uses dynamic pair hooks; legacy paths are not a second selected character.',
            'Whole source contains307 unchanged core Python files; component_pins must be merged with fresh actual-r3 resource pins before any future staging.',
            'Root alone may publish; idle/cancel existing owners, normal old GUI exit, then new complete paired process. Rollback restores whole pair and invalidates stale generation; never roll back user DB.',
            'Private face source must be current sameboot/camera birth/source. Future owner or boot changes invalidate the supplied candidate pin; no stale fallback.',
            'No actual GTK/GLES library load, device/source process inspection, ASR/model inference, real wake pronunciation/personality, playback, identityDB access or matched performance acceptance was run.',
            'Future matched full-business16fps validation must cover person-present/absent, original8framequeue capacity, ACK/pause/cancel/mouth clocks and CPU/PSS/Mali. Prior independent nice-10/camera200 evidence is not this candidate.'
        ],
        validation=dict(tests=tests['tests'], failures=tests['failures'], errors=tests['errors'],
            seconds=tests['elapsed_seconds'], new_live_threads=tests['new_live_threads'],
            report='contract_tests.json', report_sha256=digest(ROOT/'contract_tests.json'),
            junit='contract_tests.xml', junit_sha256=digest(ROOT/'contract_tests.xml'),
            safe_preflight='public_preflight.json', safe_preflight_sha256=digest(ROOT/'public_preflight.json')),
        operations=dict(board_calls=0, service_calls=0, gui_launches=0, model_calls=0, subprocess_model_starts=0,
            processes_stopped=0, microphone_opens=0, actual_playbacks=0, identity_db_reads=0,
            original_services_changed=False, production_entry_changed=False, private_data_or_llm_weights_included=False))
    json_write('HANDOFF.json', handoff)
    excluded = {'source_manifest.json','seal_receipt.json','yuki_business.review_candidate.zip'}
    files = {path.relative_to(ROOT).as_posix(): dict(sha256=digest(path), bytes=path.stat().st_size)
             for path in sorted(ROOT.rglob('*')) if path.is_file() and path.name not in excluded and '__pycache__' not in path.parts}
    json_write('source_manifest.json', dict(schema_version=1, status=handoff['status'], files=files))
    target = ROOT/'yuki_business.review_candidate.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            archive.write(ROOT/name, name)
        archive.write(ROOT/'source_manifest.json','source_manifest.json')
    sealed = dict(status=handoff['status'], tests=tests['tests'],
        source_zip_sha256=receipt['zip_sha256'], review_zip_sha256=digest(target), review_zip_bytes=target.stat().st_size,
        handoff_sha256=digest(ROOT/'HANDOFF.json'), source_manifest_sha256=digest(ROOT/'source_manifest.json'))
    json_write('seal_receipt.json', sealed)
    print(json.dumps(sealed))


if __name__ == '__main__':
    main()
