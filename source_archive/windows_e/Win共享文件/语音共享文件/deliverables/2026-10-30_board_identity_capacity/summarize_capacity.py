"""Derive capacity assessment from captured evidence; no board mutations."""
import datetime,json,statistics
from pathlib import Path
H=Path(__file__).resolve().parent
def read(name):return json.loads((H/name).read_text(encoding='utf-8'))
s=read('capacity_snapshot.json');micro=read('identity_microprobe.json');disk=read('storage_only_probe.json')
assert all(v['status']=='PASS' and v.get('board_safe_unchanged',v.get('board_guard_before_after_unchanged')) for v in (s,micro,disk))
assert read('storage_runtime_probe.json')['status']=='FAIL'
gib=1024**3;mib=1024**2;memory=s['memory_after'];root=next(v for v in s['disk'] if v['path']=='/')
busy=[v['cpu']['cpu']['busy_percent'] for v in s['samples']]
weights=Path('D:/AIModels/speaker-identity/ecapa')
weight_names=['hyperparams.yaml','embedding_model.ckpt','classifier.ckpt','mean_var_norm_emb.ckpt','label_encoder.txt']
files={name:(weights/name).stat().st_size for name in weight_names}
report=dict(status='ASSESSMENT_COMPLETE_NO_MIGRATION_PERFORMED',
 checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 verdict=dict(identity_database_and_fusion='FEASIBLE_WITH_BACKGROUND_WORKER_AND_EXISTING_CAPS',
  precomputed_voice_vector_matching='FEASIBLE_LIGHT_COMPUTE_NOT_EMBEDDING',
  current_full_windows_ecapa_stack_on_board='NOT_READY_ENVIRONMENT_AND_CPU_BUDGET_UNVERIFIED',
  storage='SUFFICIENT_FOR_BOUNDED_IDENTITY_DATA_NOT_UNBOUNDED_MEDIA_ARCHIVE'),
 observed=dict(board=s['board_model'],cpu_count=s['cpu_count'],
  frequency_khz=s['frequencies_khz'],cpu_busy_percent=s['cpu_usage']['cpu']['busy_percent'],
  cpu_sample_p50_percent=statistics.median(busy),cpu_sample_max_percent=max(busy),
  cpu_idle_core_equivalent=s['cpu_count']*(1-s['cpu_usage']['cpu']['busy_percent']/100),
  memory_total_gib=memory['MemTotal']/gib,memory_available_gib=memory['MemAvailable']/gib,
  cma_total_gib=memory['CmaTotal']/gib,cma_free_gib=memory['CmaFree']/gib,
  ordinary_memory_budget_conservative_gib=(memory['MemAvailable']-memory['CmaFree'])/gib,
  conservative_memory_note='MemAvailable minus CmaFree is a conservative planning allowance, not an exact kernel allocation limit',
  swap_bytes=memory['SwapTotal'],root_total_gib=root['total_bytes']/gib,
  root_available_gib=root['available_bytes']/gib,root_used_gib=root['used_bytes']/gib,
  current_face_database_bytes=s['assets']['actual_face_store']['']['bytes'],
  active_dialogue=False,listening=s['ui_after']['listening'],following=s['ui_after']['automatic_following'],
  ui_actual_fps=s['ui_after']['avatar_display']['fps'],ui_p95_ms=s['ui_after']['avatar_display']['p95_ms'],
  detection_hz=s['camera_after']['detection_hz'],
  primary_overruns_increased=s['camera_after']['dpu_primary_period_overruns']!=s['camera_before']['dpu_primary_period_overruns'],
  thermal_measurement_available=bool(s['temperatures_millidegrees_c'])),
 synthetic_measurements=dict(people=32,temporary_clusters=32,recent_observations=4096,
  links_kib=micro['link_database_page_bytes']/1024,
  anonymous_base_kib=micro['anonymous_base_page_bytes']/1024,
  anonymous_with_observations_mib=micro['anonymous_full_observations_page_bytes']/mib,
  process_peak_rss_mib=micro['process_peak_rss_bytes']/mib,
  lookup_ms=micro['lookup_ms'],vector_comparison=micro['precomputed_vector_comparison'],
  persistent_commit_ms=disk['commit_ms'],temporary_files_removed=disk['temporary_files_removed']),
 proposed_identity_service_budget=dict(status='PLANNING_BUDGET_NOT_MEASURED_SERVICE_PEAK',
  ram_mib=128,persistent_data_mib=100,single_background_worker=True,
  ordinary_observations='deduplicate and batch bounded writes',
  enrollment_confirmations='durable transactions, do not weaken confirmation checks',
  ui_thread='never wait synchronously for writes or feature comparisons',
  no_new_dpu_model=True),
 speaker_inference=dict(current_windows_model_files_bytes=files,
  current_windows_required_model_total_mib=sum(files.values())/mib,
  embedding_checkpoint_mib=files['embedding_model.ckpt']/mib,
  weights_transferred=False,
  current_implementation=['SpeechBrain','PyTorch','torchaudio','webrtcvad','CPU ECAPA 192 dimensions'],
  board_default_python_modules=s['modules_detected'],
  onnx_native_import=disk['existing_onnxruntime'],
  actual_board_neural_embedding_benchmark_performed=False,
  candidate_direction='separate ARM CPU runtime and verified ONNX export; single worker, bounded queue, original identity calibration retained',
  dpu_acceleration='NOT_VALIDATED; do not change active FPGA/VART/model context',
  acceptance_needed=['same public PCM vector similarity versus original implementation',
   '3/6/10-second samples under concurrent camera/display/audio workload',
   'processing time and queue freshness, peak RSS, display long frames and audio underruns',
   'real-person false accept/reject and field calibration']),
 media_storage=dict(pcm16_16khz_mono_bytes_per_second=32000,
  hypothetical_raw_pcm_mib_per_hour=32000*3600/mib,
  hypothetical_raw_pcm_gib_per_day=32000*86400/gib,
  current_policy='raw PCM not persisted; structured identity/summary data only',
  raw_video_capacity_evaluated=False),
 limitations=['30-second current idle-dialogue workload, includes sampler overhead, not peak live dialogue',
  'Memory includes protected CMA; no swap configured',
  'Synthetic SQLite footprint and 12 commits do not prove endurance or power-loss recovery',
  'No DPU utilization collector was enabled; free acceleration capacity is unknown',
  'A found Python module is not proof it can import or run inference',
  'No production identity migration, real biometric transfer, new model or service restart'],
 evidence=['capacity_snapshot.json','identity_microprobe.json','storage_runtime_probe.json','storage_only_probe.json'],
 official_runtime_reference='https://onnxruntime.ai/docs/get-started/with-python')
(H/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'],verdict=report['verdict'],observed=report['observed'],
 measurements=report['synthetic_measurements']),ensure_ascii=True))
