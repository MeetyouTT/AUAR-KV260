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

DESTINATION = '/home/root/aura-public-streaming-validation-20261031/paraformer-small-63ddc3cd0f2810b6'
EXPECTED = {
    'model.int8.onnx': (81828675, '3ef6c19369b912f7caf3cef8e545c5ccd1a33d9d7ec792a46668dc41c4b229ec'),
    'tokens.txt': (75352, '4b2d964e18b9cf139b473003b6698fb2ed9a2a5ec55b93daa677b28f578897aa'),
}


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


if __name__ == '__main__':
    receipt = json.loads((HERE / 'MODEL_HANDOFF.json').read_text(encoding='utf-8'))
    assert receipt['revision'] == '63ddc3cd0f2810b68289a7b3876e62ef5d53d6df'
    rows = receipt['files']
    assert len(rows) == 2 and {r['name'] for r in rows} == set(EXPECTED)
    for row in rows:
        source = Path(row['path'])
        assert source.resolve().is_relative_to(Path('D:/AIModels/ASR-candidates/paraformer-small-20261031').resolve())
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
