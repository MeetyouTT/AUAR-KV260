"""Reuse the app's installed small timezone dataset in the isolated speaker venv."""
import hashlib,importlib.metadata,json,shutil,subprocess,sysconfig
from pathlib import Path
import tzdata
H=Path(__file__).resolve().parent
python=Path(r'D:\AIModels\speaker-identity\venv\Scripts\python.exe')
target=Path(subprocess.check_output([str(python),'-c','import sysconfig;print(sysconfig.get_path("purelib"))'],text=True).strip())
expected=Path(r'D:\AIModels\speaker-identity\venv\Lib\site-packages')
assert target.resolve()==expected.resolve()
package=Path(tzdata.__file__).parent;metadata=Path(importlib.metadata.distribution('tzdata')._path)
receipt={'source':'existing Codex bundled runtime package','package':'tzdata','version':tzdata.__version__,
         'target_environment':str(python),'network_download':False,'files':{},'bytes':0}
for source in (package,metadata):
    destination=target/source.name
    assert not destination.exists(),'Do not overwrite an existing timezone package'
    for file in source.rglob('*'):
        assert not file.is_symlink()
        if file.is_file() and '__pycache__' not in file.parts:
            relative=file.relative_to(source);output=destination/relative
            output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,output)
            digest=hashlib.sha256(file.read_bytes()).hexdigest()
            assert hashlib.sha256(output.read_bytes()).hexdigest()==digest
            receipt['files'][source.name+'/'+relative.as_posix()]=digest;receipt['bytes']+=file.stat().st_size
result=subprocess.check_output([str(python),'-B','-c',
    "import tzdata;from zoneinfo import ZoneInfo;from datetime import datetime;print(tzdata.__version__,datetime(2026,11,1,1,tzinfo=ZoneInfo('America/Los_Angeles')).utcoffset())"],text=True).strip()
receipt['validation']=result
(H/'timezone_dependency.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in receipt.items() if k!='files'}))
