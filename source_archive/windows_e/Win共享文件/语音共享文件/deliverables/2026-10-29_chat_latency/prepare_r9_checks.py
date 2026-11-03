"""Separate receipts for the cache-release candidate; do not overwrite r8 evidence."""
from pathlib import Path
H=Path(__file__).resolve().parent
source=(H/'approve_test_receipt_r8.py').read_text(encoding='utf-8')
source=source.replace('r8','r9').replace('347','355')
(H/'approve_test_receipt_r9.py').write_text(source,encoding='utf-8')
source=(H/'live_controls_acceptance_r8.py').read_text(encoding='utf-8')
for left,right in [('deployment_r8.json','deployment_r9.json'),('live_controls_acceptance.json','live_controls_acceptance_r9.json'),
 ('cleanup_public_probe.py','cleanup_public_probe_r9.py'),('public_probe_cleanup.json','public_probe_r9_cleanup.json')]:source=source.replace(left,right)
source=source.replace("playback_ack_sent=False)","playback_ack_sent=False,tts_cache_hits=end.get('tts_cache_hits',0))")
(H/'live_controls_acceptance_r9.py').write_text(source,encoding='utf-8')
source=(H/'cleanup_public_probe.py').read_text(encoding='utf-8')
source=source.replace('live_controls_acceptance.json','live_controls_acceptance_r9.json').replace('public_probe_cleanup.json','public_probe_r9_cleanup.json')
(H/'cleanup_public_probe_r9.py').write_text(source,encoding='utf-8')
source=(H/'verify_release_r8.py').read_text(encoding='utf-8')
for left,right in [('source_plan_r8.json','source_plan_r9.json'),('deployment_r8.json','deployment_r9.json'),
 ('live_handoff_r8_final.json','live_handoff_r9_final.json'),('live_controls_acceptance.json','live_controls_acceptance_r9.json'),
 ('voice_refined.json','voice_trimmed.json'),('tests_passed=347','tests_passed=355')]:source=source.replace(left,right)
source=source.replace("'memory_source_coverage'):assert", "'memory_source_coverage','idle_tts_cuda_cache_release'):assert")
source=source.replace("latency_options=health['latency_options'],voice_request_diagnostics", "tts_cuda_idle_cache=health['dependencies']['tts'].get('cuda_idle_cache',{}),\n  latency_options=health['latency_options'],voice_request_diagnostics")
(H/'verify_release_r9.py').write_text(source,encoding='utf-8')
for name in ('approve_test_receipt_r9.py','live_controls_acceptance_r9.py','cleanup_public_probe_r9.py','verify_release_r9.py'):
 compile((H/name).read_text(encoding='utf-8'),name,'exec')
print('r9 validation scripts prepared with independent receipts')
