from pathlib import Path
import json,subprocess,hashlib,sys,re
from datetime import datetime,timezone,timedelta
sys.stdout.reconfigure(encoding='utf-8')
B=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5')
S=Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-11-03_scheme_a_source_release_9a4f')
R=B/'self_audit_latest_package';R.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rar=S/'最终工程包/auar_xuefei_source.rar'
expected='022422d9d1efa6106c2b247ac901dddd2f439a1a5e8eb19a22539010c3a944f4'
assert sha(rar)==expected
code=r'''
from pathlib import Path
import hashlib,json
base=Path('/home/ghmd/auar-scheme-a-9a4f-20261103-01a1a08b/verification/final-roundtrip02')
root=base/'expanded/auar_xuefei'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(base/'auar_xuefei_source.rar')=='022422d9d1efa6106c2b247ac901dddd2f439a1a5e8eb19a22539010c3a944f4'
checked=[];bad=[]
for line in (root/'checksums.sha256').read_text().splitlines():
 if not line.strip():continue
 h=line[:64];name=line[66:];p=(root/name).resolve();p.relative_to(root.resolve())
 ok=p.is_file() and sha(p)==h
 checked.append(name)
 if not ok:bad.append(name)
assert not bad,bad
names=['README.md','build/env.json','build/reproduce.py','board/stage.py','board/readme.md','board/deploy.json','board/release_9a4f.json','board/camera_release.json','src/models/readme.md','src/models/inputs/board_audio_dependencies.json','third_party_notices.md','license','report/validation_summary.md','report/evidence/hardware_results.json','report/evidence/implementation_receipt.json','report/evidence/model_build.json','report/evidence/native_build.json','report/evidence/firmware_fresh.json','report/evidence/software_skill_deploy.json']
files={n:{'sha256':sha(root/n),'bytes':(root/n).stat().st_size,'text':(root/n).read_text()} for n in names if (root/n).is_file()}
print(json.dumps({'archive_sha256':sha(base/'auar_xuefei_source.rar'),'archive_bytes':(base/'auar_xuefei_source.rar').stat().st_size,'frozen_tree_files':sum(p.is_file() for p in root.rglob('*')),'recomputed_checksums':len(checked),'bad_checksums':bad,'method':'Read-only SHA recheck of the prior same-archive frozen extraction; no new hardware execution','files':files}))
'''
proc=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','aura-ubuntu','python3 -'],input=code.encode(),capture_output=True)
if proc.returncode:print(proc.stderr.decode(errors='replace'));raise SystemExit(proc.returncode)
d=json.loads(proc.stdout)
src=R/'frozen_sources';src.mkdir(exist_ok=True)
for n,item in d.pop('files').items():
 p=src/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(item['text'].encode('utf-8'))
 assert sha(p)==item['sha256'],n
d['windows_archive_sha256']=sha(rar)
d['report_pdf_sha256']=sha(B/'v5_contribution_bjt_simsun/auar_xuefei_technical_report.pdf')
d['checked_at_beijing']=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
(R/'verification_basis.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
# Preserve the independently collected native timing table for the package under review.
impl=B/'v6_verified_revision/evidence/implementation/source_rebuild_utilization.rpt'
if impl.exists():
 text=impl.read_text(errors='replace');m=re.search(r'\| CLB\s+\|\s*(\d+)\s*\|.*?\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|',text)
 d['new_clb_placement']=m.groups() if m else None
print(json.dumps(d,ensure_ascii=False,indent=2))
