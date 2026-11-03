from pathlib import Path
import hashlib,json,zipfile
phase=Path('/home/root/aura-yuki-validation-20261030/native_integration');out=phase/'paired_ab'
basis=json.loads((phase/'board_source/manifest.json').read_text());runtime=Path(basis['runtime'])
config=json.loads((runtime/'aura/config/board_avatar_gtk.json').read_text())
info={'portrait_config':{k:v for k,v in config['portrait_offload'].items() if k in ('enabled','host','port','revision','fps','max_age_ms')},'gpu':{}}
for name in ('utilization_pp','utilization_gp','utilization_gp_pp','gpu_memory','version'):
    path=Path('/sys/kernel/debug/mali')/name
    try:
        data=path.read_text();assert len(data)<12000 and '\0' not in data
        info['gpu'][name]=data
    except Exception as error:info['gpu'][name]={'error':str(error)}
names=['board/runtime/portrait_offload.py','common/portrait_wire.py']
with zipfile.ZipFile(out/'fresh-portrait-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
    info['source_hashes']={}
    for name in names:
        data=(runtime/'aura'/name).read_bytes();info['source_hashes'][name]=hashlib.sha256(data).hexdigest();archive.writestr(name,data)
    archive.writestr('gpu-transport.json',json.dumps(info,indent=2))
(out/'gpu-transport.json').write_text(json.dumps(info,indent=2));print(json.dumps(info))
