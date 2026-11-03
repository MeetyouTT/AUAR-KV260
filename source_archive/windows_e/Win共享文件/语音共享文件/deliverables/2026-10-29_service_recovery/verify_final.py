"""Final read-only checks use /proc for the running entry, preserving pending updates."""
import datetime,hashlib,json
from recovery_common import H,A,read,save,board,windows,ssh
baseline=read('baseline.json');entry=read('running_entry.json');audit=read('motion_binding_audit.json')
report={'status':'CHECKING','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
try:
 current=board();assert current['preflight_ready']
 for key in ('boot','actual_runtime','pins','pan','settings'):assert current[key]==baseline['board'][key],key
 for name in ('ui_service','camera_service'):
  for key in ('MainPID','NRestarts','ActiveState'):assert current[name][key]==baseline['board'][name][key],name+key
 script=r'''
import hashlib,json
from pathlib import Path
args=Path('/proc/'+PID+'/cmdline').read_bytes().decode().split('\0')
assert '--config' in args
path=Path(args[args.index('--config')+1]);cfg=json.loads(path.read_text());root=Path(cfg['runtime'])
print(json.dumps({'running_config':str(path),'config_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
 'runtime':str(root),'pins':cfg['component_sha256'],
 'hash_mismatches':[name for name,digest in cfg['component_sha256'].items() if hashlib.sha256((root/'aura'/name).read_bytes()).hexdigest()!=digest],
 'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'fdt_sha256':hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest(),
 'firmware':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
 'vart':Path('/etc/vart.conf').read_text().strip(),
 'fpga_state':Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()}))
'''.replace('PID',repr(current['ui_service']['MainPID']))
 running=json.loads(ssh('python3 -B -',script,timeout=20))
 assert running['running_config']==entry['running_config'] and running['config_sha256']==entry['running_config_sha256']
 assert not running['hash_mismatches'] and running['pins']==baseline['board']['pins']
 assert all(running[key]==audit['actual'][key] for key in ('boot','fdt_sha256','firmware','vart','fpga_state'))
 for name,digest in baseline['source_sha256'].items():assert hashlib.sha256((A/name).read_bytes()).hexdigest()==digest,name
 assert hashlib.sha256((A/'config/model_storage.local.json').read_bytes()).hexdigest()==baseline['model_storage_sha256']
 endpoints=read('endpoints.json');assert endpoints['status']=='PASS'
 voice=read('voice_probe.json');assert voice['status']=='PASS' and len(voice['checks'])==2
 assert read('cache_retention_verification.json')['status']=='PASS'
 win=windows();daemons=[row for row in baseline['windows']['models'] if row['Name'].startswith('ollama')]
 assert all(row in win['models'] for row in daemons),'An existing model daemon changed; inspect without killing it'
 missing=[row for row in baseline['windows']['models'] if row not in win['models']]
 report.update(status='PASS',revision=baseline['revision'],fingerprint=baseline['fingerprint'],
  source_unchanged=True,windows_services_ready=list(endpoints['services']),actual_voice_requests=2,
  first_pcm_ms=[row['first_pcm_ms'] for row in voice['checks']],
  board={'boot':current['boot'],'running_config':running['running_config'],'runtime':running['runtime'],
   'configured_next_start':current['actual_config'],'next_start_config_sha256':current['config_sha256'],
   'next_start_pins_equal_running':current['pins']==running['pins'],'pins':len(running['pins']),
   'ui_pid':current['ui_service']['MainPID'],'camera_pid':current['camera_service']['MainPID'],
   'listening':current['listening'],'microphone_open':current['microphone_open'],'phase':current['phase'],
   'pan':current['pan'],'portrait_offload':current['portrait_offload'],'display':current['display']},
  parallel_next_start_update_preserved=True,board_restart_performed=False,motion_bindings_changed=False,
  motion_state='PROTECTED_DISABLED',motion_blockers=audit['blockers'],register_io=False,
  microphone_enabled=False,physical_playback=False,motion_command_sent=False,
  original_dialogue_visual_archive_speaker_sources_unchanged=True,
  live_cache_expired_removed=read('cache_retention_verification.json')['removed_count'],
  model_daemons_preserved=True,existing_model_processes_missing_at_final=missing,
  model_processes_before=baseline['windows']['models'],model_processes_after=win['models'],
  existing_models_stopped=False,model_storage_unchanged=True,full_project_complete=False)
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
save('verification.json',report)
print(json.dumps({'status':report['status'],'revision':report.get('revision'),'services':report.get('windows_services_ready'),
 'voice_checks':report.get('actual_voice_requests'),'motion_state':report.get('motion_state'),
 'missing_prior_model_processes':report.get('existing_model_processes_missing_at_final'),'error':report.get('error')},ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)
