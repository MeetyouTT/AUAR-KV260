"""Read-only source inventory for the user's package review. No project imports/tests."""
import collections
import csv
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
SKIP_DIRS = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache', 'node_modules', 'test_tmp'}
TEXT_EXT = {'.py', '.sv', '.v', '.vh', '.xdc', '.tcl', '.ttcl', '.c', '.cpp', '.h', '.hpp', '.sh', '.bat', '.ps1', '.json', '.jsonl', '.md', '.txt', '.csv', '.xml', '.dts', '.dtsi', '.ini', '.yaml', '.yml'}

def scan(base):
    base = Path(base)
    result = {'root': str(base), 'exists': base.exists(), 'files': {}, 'directories': [], 'errors': [], 'excluded_directories': []}
    if not base.exists():
        return result
    for current, dirs, files in os.walk(base, followlinks=False, onerror=lambda e: result['errors'].append(str(e))):
        for name in list(dirs):
            path = Path(current) / name
            if name in SKIP_DIRS or path.is_symlink():
                result['excluded_directories'].append(str(path.relative_to(base)))
                dirs.remove(name)
            else:
                result['directories'].append(path.relative_to(base).as_posix())
        for name in files:
            path = Path(current) / name
            rel = path.relative_to(base).as_posix()
            try:
                st = path.stat()
                info = {'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns}
                # Never open personal stores, recordings, weights or image data.
                if path.suffix.lower() in TEXT_EXT and st.st_size <= 2_000_000 and not path.is_symlink():
                    data = path.read_bytes()
                    after = path.stat()
                    info['sha256'] = hashlib.sha256(data).hexdigest()
                    info['stable_read'] = (st.st_size, st.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
                result['files'][rel] = info
            except OSError as e:
                result['errors'].append({'path': rel, 'error': str(e)})
    result['file_count'] = len(result['files'])
    result['bytes'] = sum(x['bytes'] for x in result['files'].values())
    result['sha256_count'] = sum('sha256' in x for x in result['files'].values())
    return result

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def remote(script):
    r = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'aura-ubuntu', 'python3 -B -'], input=script, text=True, encoding='utf-8', capture_output=True, timeout=180)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    return json.loads(r.stdout)

def main():
    start = dt.datetime.now(dt.timezone.utc).isoformat()
    roots = {
        'windows_live': r'E:\Win共享文件\语音共享文件\aura',
        'windows_delivery': r'E:\AUAR_工程交付_20261102\aura',
    }
    windows = {name: scan(root) for name, root in roots.items()}
    save('windows_inventory.json', windows)
    print(json.dumps({'windows': {k: {n: v[n] for n in ['root', 'file_count', 'bytes', 'sha256_count']} for k, v in windows.items()}}, ensure_ascii=False), flush=True)
    source = Path(__file__).read_text(encoding='utf-8')
    functions = source[source.index('SKIP_DIRS ='):source.index('def save(')]
    script = '''import collections,csv,datetime as dt,hashlib,io,json,os\nfrom pathlib import Path\n'''+functions+'''
roots={
 'ubuntu_voice':'/home/ghmd/Win共享文件/语音共享文件/aura',
 'ubuntu_sharedfolder':'/home/ghmd/Win共享文件/共享文件夹/aura',
 'ubuntu_scratch':'/home/ghmd/auar-source-v2-20261102',
 'ubuntu_pynq':'/home/ghmd/Win共享文件/协作任务/2026-11-02_pynq_skill/skill/pynq-contract-testgen',
}
result={'inventories':{name:scan(root) for name,root in roots.items()},'references':{},'parent_agents':{}}
base=Path('/home/ghmd/Win共享文件/协作任务/2026-11-02_project_structure')
for name in ['rar_source_layout.md','rar_source_manifest.csv','rar_source_requirements.csv','rar_source_budget.csv','rar_source_validation.json','runtime_config_readme.md','evidence/scheme_a_source_audit.json']:
 p=base/name
 result['references'][name]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'text':p.read_text(encoding='utf-8-sig')}
for root in roots.values():
 for p in [Path(root)/'AGENTS.md',Path(root).parent/'AGENTS.md']:
  if p.exists():result['parent_agents'][str(p)]=p.read_text()
result['scratch_texts']={}
for p in Path(roots['ubuntu_scratch']).rglob('*'):
 if p.is_file() and (p.suffix in ['.py','.tcl'] or p.name=='component.xml'):
  result['scratch_texts'][str(p)]=p.read_text()
print(json.dumps(result,ensure_ascii=False))
'''
    ubuntu = remote(script)
    save('ubuntu_inventory.json', ubuntu['inventories'])
    save('ubuntu_parent_agents.json', ubuntu['parent_agents'])
    save('scratch_texts.json', ubuntu['scratch_texts'])
    refs = OUT / 'reference'
    refs.mkdir(exist_ok=True)
    for name, obj in ubuntu['references'].items():
        dest = refs / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(obj['text'], encoding='utf-8-sig' if name.endswith('.csv') else 'utf-8')
    input_path=Path(r'D:\Download\rar_source_layout.md')
    save('audit_scope.json', {'started_utc': start,'completed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),'timezone':'America/Los_Angeles','user_document':str(input_path),'user_document_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),'ubuntu_document_sha256':ubuntu['references']['rar_source_layout.md']['sha256'],'ubuntu_source_document':ubuntu['references']['rar_source_layout.md']['path'],'excluded_directory_names':sorted(SKIP_DIRS),'read_only_project_review':True,'board_connections':0,'project_execution_or_import':False,'model_inference':False,'new_archive':False,'notes':'Only audit artifacts written. Existing project/firmware/configuration not changed. Source inventories exclude caches/venvs and directory symlinks; no completeness claim outside recorded roots.'})
    print(json.dumps({'ubuntu': {k: {n: v[n] for n in ['root','file_count','bytes','sha256_count']} for k,v in ubuntu['inventories'].items()},'reference_count':len(ubuntu['references']),'document_identical':hashlib.sha256(input_path.read_bytes()).hexdigest()==ubuntu['references']['rar_source_layout.md']['sha256'],'parent_agents':list(ubuntu['parent_agents'])},ensure_ascii=False),flush=True)

if __name__ == '__main__':
    main()
