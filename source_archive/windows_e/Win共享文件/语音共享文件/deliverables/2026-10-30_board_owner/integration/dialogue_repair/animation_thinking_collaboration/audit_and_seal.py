"""Reproducible local evidence seal; reads only verified public sources."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name,value):
    (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    baseline=json.loads((HERE/'SOURCE_BASELINE.json').read_text(encoding='utf-8'))
    mapping=json.loads(Path(baseline['source_mapping']).read_text(encoding='utf-8'))
    if sha(Path(baseline['source_mapping']))!=baseline['source_mapping_sha256']:
        raise ValueError('v16 source mapping changed')
    if len(mapping['component_pins'])!=378 or mapping['startup_sha256']!=baseline['startup_sha256']:
        raise ValueError('Unexpected production source binding')
    for relative,row in baseline['files'].items():
        if sha(HERE/'before'/relative)!=row['sha256']:
            raise ValueError('Before copy changed: '+relative)
    for path in (HERE/'runtime_v16').rglob('*.py'):
        relative=path.relative_to(HERE/'runtime_v16').as_posix()
        if sha(path)!=mapping['component_pins'][relative]:
            raise ValueError('Public runtime baseline changed: '+relative)
    tests=json.loads((HERE/'TEST_RESULTS.json').read_text(encoding='utf-8'))
    if tests.get('successful') is not True or tests.get('tests_run')!=25:
        raise ValueError('Required local tests have not passed')
    rows={};patches=[]
    for path in sorted((HERE/'candidate').rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(HERE/'candidate').as_posix()
        before=HERE/'before'/relative
        if relative not in baseline['files']:
            raise ValueError('Unexpected candidate path: '+relative)
        rows[relative]=dict(before_sha256=sha(before),after_sha256=sha(path),bytes=path.stat().st_size)
        if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8'))
        if path.suffix=='.py' and tests.get('candidate_python_sha256',{}).get(relative)!=sha(path):
            raise ValueError('Candidate Python does not match the passing test run: '+relative)
        patches.extend(difflib.unified_diff(before.read_text(encoding='utf-8').splitlines(keepends=True),
            path.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='a/'+relative,tofile='b/'+relative))
    if len(rows)!=5:
        raise ValueError('Expected three Python adapters and two native source files')
    (HERE/'changes.patch').write_text(''.join(patches),encoding='utf-8')
    manifest=dict(schema='aura.animation-thinking-source-manifest.v1',
        status='FROZEN_LOCAL_TESTED_NATIVE_BUILD_AND_PREVIEW_PENDING',
        base_root=baseline['root'],base_startup_sha256=baseline['startup_sha256'],
        base_source_manifest_sha256=baseline['source_manifest_sha256'],files=rows,
        patch_sha256=sha(HERE/'changes.patch'),
        no_function_route_files_modified=True,production_modified=False,
        native_library_built=False,paired_selection_resealed=False)
    save('SOURCE_MANIFEST.json',manifest)
    queries={
      'tools/board_avatar_gtk.py':('from tools.formal_yuki import native_controller_type',
          'controller_type=native_controller_type()', 'from tools.formal_native_yuki import prepare_portrait',
          'visual_controller.portrait_offload=self.native_yuki',
          'from tools.formal_yuki import paired_recording_type',
          'from tools.formal_native_yuki import create_gl_area',
          'self.output = GStreamerAudioOutput'),
      'tools/formal_yuki.py':('def native_controller_type', 'dict(RealtimeFacials=NumericFacials)',
          'def paired_recording_type'),
      'tools/formal_native_yuki.py':('class StrictLocalPortrait', 'scoped_function(original.prepare_portrait',
          'original.create_gl_area'),
      'tools/native_yuki.py':('class Control', 'class LocalPortrait', 'playing=bool(self.output.active',
          'def tick_native', 'mailbox.consume()', 'self.native.render'),
      'tools/streaming_controller.py':("if snapshot.get('audible')", 'self.portrait_frame', 'self.output.finished()'),
      'tools/gstreamer_persistent_engine.py':('self.sink.query_position', 'self._observe(position)',
          'start<=now_ns<end', "'clock_source':'GStreamer ALSA sink position query'"),
      'board/runtime/audio/board_dialogue_jobs.py':('raw = self.asr.transcribe', "emit('start'"),
      'tools/board_recording.py':('def _queue_transcription', "state='TRANSCRIBING'",'self._poll_transcription()',
          'result=self.controller.tick()'),
      'tools/production_listening.py':('original_tick = recording._monitor_tick',
          'recording._monitor_tick = monitor_tick','recording.monitor_enabled = settings.read()'),
    }
    trace={}
    for relative,needles in queries.items():
        path=HERE/'runtime_v16'/relative
        lines=path.read_text(encoding='utf-8').splitlines()
        matches=[dict(line=i+1,text=line.strip()) for i,line in enumerate(lines) if any(n in line for n in needles)]
        trace[relative]=dict(sha256=sha(path),production_pin=mapping['component_pins'][relative],matches=matches)
    before_cpp=(HERE/'before/native/yuki_host.cpp').read_text(encoding='utf-8')
    after_cpp=(HERE/'candidate/native/yuki_host.cpp').read_text(encoding='utf-8')
    framing=[line for line in before_cpp.splitlines() if 'view_top=' in line or 'scale=height/' in line or 'renderer->draw(' in line]
    if not all(line in after_cpp for line in framing):
        raise ValueError('Waist framing changed')
    model=HERE.parents[1]/'formal_switch/overlay/aura/assets/yuki/model.runtime.json'
    if sha(model)!=mapping['component_pins']['assets/yuki/model.runtime.json']:
        raise ValueError('Public character model does not match production')
    metadata=json.loads(model.read_text(encoding='utf-8'))['metadata']
    eye=next(row for row in metadata['eyeControl'] if row['label']=='face_eye_open')
    if eye['beginFrame']!=0 or eye['endFrame']!=10 or eye['blinkEnabled']!=1:
        raise ValueError('Pinned eye range differs from native gate contract')
    audit=dict(schema='aura.animation-thinking-call-path.v1',source_trace=trace,
        true_path=['board_avatar_gtk','formal_yuki.native_controller_type / paired_recording_type',
                   'formal_native_yuki.StrictLocalPortrait','native_yuki.LocalPortrait.offer',
                   'native GTK DrawingArea / EGL frame loop','libaura_yuki / YukiControl'],
        audio_clock='GStreamer ALSA sink query_position; answer track and audible interval, never model strings',
        pre_stream_asr_wait='PairedRecording wraps existing TRANSCRIBING state without changing FSM/generation or jobs',
        direct_stream_events='text/audio/end readiness cannot override audible gate',
        native_override='Existing PlaybackInstance variable difference source after author ticks, before prepare_frame; 3 fixed face parameters',
        controls_layout_unchanged=True,stats_layout_unchanged=True,
        protocol_delta='Original expression low byte preserved; eye-policy bits 0x100/0x200; new yuki_control_features export required',
        character_eye_contract=dict(model_sha256=sha(model),parameter='face_eye_open',
            open=eye['beginFrame'],closed=eye['endFrame'],authored_blink_enabled=True),
        controls_ttl_ms=150,steady_timers_added=0,steady_processes_added=0,
        frame_target=16,physical_fps_measured=False,waist_projection_unchanged=True,
        resource_or_texture_modified=False,palette_modified=False,body_timeline_modified=False,
        private_data_read=False,device_access=False,model_inference=False)
    save('CALL_PATH_AUDIT.json',audit)
    helpers=('prepare_sources.py','run_tests.py','build_native_isolated.py','seal_paired_overlay.py',
             'audit_and_seal.py','NATIVE_BASELINE.json','tests/test_thinking_animation.py','tests/native_eye_gate.cpp','REVIEW.txt')
    handoff=dict(schema='aura.animation-thinking-handoff.v1',status=manifest['status'],
        source_manifest_sha256=sha(HERE/'SOURCE_MANIFEST.json'),
        baseline_sha256=sha(HERE/'SOURCE_BASELINE.json'),call_path_audit_sha256=sha(HERE/'CALL_PATH_AUDIT.json'),
        local_tests=tests,files=rows,helper_pins={name:sha(HERE/name) for name in helpers},
        coordinator_thread='01a18bcd-1167-71a0-ba0b-d809148d39d9',
        conflicts=[],function_route_files_modified=[],
        native_build_window_required=True,native_build_script='build_native_isolated.py',
        paired_overlay_script='seal_paired_overlay.py',
        required_next_steps=['Owner re-read current production startup/pins and preserve PAUSED/mic=false',
          'Owner allocate isolated native build window; run build_native_isolated.py against pinned native base',
          'CPU headless native test must pass before generating paired_overlay; this is not a visual/FPS acceptance',
          'Run seal_paired_overlay.py with matching library and build receipt; rerun tests with paired sources',
          'Owner merge only the renderer overlay into the freshest combined candidate and update character_pair selection SHA / source manifest',
          'Owner coordinate one native GTK/EGL preview; no simultaneous display owner, no real dialogue/PCM export',
          'Only the main owner performs any controlled deployment or rollback'],
        not_claimed=['native compilation success','board visual preview','physical 16fps achievement',
                     'acoustic lip-sync acceptance','production deployment'],
        preserved=dict(user_paused=True,microphone=False,audio_input_queue_frames=8,fps_target=16,
            character='御笠雪妃',framing='waist-wine-v1',business_owner='board',
            windows_models='existing 27B and OmniVoice16',model_storage='D:/AIModels'),
        initial_test_fixture_failure='First run retained in TEST_RESULTS_initial.json; safe reset control was unconsumed in readiness test, fixture fixed; no product behavior was weakened',
        device_or_production_actions_performed=False,private_data_exported=False)
    if (HERE/'native_build_source.zip').is_file():
        handoff['native_build_bundle']=dict(path='native_build_source.zip',
            sha256=sha(HERE/'native_build_source.zip'),bytes=(HERE/'native_build_source.zip').stat().st_size)
    save('HANDOFF.json',handoff)
    print(json.dumps(dict(status=handoff['status'],files=len(rows),local_tests=tests['tests_run'],
                         source_manifest_sha256=sha(HERE/'SOURCE_MANIFEST.json'))))


if __name__=='__main__':
    main()
