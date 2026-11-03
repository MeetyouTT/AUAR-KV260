"""Capture only a legacy history prefix, never an exact/final checkpoint."""
import base64,gzip,hashlib,json,os,time,urllib.request
from pathlib import Path
expected_boot='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==expected_boot
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def health():
 with op.open('http://127.0.0.1:8790/health',timeout=4) as stream:return json.load(stream)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
first=health();pid=first['pid'];assert pid==29563
birth=int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19])
runtime=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-vision-recovery-c76110abefc304bb/aura')
manifest={str(p.relative_to(runtime)):sha(p.read_bytes()) for p in sorted(runtime.rglob('*.py')) if p.is_file() and not p.is_symlink()}
assert len(manifest)==214
unit_sha=sha(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes())
assert unit_sha=='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
h=health();assert h['pid']==pid
assert int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19])==birth
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
s=h['dpu_schedule'];assert not s['owner_fenced']
events=s['optional_diagnostics']['fault_events']
for kind,code in [('yunet',1),('sface',2)]:
 relevant=[e for e in events if e['task_code']==code]
 assert len(relevant)==s['optional'][kind]['overruns']
 assert all(e['native_completed']==1 and e['native_status']==0 and e['native_failed']==0 and not e['body_failed'] for e in relevant)
feature=h['identity']['feature_inference']
feature={k:feature[k] for k in ['kind','model_id','ready','requests','execution_attempts','completed','features_returned',
 'deferred','slot_denials','expired_after_admission']}
captured=time.monotonic_ns();manifest_sha=sha(canonical(manifest))
payload={'schema':'aura-legacy-health-prefix-1','boot':boot,'source_pid':pid,'source_birth_ticks':birth,
 'captured_mono_ns':captured,'source_unit_sha256':unit_sha,'source_manifest_sha256':manifest_sha,
 'schedule':s,'feature_inference':feature}
wrapper={'schema':'aura-native-legacy-boot-archive-1','prefix_scope':'legacy_health_prefix_lower_bound',
 'source_boot':boot,'source_pid':pid,'source_birth_ticks':birth,'captured_mono_ns':captured,
 'source_unit_sha256':unit_sha,'source_manifest_sha256':manifest_sha,'source_manifest':manifest,
 'legacy_payload_sha256':sha(canonical(payload)),'legacy_payload':payload}
raw=canonical(wrapper);digest=sha(raw)
destination=Path('/home/root/aura-native-critical-20261024/legacy-prefix')/digest[:16]
destination.mkdir(parents=True,exist_ok=False,mode=0o700)
with (destination/'legacy-boot-archive.json').open('xb') as output:
 output.write(raw);output.flush();os.fsync(output.fileno())
compressed=gzip.compress(raw,mtime=0)
print(json.dumps({'scope':'legacy prefix only; known counters lower bounds, unknown tail, no production mutation',
 'sha256':digest,'path':str(destination/'legacy-boot-archive.json'),'gzip_base64':base64.b64encode(compressed).decode(),
 'faults':{k:s['optional'][k]['overruns'] for k in ('yunet','sface')},'captured_mono_ns':captured,
 'not_a_final_checkpoint':True,'new_boot_use_only':True}))
