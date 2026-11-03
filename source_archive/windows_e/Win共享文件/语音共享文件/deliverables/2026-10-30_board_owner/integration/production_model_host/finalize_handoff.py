"""Local metadata/source sealing only. No model/service/device/DB operation."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()

changed=['start_inference.ps1','stop_inference.ps1','aura/config/model_inference.local.json',
    'aura/tools/model_inference_startup.py','aura/tests/framework/test_model_inference_startup.py']
owned=[str(p.relative_to(PROJECT)).replace('\\','/') for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.ps1','.txt')]
dependencies=['aura/tools/model_inference_host.py','aura/common/model_inference_wire.py',
    'aura/tools/voice_worker_transport.py','aura/tools/owned_speech_process.py','aura/tools/service_instance_lock.py',
    'aura/tools/voice_startup_guard.py','aura/common/gpu_coordination.py','aura/tools/dialogue_host_ollama.py',
    'aura/board/runtime/audio/omnivoice_voice.py','aura/board/runtime/audio/selected_voice.py',
    'aura/config/board_dialogue_model.json','aura/config/model_storage.local.json',
    'aura/config/gpu_runtime.local.json','aura/config/ollama_runtime.local.json',
    'deliverables/2026-10-18_board_dialogue/project_ollama.py','aura/tools/model_runtime_dashboard.py']
files={}
for name in dict.fromkeys(changed+owned+dependencies):
    path=PROJECT/name;raw=path.read_bytes()
    if path.suffix=='.py':ast.parse(raw,feature_version=(3,9))
    files[name]=dict(bytes=len(raw),sha256=sha(raw),role='changed_or_added' if name in changed+owned else 'unchanged_dependency')
manifest=dict(schema='aura.production-model-host.source_manifest.v1',files=files)
(HERE/'source_manifest.json').write_bytes(encoded(manifest))
ready=json.loads((HERE/'actual_ready.json').read_bytes())
snap=json.loads((HERE/'dashboard_snapshot.json').read_bytes())
tasks={row['id']:row for row in snap['samples'][-1]['tasks']}
assert ready['main_pid'] in tasks['host']['pids'] and ready['tts_pid'] in tasks['tts']['pids']
assert ready['fixed_daemon_pid'] in tasks['llm']['pids']
assert all(v['model_health_available'] is True for v in snap['samples'])
assert sha((PROJECT/'start_voice.ps1').read_bytes())=='90b8510e00b5877d7ef21551c4e47c8d87ed69c4e6ff2621199e22c65f8251b0'
assert sha((PROJECT/'deliverables/2026-10-18_board_dialogue/start_background_models.ps1').read_bytes())=='2a6a2fc4fedda0428b481ccc571b5d0a1b0397d0fc55fac0543833f9cb35e47a'
handoff=dict(status='WINDOWS_MODEL_ONLY_PERSISTENT_READY_DEFAULT_BUSINESS_GATE_PENDING',
    role='model_inference_only',session_id=ready['session_id'],main_pid=ready['main_pid'],
    launcher_pid=ready['launcher']['pid'],tts_pid=ready['tts_pid'],fixed_daemon_pid=ready['fixed_daemon_pid'],
    endpoint='http://192.168.50.1:8797',allowed_inference_peers=['192.168.50.2'],lifetime_seconds=None,
    health_verified=True,start_idempotent_verified=True,unique_ram_tts_workers=1,
    fixed_model='aura-qwen3.8-27b-abliterated:iq4_xs',tts='OmniVoice',num_step=16,
    caller_owned_messages=True,business_database_opened=False,raw_audio_archived=False,
    model_weights_copied=False,other_models_stopped=False,legacy_services_started=False,
    gpu_guard_changed=False,total_startup_deadline_seconds=300,
    corrected_subbudget='TTS now uses same original absolute300s deadline; previous artificial120s deadline removed',
    real_stop_restart_after_ready_exercised=False,
    stop_semantics='normal stop closes this host/TTS; explicit idle same-owner restart additionally releases its loaded fixed27B',
    dashboard=dict(new_window_opened=False,private_screenshot_taken=False,snapshot=str(HERE/'dashboard_snapshot.json'),
        host_main_recognized=True,tts_family_recognized=True,fixed27b_recognized=True),
    validation=dict(fake_lifecycle_tests=7,startup_budget_tests=7,actual_tts_first_fixed27b_ready=True,
        existing_dashboard_metadata_samples=3,additional_generation_or_performance_test=False),
    pending=dict(default_wrapper_applied=False,legacy_background_gate_applied=False,
        business_owner_marker_applied=False,requires_root_single_writer_handover_manifest=True),
    source_manifest_sha256=sha((HERE/'source_manifest.json').read_bytes()),
    evidence={'actual_ready.json':sha((HERE/'actual_ready.json').read_bytes()),
        'dashboard_snapshot.json':sha((HERE/'dashboard_snapshot.json').read_bytes()),
        'before.json':sha((HERE/'before.json').read_bytes()),
        'business_gate_prepared.json':sha((HERE/'business_gate_prepared.json').read_bytes())})
(HERE/'HANDOFF.json').write_bytes(encoded(handoff))
print(json.dumps(dict(status=handoff['status'],source_manifest_sha256=handoff['source_manifest_sha256'],
    handoff_sha256=sha((HERE/'HANDOFF.json').read_bytes())),sort_keys=True))
