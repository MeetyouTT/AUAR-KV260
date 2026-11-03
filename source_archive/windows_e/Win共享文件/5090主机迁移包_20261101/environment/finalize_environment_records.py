"""Resolve stale distribution metadata and preserve the original speech package."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

ENV = Path(__file__).resolve().parent
PACKAGE = ENV.parent
VOICE_ROOT = Path('C:/Users/35870/.codex/visualizations/2026/10/09/01a12110-3ba4-7651-b3d7-2e6560916eb6/omnivoice-runtime-py310')
VOICE_PYTHON = VOICE_ROOT/'Scripts/python.exe'
code = r'''
import ast,importlib.metadata as m,importlib.util as u,json,pathlib,re,sys
normalize=lambda n:re.sub('[-_.]+','-',n).lower()
observed={}
for d in m.distributions():observed.setdefault(normalize(d.metadata['Name']),[]).append(d.version)
effective=[{'name':name,'version':m.version(name)} for name in sorted(observed)]
duplicates={name:versions for name,versions in observed.items() if len(versions)>1}
module_sources={}
for name in ('transformers','torch','omnivoice','numpy'):
 try:
  spec=u.find_spec(name);p=pathlib.Path(spec.origin);value={'origin':str(p)}
  tree=ast.parse(p.read_text(encoding='utf-8'))
  for n in tree.body:
   if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets):
    try:value['literal_source_version']=ast.literal_eval(n.value)
    except (ValueError,TypeError):pass
  module_sources[name]=value
 except Exception as e:module_sources[name]={'error_class':type(e).__name__}
print(json.dumps({'executable':sys.executable,'packages':effective,'observed_duplicate_dist_info':duplicates,'module_source_versions_without_import':module_sources}))
'''
summary=[]
for label in ('voice_py310','analysis_py312','dashboard_codex_python'):
    original=json.loads((ENV/(label+'_packages.json')).read_text(encoding='utf-8'))
    result=subprocess.run([original['executable'],'-I','-B','-c',code],capture_output=True,
        text=True,encoding='utf-8',timeout=40,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    assert result.returncode==0,label
    value=json.loads(result.stdout)
    (ENV/(label+'_effective_packages.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ENV/(label+'_requirements_effective.txt')).write_text(''.join(row['name']+'=='+row['version']+'\n' for row in value['packages']),encoding='utf-8')
    summary.append(dict(environment=label,raw_distribution_entries=len(original['packages']),
                        unique_effective_packages=len(value['packages']),
                        duplicated_metadata_names=len(value['observed_duplicate_dist_info'])))

metadata_root=VOICE_ROOT/'Lib/site-packages/omnivoice-0.2.1.dist-info'
target=PACKAGE/'external_dependencies/source_metadata/omnivoice-0.2.1.dist-info'
rows=[]
for name in ('METADATA','RECORD','WHEEL','entry_points.txt'):
    src=metadata_root/name
    dst=target/name
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)
    h=hashlib.sha256(src.read_bytes()).hexdigest()
    assert hashlib.sha256(dst.read_bytes()).hexdigest()==h
    rows.append(dict(source=str(src),target=str(dst),bytes=src.stat().st_size,sha256=h))
for src in (metadata_root/'licenses').rglob('*'):
    if src.is_file():
        dst=target/src.relative_to(metadata_root)
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
        h=hashlib.sha256(src.read_bytes()).hexdigest()
        assert hashlib.sha256(dst.read_bytes()).hexdigest()==h
        rows.append(dict(source=str(src),target=str(dst),bytes=src.stat().st_size,sha256=h))
(ENV/'OMNIVOICE_METADATA_MANIFEST.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
source=PACKAGE/'external_dependencies/source'
(source/'pyproject.toml').write_text('''# Migration wrapper around preserved installed source; not upstream packaging.
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "omnivoice"
version = "0.2.1"
description = "Preserved source-host OmniVoice package for migration"

[tool.setuptools.packages.find]
where = ["."]
include = ["omnivoice*"]

[tool.setuptools.package-data]
omnivoice = ["**/*"]
''',encoding='utf-8')
result=dict(schema='aura-effective-environment-locks-1',status='EFFECTIVE_LOCKS_EXPORTED',
    original_observed_catalogs_preserved=True,versions_resolved_using_original_interpreter_metadata=True,
    module_source_versions_read_without_import=True,model_imported_or_device_used=False,
    environments=summary,omnivoice_metadata_files=len(rows),venv_copied=False)
(ENV/'EFFECTIVE_ENVIRONMENT_LOCK_RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
