"""Read current owners and pinned source first; never resume listening, query private rows or infer identities."""
import math

def num(obj,keys):
 if not isinstance(obj,dict):return {}
 return {k:obj.get(k) if type(obj.get(k)) is bool or type(obj.get(k)) in (int,float) and math.isfinite(obj[k]) else None for k in keys}
def enum(value,allowed):return value if isinstance(value,str) and value in allowed else 'UNKNOWN'
def fp(pid):
 path=Path('/proc')/str(pid);fields=(path/'stat').read_text().rsplit(')',1)[1].split()
 return dict(pid=pid,birth_ticks=int(fields[19]),parent_pid=int(fields[1]),command_sha256=digest(path/'cmdline'))
def main_pid(unit):
 p=subprocess.run(['systemctl','show',unit,'--property=MainPID,ActiveState,SubState,Job','--no-pager'],capture_output=True,text=True,timeout=5)
 assert p.returncode==0
 row=dict(x.split('=',1) for x in p.stdout.splitlines() if '=' in x)
 return int(row['MainPID']),dict(active=enum(row.get('ActiveState'),{'active','inactive','failed','activating','deactivating'}),
                               substate=enum(row.get('SubState'),{'running','dead','failed','start','stop'}),job_present=bool(row.get('Job')))
def optional_model_health():
 c=http.client.HTTPConnection('192.168.50.1',8797,timeout=3)
 try:
  c.request('GET','/health');r=c.getresponse();data=r.read(262145);assert r.status==200 and len(data)<=262144
  h=json.loads(data);backend=h.get('backend',{});gpu=backend.get('gpu_coordination',{});res=gpu.get('llm_residency',{})
  return dict(available=True,role=enum(h.get('role'),{'model_inference_only'}),**num(h,('ok','active','pending','request_logging')),
              backend=num(backend,('tts_ready','llm_ready','num_step')),
              llm_residency=num(res,('available','llm_resident','llm_gpu_resident','fresh','age_ms')),
              voice=num(backend.get('voice',{}),('alive','request_active','quarantined','closed')),
              counters=num(h.get('counts',{}),('accepted_llm','accepted_tts','completed','cancelled')),request_kind='HEALTH_GET_ONLY')
 except Exception as exc:return dict(available=False,error_class=type(exc).__name__,request_kind='HEALTH_GET_ONLY')
 finally:c.close()

checks={};boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();checks['boot_matches_spec']=boot==SPEC['boot_id']
v=get_json(8783,'/api/state');h=get_json(8790,'/health')
camera,camera_unit=main_pid('aura-camera-ui.service');supervisor,gui_unit=main_pid('aura-avatar-ui.service')
gtk=document(BUSINESS/'runtime/launch.json')['pid']
owners={role:fp(pid) for role,pid in (('camera',camera),('supervisor',supervisor),('gtk',gtk))}
checks['current_owner_relationships']=(camera==h.get('pid') and owners['gtk']['parent_pid']==supervisor
                                     and camera_unit['active']=='active' and gui_unit['active']=='active'
                                     and not camera_unit['job_present'] and not gui_unit['job_present'])
