import datetime,json,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent
def get(url):
    with urllib.request.urlopen(url,timeout=5) as response:return json.load(response)
voice=get('http://192.168.50.1:8792/health');hub=get('http://127.0.0.1:8812/health')
expected=json.loads((H/'observation_installation.json').read_text(encoding='utf-8'))['fingerprint']
assert voice['ready'] and not voice['busy'] and voice['source_fingerprint']==expected
assert hub['speaker_ready']
v=dict(status='READY_FOR_CALIBRATION_NOT_FINAL',voice_health=voice,hub_health=hub,
 checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),gpu_policy='observe',
 initial_startup_failure_retained='observation_ready.json',new_anonymous_binding_not_yet_integrated=True)
(H/'observation_ready_env_fixed.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':v['status'],'revision':voice['service_revision'],'gpu_mode':voice['gpu_coordination']['mode'],
 'tts_warmup_reserved_peak_bytes':voice['gpu_coordination']['tts_stats']['warmup_inference']['peak_reserved_bytes']}))
