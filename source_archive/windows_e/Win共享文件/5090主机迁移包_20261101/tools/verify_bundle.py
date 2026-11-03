"""Verify the exported payload before changing new-host paths. No network or device access."""
import argparse
import hashlib
import json
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--full-workspace',action='store_true',help='Also check all in-place workspace records (large files: size only).')
a=p.parse_args()
package=Path(__file__).resolve().parents[1]
workspace=package.parent
manifest=json.loads((package/'PACKAGE_MANIFEST.json').read_text('utf-8'))
failures=[]
checked=0


def file_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def check(root,row):
    global checked
    path=root/row['path']
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        failures.append(dict(path=row['path'],reason='OUTSIDE_ROOT_OR_SYMLINK'))
        return
    if not path.is_file():
        failures.append(dict(path=row['path'],reason='MISSING'))
        return
    if path.stat().st_size!=row['bytes']:
        failures.append(dict(path=row['path'],reason='SIZE_CHANGED'))
    elif row.get('sha256') and file_sha(path)!=row['sha256']:
        failures.append(dict(path=row['path'],reason='HASH_CHANGED'))
    checked+=1

for row in manifest['files']:
    check(package,row)
for row in manifest['workspace_critical_files']:
    check(workspace,row)
if a.full_workspace:
    with (package/'verification/WORKSPACE_FILES.jsonl').open('r',encoding='utf-8') as f:
        for line in f:
            check(workspace,json.loads(line))
report=dict(schema='aura-migration-verification-1',
    status='PASS' if not failures else 'CHANGED_OR_MISSING_FILES',
    checked_files=checked,failures=failures,full_workspace=a.full_workspace,
    package_root=str(package),workspace_root=str(workspace),
    network_device_or_model_access=False,
    new_host_configuration_or_gpu_compatibility_claimed=False)
(package/'verification/VERIFY_RESULT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'],checked_files=checked,failures=len(failures)),ensure_ascii=False))
raise SystemExit(0 if not failures else 1)