actual_start=digest(BUSINESS/'startup/config.json');actual_manifest=digest(BUSINESS/'production_source_manifest.json')
startup=document(BUSINESS/'startup/config.json');manifest=document(BUSINESS/'production_source_manifest.json')
pins=startup['component_sha256'];mismatches=[relative for relative,pin in pins.items() if digest(BUSINESS/'runtime/aura'/relative)!=pin]
checks['startup_matches_spec']=actual_start==SPEC['startup_sha256'];checks['manifest_matches_spec']=actual_manifest==SPEC['source_manifest_sha256']
checks['source_380_matches']=len(pins)==380 and pins==SPEC['component_sha256']==manifest['component_pins'] and not mismatches
source_sha=digest(BUSINESS/'runtime/aura/tools/production_memory_presentation.py')
checks['de04_current']=source_sha=='de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2'
wide_error=None
try:wide_active();verify_wide_files();wide_ok=True
except Exception as exc:wide_ok=False;wide_error=type(exc).__name__
checks['wide_firmware_vart_and_files_match']=wide_ok
fdt=digest('/sys/firmware/fdt');checks['fdt_matches']=fdt=='aed6f0cbe5184a6eed38449731e92106b923573cb324fa4c68079fdb5bbfd53e'
cfg=document(BUSINESS/'runtime/aura/config/board_avatar_gtk.json');face_ref=cfg['board_business']['face_readback']
checks['gui_configuration_matches']=digest(BUSINESS/'runtime/aura/config/board_avatar_gtk.json')==SPEC['configuration_sha256']
checks['face_readback_matches']=face_ref==SPEC['face_readback'] and digest(face_ref['path'])==face_ref['sha256']
binding=document(face_ref['path'])
checks['camera_binding_matches_discovered_owner']=(binding.get('board_boot_id')==boot and binding.get('camera_pid')==camera
 and str(binding.get('camera_start_ticks'))==str(owners['camera']['birth_ticks'])
 and binding.get('camera_cmdline_sha256')==owners['camera']['command_sha256'])
camera_pins=binding.get('source_sha256',{});checks['camera_source_pins_match']=len(camera_pins)==23 and all(digest(path)==pin for path,pin in camera_pins.items())
manual=document(BUSINESS/'runtime/aura/config/pan_manual.local.json');face=document(manual['face_follow_config']);control=Path(face['release_root'])
controller=document(control/'deployment-manifest.json')
checks['original_25_controller_matches']=(control==Path('/home/root/aura-pan-wide-20261028/control-10282601') and len(controller['files'])==25
 and digest(control/'deployment-manifest.json')==face['manifest_sha256']=='5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562'
 and all(digest(row['destination'])==row['sha256'] for row in controller['files']))
pan=v.get('manual_pan',{});rb=pan.get('readback') or {};hf=v.get('handsfree_dialogue',{})
checks['motion_output_closed']=(pan.get('automatic_following') is False and rb.get('flags')==0 and rb.get('lease_left_ms')==0
 and rb.get('active') is False and rb.get('armed') is False)
preference=document('/home/root/.local/share/aura-board-business/listening_preference.json')
checks['saved_and_current_paused']=(preference=={'version':1,'enabled':False} and hf.get('state')=='PAUSED'
 and hf.get('enabled') is False and hf.get('microphone_open') is False and v.get('playing') is False)
busy=(v.get('phase') in ('THINKING','SPEAKING') or v.get('playing') is True or v.get('pending_job') is not None
 or v.get('local_transcription',{}).get('state') in ('TRANSCRIBING','GENERATING','PLAYING'))
checks['no_foreground_job_busy']=not busy
business=v.get('board_business',{});memory=business.get('memory',{});retention=business.get('retention',{});clock=business.get('clock',{});speaker=business.get('speaker',{})
checks['gui_and_camera_errors_clear']=(v.get('runtime_faults',{}).get('count')==0 and v.get('avatar_renderer',{}).get('worker_faults',{}).get('count')==0
 and h.get('camera_error')==h.get('detector_error')==h.get('identity',{}).get('error')=='' and h.get('dpu_schedule',{}).get('owner_fenced') is False)
checks['business_retention_clock_speaker_available']=(business.get('started') is True and business.get('closed') is False
 and memory.get('running') is True and not memory.get('error') and retention.get('enabled') is True and retention.get('running') is True
 and clock.get('safe_for_compaction') is True and speaker.get('ready') is True)
model=optional_model_health();checks['model_service_and_tts_ready']=(model.get('available') is True and model.get('ok') is True
 and model.get('role')=='model_inference_only' and model.get('backend',{}).get('tts_ready') is True)
