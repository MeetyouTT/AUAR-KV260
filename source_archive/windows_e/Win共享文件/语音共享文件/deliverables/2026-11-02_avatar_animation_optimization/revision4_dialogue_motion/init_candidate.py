from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    for folder in ('baseline/native','candidate/native','baseline/runtime/tools','candidate/runtime/tools','tests','validation'):
        (HERE/folder).mkdir(parents=True,exist_ok=True)
    for source in (BASE/'revision3_natural_lower_arm/candidate/native').iterdir():
        if source.is_file():
            for folder in ('baseline/native','candidate/native'):
                target=HERE/folder/source.name
                if not target.exists():shutil.copyfile(source,target)
    source=BASE/'baseline/runtime/tools/native_yuki.py'
    for folder in ('baseline/runtime/tools','candidate/runtime/tools'):
        target=HERE/folder/source.name
        if not target.exists():shutil.copyfile(source,target)
    sources={str(p.relative_to(HERE)):sha(p) for p in (HERE/'baseline').rglob('*') if p.is_file()}
    (HERE/'validation/BASELINE_SOURCES.json').write_text(json.dumps(sources,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'status':'R4_LOCAL_CANDIDATE_INITIALIZED','baseline_files':len(sources),'device_calls':0}))
if __name__=='__main__':main()
