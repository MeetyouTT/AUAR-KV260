import base64,hashlib,json,urllib.request
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
old=Path('/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2');m=json.loads((old/'candidate-manifest.json').read_text())
g=Path('/home/root/aura-windows-portrait-20261027/handoff-31b0c262c5b74d52966c00b978dfef3f');c=json.loads((g/'startup/config.json').read_text());runtime=Path(c['runtime'])/'aura'
d={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'fdt_sha256':sha('/sys/firmware/fdt'),'fdt_b64':base64.b64encode(Path('/sys/firmware/fdt').read_bytes()).decode(),'old_manifest':m,'old_manifest_sha256':sha(old/'candidate-manifest.json'),'old_runtime_verified':all(sha(p)==s for p,s in m['runtime_files'].items()),'gui_components':len(c['component_sha256']),'gui_components_verified':all(sha(runtime/p)==s for p,s in c['component_sha256'].items()),'pan_manual':json.loads((runtime/'config/pan_manual.local.json').read_text()),'pan_face':json.loads((runtime/'config/pan_face.local.json').read_text()),'dpu_init_source':Path('/etc/init.d/dpu-auto-config').read_text()}
for n in ['manual_release.py','manual_process.py','face_process.py']:
 p=runtime/'board/motion'/n
 if p.exists():d[n]={'sha256':sha(p),'source':p.read_text()}
print(json.dumps(d))
