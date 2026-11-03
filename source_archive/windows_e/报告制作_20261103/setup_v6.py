from pathlib import Path
import json,shutil,sys,hashlib,re
sys.stdout.reconfigure(encoding='utf-8')
B=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5')
S=Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-11-03_scheme_a_source_release_9a4f')
R=B/'v6_verified_revision'
assert not R.exists()
R.mkdir()
for name in ['data','evidence','figures','report','sources','tools']:
 shutil.copytree(B/'v5_contribution_bjt_simsun'/name,R/name,ignore=shutil.ignore_patterns('__pycache__'))
(R/'qa').mkdir()
for name in ['readme.md']:
 shutil.copy2(B/'v5_contribution_bjt_simsun'/name,R/name)
shutil.copy2(Path(r'D:\Download\tech_report_defects.md'),R/'sources/v5_review_defects.md')
ex=R/'evidence/source_archive';ex.mkdir()
for name in ['archive_verification.json','验证摘要.md','Tcl解包复验.json','archive.sha256']:
 shutil.copy2(S/'已交付源码包'/name,ex/name)
deps=R/'sources/reproduction';deps.mkdir()
for name in ['build/env.json','src/models/calibration/vectors/references.json','src/models/inputs/board_audio_dependencies.json','third_party_notices.md','board/readme.md','board/stage.py','board/install.sh','README.md']:
 src=S/'auar_xuefei'/name
 if src.exists():shutil.copy2(src,deps/name.replace('/','_'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ar=S/'已交付源码包/auar_xuefei_source.rar'
v=json.loads((ex/'archive_verification.json').read_text(encoding='utf-8'))
assert sha(ar)==v['sha256']
audio=json.loads((deps/'src_models_inputs_board_audio_dependencies.json').read_text(encoding='utf-8'))
live=json.loads((R/'evidence/live_board_samples.json').read_text(encoding='utf-8'))
summary={'source_archive':{'sha256':sha(ar),'bytes':ar.stat().st_size,'files':v['files'],'checked_records':v['checked_records'],'scope':'verified staged RAR; final implementation at that archive snapshot RUNNING'},'audio':{'files':len(audio),'unpacked_bytes':sum(x['bytes'] for x in audio)},'live_container_type':type(live).__name__,'live_keys':list(live)[:12] if isinstance(live,dict) else None}
(R/'qa/source_crosscheck.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
if isinstance(live,dict):
 for k,x in live.items():
  if isinstance(x,list):print(k,'count',len(x),'first',str(x[0])[:2200] if x else '')
for fn in ['v24_narrow_timing.rpt','v25_wide_timing.rpt']:
 p=R/'evidence/history'/fn;s=p.read_text(encoding='utf-8',errors='replace')
 print(fn,'header',s[:650])
 for pattern in ['no_input_delay','no_output_delay','WNS(ns)','Path Group:']:
  m=re.search(re.escape(pattern),s)
  if m:print(pattern,s[max(0,m.start()-180):m.start()+750])
print('READY',R)
