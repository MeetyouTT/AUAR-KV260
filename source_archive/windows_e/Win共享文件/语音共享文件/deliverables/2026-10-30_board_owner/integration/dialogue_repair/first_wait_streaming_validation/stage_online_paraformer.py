"""Copy verified ASR resources into a new board public test directory only."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh, KEY

DESTINATION = '/home/root/aura-public-streaming-validation-20261031/online-paraformer-8e40c43232a1c5c6'

if __name__ == '__main__':
    receipt = json.loads((HERE/'online_paraformer_download_manifest.json').read_text(encoding='utf-8'))
    rows = receipt['files']
    for row in rows:
        source = Path(row['path'])
        assert source.resolve().is_relative_to(Path('D:/AIModels/ASR-candidates').resolve())
        assert source.stat().st_size == row['size'] and hashlib.sha256(source.read_bytes()).hexdigest() == row['sha256']
    script = "import pathlib,json\np=pathlib.Path("+repr(DESTINATION)+")\n"
    script += "assert not p.is_symlink() and not p.parent.is_symlink()\np.mkdir(mode=0o700,parents=True,exist_ok=True)\nprint(json.dumps(dict(ready=True)))\n"
    assert json.loads(ssh('python3 -B -', script, timeout=15))['ready']
    for row in rows:
        target = DESTINATION+'/'+Path(row['path']).name
        check = 'import pathlib,hashlib,json\np=pathlib.Path('+repr(target)+')\nassert not p.is_symlink()\nprint(json.dumps(dict(exists=p.exists(),sha256=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None)))\n'
        observed = json.loads(ssh('python3 -B -', check, timeout=20))
        if observed['exists']:
            assert observed['sha256'] == row['sha256']
        else:
            result = subprocess.run(['scp','-O','-q','-i',str(KEY),'-o','BatchMode=yes','-o','IdentitiesOnly=yes',
                '-o','StrictHostKeyChecking=yes',row['path'],'root@192.168.50.2:'+target],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
            assert result.returncode == 0, 'isolated_model_transfer_failed'
        observed = json.loads(ssh('python3 -B -', check, timeout=20))
        assert observed['sha256'] == row['sha256']
        print(json.dumps(dict(staged=Path(target).name,verified=True)), flush=True)
    value = dict(status='ISOLATED_PUBLIC_MODELS_STAGED_NOT_DEPLOYED',board_directory=DESTINATION,
                 files=[dict(name=Path(r['path']).name,size=r['size'],sha256=r['sha256']) for r in rows])
    (HERE/'online_paraformer_staged_manifest.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