service=v.get('local_transcription',{}).get('service',{});front=v.get('audio_frontend',{}).get('current',{})
asr=dict(transcription_state=enum(v.get('local_transcription',{}).get('state'),{'IDLE','DISABLED','CANCELLED','ANSWERED','TRANSCRIBING','GENERATING','PLAYING','ERROR'}),
         service=num(service,('enabled','ready','available','feedback_ready','asr_ready','frontend_ready','model_ready','board_owned')),
         frontend=num(front,('ready','available','running','worker_alive','model_ready','asr_ready','process_ready','frontend_ready')),
         configured_variant='PARAFORMER_SMALL' if cfg['board_business'].get('asr_variant')=='paraformer_small' else 'UNKNOWN',
         configured_threads=cfg['board_business'].get('asr_threads'),error_present=bool(v.get('local_transcription',{}).get('error')),
         warmup_or_decode_executed=False)
result=dict(schema='aura-resumed-summary-acceptance-preflight-1',status='PASS_PAUSED_PLAN_PREPARATION_READY' if all(checks.values()) else 'PRECHECK_REQUIRES_REVIEW',
 observed_mono=time.monotonic(),boot_id=boot,startup_sha256=actual_start,manifest_sha256=actual_manifest,component_pins=len(pins),source_sha256=source_sha,
 configuration_sha256=digest(BUSINESS/'runtime/aura/config/board_avatar_gtk.json'),checks=checks,failed_checks=[k for k,x in checks.items() if not x],
 owners_discovered_fresh=owners,prior_pids_used_as_lookup=False,units=dict(camera=camera_unit,gui=gui_unit),component_mismatch_count=len(mismatches),
 firmware=firmware(),fdt_sha256=fdt,wide_validation_error_class=wide_error,
 state=dict(page=enum(v.get('ui_page'),{'main','vision','settings'}),phase=enum(v.get('phase'),{'IDLE','THINKING','SPEAKING','ACTION'}),
             foreground_job_busy=busy,listening_state=enum(hf.get('state'),{'PAUSED','WAITING_SPEECH','CONVERSATION','WAITING_SERVICE','COOLDOWN'}),
             listening_enabled=hf.get('enabled'),microphone_open=hf.get('microphone_open'),playing=v.get('playing'),saved_preference_enabled=preference.get('enabled'),
             following=pan.get('automatic_following'),pan_state=enum(pan.get('state'),{'READY','FAULT','MOVING','STOPPING'}),readback=num(rb,('flags','width_us','lease_left_ms','active','armed','bound','referenced'))),
 asr=asr,model=model,memory=dict(metrics=num(memory,('running','completed','discarded','model_calls_inside_transaction')),error_present=bool(memory.get('error')),
                              retry=num(memory.get('retry_backoff'),('failure_streak','retry_in_seconds','last_delay_seconds','skipped_for_cooldown'))),
 retention=num(retention,('enabled','running','initial_retention_enabled')),
 clock=dict(metrics=num(clock,('anchored','same_boot','event_time_available','persistent','safe_for_compaction','verified_age_seconds','anchor_age_seconds','uncertainty_seconds')),
            quality=enum(clock.get('quality'),{'VERIFIED','verified','BOUNDED','bounded','ANCHORED','anchored','safe','TRUSTED'})),
 speaker=num(speaker,('ready','active','speaker_calibrated','automatic_profile_access','pcm_persisted','single_cpu_worker','queued_or_active')),
 faults=dict(gui=v.get('runtime_faults',{}).get('count'),renderer=v.get('avatar_renderer',{}).get('worker_faults',{}).get('count'),
             native_primary_period_overruns=h.get('dpu_schedule',{}).get('primary_period_overruns'),owner_fenced=h.get('dpu_schedule',{}).get('owner_fenced')),
 can_continue_plan_preparation=all(checks.values()),live_window_started=False,microphone_or_motion_command_sent=False,
 private_database_or_previous_bodies_opened=False,identity_registered=False,performance_sample_started=False,
 readiness_limits=['ASR/model states are reported metadata only; no synthesis, decode or inference warmup was sent.',
                   'Missing explicit ASR or LLM ready fields remain null; prior real voice acceptance is historical.',
                   'This receipt supports plan preparation while paused; it does not start the proposed retention test.'])
print(json.dumps(result,allow_nan=False))
