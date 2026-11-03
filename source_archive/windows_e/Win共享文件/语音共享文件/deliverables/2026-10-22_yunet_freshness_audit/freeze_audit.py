"""Freeze a local explanatory audit; no deployment or inference is performed."""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil

root=Path('/home/ghmd/aura-freshness-audit-20261022')
out=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_yunet_freshness_audit')
original=json.loads((root/'release.json').read_text())
assert original['verification']['virtual_time_checks_passed']==6
assert not original['board_connected'] and not original['source_files_modified']
assert not out.exists()
for name,row in original['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==row['sha256']
out.mkdir(parents=True)
for name in original['files']:
    shutil.copyfile(root/name,out/name)
shutil.copyfile(root/'release.json',out/'upstream-release.json')
text=(out/'README.md').read_text()
text=text.replace('../Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start/',
                  '../2026-10-21_dpu_vision_start/')
text=text.replace('../aura-thread-sched-20261022/candidate/aura/',
                  '../2026-10-22_thread_wait_diagnostics/candidate/aura/')
text+='\n共享打包说明：主任务仅改写本报告两处源码链接指向同级冻结交付；原审查SHA保留在upstream-release.json。本机复算脚本保留已验证Ubuntu路径，Windows未执行或回执。建议代码尚未实现/部署。\n'
(out/'README.md').write_text(text)
for dest in re.findall(r'\]\(([^)]+)\)',text):
    if '://' not in dest:assert (out/dest).exists(),dest
for p in out.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for p in out.glob('*.json'):json.loads(p.read_text())
release=dict(original)
release['files']={p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
                  for p in out.iterdir() if p.is_file()}
release['packaging_scope']='same local evidence; README source links retargeted to shared frozen releases'
(out/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n')
shutil.copyfile(Path(__file__),out/'freeze_audit.py')
files=sorted(p for p in out.rglob('*') if p.is_file())
(out/'FILES.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '
    +str(p.relative_to(out))+'\n' for p in files))
print(json.dumps({'delivery':str(out),'hashed_files':len(files),'board_operations':0}))
