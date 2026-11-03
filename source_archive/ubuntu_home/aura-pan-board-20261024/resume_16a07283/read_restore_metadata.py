import hashlib,json,os,subprocess
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5')
meta=json.loads((OPS/'meta.json').read_text());cfg=Path(meta['candidate_config']);value=json.loads(cfg.read_text())
native=value['native_execution'];checkpoint=Path(native['checkpoint_output']);cp=json.loads(checkpoint.read_text()) if checkpoint.exists() else None
gui=json.loads((N/'startup/config.json').read_text());aura=N/'runtime/aura';pins=gui['component_sha256']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
print(json.dumps(dict(boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),candidate_config=str(cfg),
 candidate_config_sha256=sha(cfg),checkpoint=str(checkpoint),native_manifest_sha256=native['source_manifest_sha256'],
 native_unit_sha256=native['source_unit_sha256'],checkpoint_boot=cp['seed'].get('boot_id') if cp else None,
 checkpoint_source_pid=cp['seed'].get('source_pid') if cp else None,checkpoint_sha256=sha(checkpoint) if cp else None,
 old_gui_config_sha256=sha(N/'startup/config.json'),gui_pins=len(pins),gui_pins_valid=all(sha(aura/n)==h for n,h in pins.items()),
 database_path=json.loads((Path('/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2')/'payload.json').read_text())['baseline']['database_path'],
 ARM=0,COMMIT=0)))
