"""Root-only transfer of the two verified public ASR files to an isolated board directory."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh, KEY

DESTINATION = '/home/root/aura-public-streaming-validation-20261031/sensevoice-2365baeacb507f82'
EXPECTED = {
    'model.int8.onnx': (239233841, 'c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51'),
    'tokens.txt': (315894, 'f449eb28dc567533d7fa59be34e2abca8784f771850c78a47fb731a31429a1dc'),
}


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


if __name__ == '__main__':
    receipt = json.loads((HERE / 'MODEL_HANDOFF.json').read_text(encoding='utf-8'))
    assert receipt['revision'] == '2365baeacb507f821a0c8120fcee3d484dba7a07'
    rows = receipt['files']
    assert len(rows) == 2 and {r['name'] for r in rows} == set(EXPECTED)
    for row in rows:
        source = Path(row['path'])
        assert source.resolve().is_relative_to(Path('D:/AIModels/ASR-candidates/sensevoice-20261031').resolve())
        assert not source.is_symlink() and source.name == row['name']
        assert (row['size'], row['sha256']) == EXPECTED[row['name']]
        assert source.stat().st_size == row['size'] and digest(source) == row['sha256']
    script = 'import pathlib,json,shutil\np=pathlib.Path(' + repr(DESTINATION) + ')\n'
    script += "assert not any(x.is_symlink() for x in (p,*p.parents))\np.mkdir(mode=0o700,parents=True,exist_ok=True)\nassert shutil.disk_usage(p).free>800*1024*1024\nprint(json.dumps(dict(ready=True)))\n"
    assert json.loads(ssh('python3 -B -', script, timeout=15))['ready']
    for row in rows:
        target = DESTINATION + '/' + row['name']
        check = 'import pathlib,hashlib,json\np=pathlib.Path(' + repr(target) + ')\n'
        check += "assert not any(x.is_symlink() for x in (p,*p.parents))\nprint(json.dumps(dict(exists=p.exists(),size=p.stat().st_size if p.exists() else None,sha256=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None)))\n"
        observed = json.loads(ssh('python3 -B -', check, timeout=20))
        if observed['exists']:
            assert observed['sha256'] == row['sha256'] and observed['size'] == row['size']
        else:
            result = subprocess.run(['scp', '-O', '-q', '-i', str(KEY), '-o', 'BatchMode=yes',
                '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=yes', row['path'],
                'root@192.168.50.2:' + target], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            assert result.returncode == 0, 'isolated_model_transfer_failed'
        observed = json.loads(ssh('python3 -B -', check, timeout=20))
        assert observed['sha256'] == row['sha256'] and observed['size'] == row['size']
        print(json.dumps(dict(staged=row['name'], verified=True)), flush=True)
    value = dict(status='ISOLATED_PUBLIC_MODELS_STAGED_NOT_DEPLOYED', board_directory=DESTINATION,
        files=[dict(name=r['name'], size=r['size'], sha256=r['sha256']) for r in rows], production_changed=False)
    (HERE / 'STAGED_MODELS.json').write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
