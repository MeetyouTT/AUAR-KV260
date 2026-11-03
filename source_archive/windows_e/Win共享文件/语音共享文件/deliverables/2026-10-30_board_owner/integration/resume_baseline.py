"""Read current board metadata and pinned Python sources, never business data."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.partial')
    with temporary.open('w', encoding='utf-8') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)


def main():
    tree = ast.parse((PROJECT / 'deliverables/2026-10-28_timeline_summaries/capture_board.py').read_text(encoding='utf-8'))
    script = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == 'script' for target in node.targets))
    current = json.loads(ssh('python3 -B -', script, timeout=30))
    current['checked_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write_json(HERE / 'resume_board_baseline.json', current)
    assert current['preflight_ready'], 'Board not idle/protected or source pins invalid'
    script = r'''
import hashlib,json
from pathlib import Path
root=Path(ROOT_STRING)
config=Path(CONFIG_STRING)
cfg=json.loads(config.read_text())
assert cfg['runtime']==str(root)
sources={}
for name,digest in cfg['component_sha256'].items():
    relative=Path(name)
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe component path')
    if relative.suffix!='.py':continue
    source=root/'aura'/relative
    # Released runtime components may be symlinks to earlier immutable releases.
    # The exact component name, Python suffix and release SHA authorize the read.
    assert source.resolve().suffix=='.py'
    assert source.stat().st_size<=2*1024*1024
    data=source.read_bytes()
    assert hashlib.sha256(data).hexdigest()==digest,name
    sources[name]={'sha256':digest,'text':data.decode('utf-8')}
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  'runtime':str(root),'config_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),
                  'sources':sources}))
'''.replace('ROOT_STRING', repr(current['actual_runtime'])).replace('CONFIG_STRING', repr(current['actual_config']))
    result = json.loads(ssh('python3 -B -', script, timeout=35))
    assert result['boot'] == current['boot']
    assert result['config_sha256'] == current['config_sha256']
    destination = HERE / 'resume_runtime/fresh_source/aura'
    manifest = {}
    for name, row in result['sources'].items():
        data = row['text'].encode('utf-8')
        assert hashlib.sha256(data).hexdigest() == row['sha256']
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        manifest[name] = row['sha256']
    write_json(destination.parent / 'manifest.json', dict(boot=result['boot'], runtime=result['runtime'],
               config_sha256=result['config_sha256'], source_sha256=manifest,
               scope='Pinned Python source only; no runtime settings, databases, images, keys or model files'))
    print(json.dumps(dict(status='PASS', boot=current['boot'], runtime=current['actual_runtime'],
                         preflight_ready=current['preflight_ready'], sources=len(manifest),
                         source_directory=str(destination)), ensure_ascii=True))


if __name__ == '__main__':
    main()
