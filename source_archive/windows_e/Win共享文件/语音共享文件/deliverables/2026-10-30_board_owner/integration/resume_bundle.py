"""Build a source-only candidate; optional explicit staging never changes a service.

The base is the freshly verified release source, not an old shared-tree GUI.
Overrides name only this task's reviewed candidate modules. No configurations,
database, model resource, credential, image or audio file enters this bundle.
"""
import argparse
import ast
import base64
import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
from resume_baseline import write_json

OVERRIDES = (
    'common/board_memory.py', 'common/board_memory_migration.py', 'common/board_timeline_clock.py',
    'common/model_inference_wire.py',
    'board/runtime/board_dialogue.py', 'board/runtime/board_dialogue_client.py',
    'board/runtime/board_memory_policy.py', 'board/runtime/board_business.py',
    'board/runtime/audio/board_asr.py', 'board/runtime/audio/board_asr_frontend.py',
    'board/runtime/audio/board_gtcrn_fft.py', 'board/runtime/audio/board_speaker_onnx.py',
    'board/runtime/audio/board_dialogue_jobs.py', 'board/runtime/audio/board_capture.py',
    'board/runtime/audio/board_pcm_queue.py',
    'board/runtime/visual_memory.py', 'board/runtime/board_speaker_business.py',
    'tools/board_business_gui.py', 'tools/board_profile_dialog.py',
    'tools/speaker_device.py',
    'tools/binding_hub_runtime.py',
    'board/visual_timeline.py',
)


def build(*, probe_only=False):
    base = HERE / 'resume_runtime/fresh_source'
    metadata = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
    entries = {}
    for name, expected in metadata['source_sha256'].items():
        data = (base / 'aura' / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected, 'Fresh source changed: ' + name
        entries[name] = data
    for name in OVERRIDES:
        if probe_only and not (PROJECT / 'aura' / name).exists():
            continue
        data = (PROJECT / 'aura' / name).read_bytes()
        compile(data, name, 'exec')
        entries[name] = data
    # These two files were minimally patched from the fresh release snapshot;
    # never substitute the older main-tree GTK implementation.
    gui_root = HERE / 'resume_runtime/gui_candidate/aura'
    for name in ('tools/board_avatar_gtk.py', 'tools/profile_selection_ui.py'):
        data = (gui_root / name).read_bytes()
        compile(data, name, 'exec')
        entries[name] = data
    # Host-only helpers used by newly moved board code were not all pins in
    # the former GTK release. Resolve their project-local Python imports too.
    added_dependencies = []
    scanned = set()
    project_packages = {'common', 'board', 'host', 'tools', 'tests'}
    while set(entries) - scanned:
        name = next(iter(set(entries) - scanned))
        scanned.add(name)
        package = name[:-3].split('/')[:-1]
        tree = ast.parse(entries[name], filename=name)
        wanted = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                wanted.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base_parts = package[:len(package)-node.level+1]
                    base_parts += node.module.split('.') if node.module else []
                    base_name = '.'.join(base_parts)
                else:
                    base_name = node.module or ''
                wanted.append(base_name)
                wanted.extend(base_name+'.'+alias.name for alias in node.names if alias.name != '*')
        for module in wanted:
            if module.split('.')[0] not in project_packages:
                continue
            relative = module.replace('.', '/')+'.py'
            if relative in entries:
                continue
            source = PROJECT/'aura'/relative
            if not source.is_file():
                continue
            data = source.read_bytes()
            compile(data, relative, 'exec')
            entries[relative] = data
            added_dependencies.append(relative)
    # Each package is explicit; never allow an installed stale package to win.
    for name in tuple(entries):
        parent = Path(name).parent
        while parent != Path('.'):
            entries.setdefault((parent / '__init__.py').as_posix(), b'')
            parent = parent.parent
    pins = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(entries.items())}
    fingerprint = hashlib.sha256(json.dumps(dict(files=pins, probe_only=probe_only),
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    manifest = dict(schema_version=1, purpose='source_only_board_business_candidate',
        source_fingerprint=fingerprint, source_boot=metadata['boot'], source_runtime=metadata['runtime'],
        source_config_sha256=metadata['config_sha256'], source_sha256=pins,
        overrides=list(OVERRIDES), business_data_included=False, model_data_included=False,
        additional_python_dependencies=sorted(added_dependencies),
        probe_only=probe_only, production_entry_switch_permitted=False,
        candidate_root='/home/root/aura-board-owner-candidate-20261030/resume-' + fingerprint[:16])
    output = HERE / 'resume_bundle'
    output.mkdir(exist_ok=True)
    archive = output / (fingerprint + '.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, data in sorted(entries.items()):
            item = zipfile.ZipInfo('code/' + name, date_time=(2026, 10, 30, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o600 << 16
            bundle.writestr(item, data)
        bundle.writestr('manifest.json', json.dumps(manifest, sort_keys=True, ensure_ascii=True).encode())
    manifest['archive_sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest['archive_path'] = str(archive)
    manifest['built_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write_json(output / 'latest.json', manifest)
    return archive, manifest


def stage(archive, manifest):
    window = json.loads((HERE.parent / 'coordination/runtime_windows.json').read_text(encoding='utf-8-sig'))
    if window['performance_window'].get('state') != 'BUSINESS_ACCEPTANCE_EXCLUSIVE':
        raise RuntimeError('The current character resource window has not been returned')
    if window['performance_window'].get('board_boot') != manifest['source_boot']:
        raise RuntimeError('A fresh baseline is required for this board boot')
    script = r'''
import base64,hashlib,io,json,os,zipfile
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
data=base64.b64decode(PAYLOAD,validate=True)
assert hashlib.sha256(data).hexdigest()==DIGEST
assert len(data)<8*1024*1024
parent=Path('/home/root/aura-board-owner-candidate-20261030')
assert parent.is_dir() and not parent.is_symlink()
target=parent/TARGET
assert target.parent==parent and not target.is_symlink()
target.mkdir(mode=0o700,exist_ok=True)
with zipfile.ZipFile(io.BytesIO(data)) as archive:
    entries=archive.infolist()
    assert len(entries)<1000 and sum(e.file_size for e in entries)<20*1024*1024
    manifest=json.loads(archive.read('manifest.json'))
    assert manifest['candidate_root']==str(target)
    assert manifest['purpose']=='source_only_board_business_candidate'
    expected={'code/'+name:digest for name,digest in manifest['source_sha256'].items()}
    expected['manifest.json']=hashlib.sha256(archive.read('manifest.json')).hexdigest()
    assert set(archive.namelist())==set(expected) and len(entries)==len(expected)
    for entry in entries:
        relative=Path(entry.filename)
        assert not relative.is_absolute() and '..' not in relative.parts
        assert entry.filename=='manifest.json' or relative.suffix=='.py'
        destination=target/relative
        assert not destination.is_symlink() and target.resolve() in destination.resolve().parents
        content=archive.read(entry)
        assert hashlib.sha256(content).hexdigest()==expected[entry.filename]
        destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        if destination.exists():
            assert destination.read_bytes()==content
        else:
            with destination.open('xb') as output:output.write(content);output.flush();os.fsync(output.fileno())
            destination.chmod(0o600)
print(json.dumps({'status':'STAGED_SOURCE_ONLY','candidate_root':str(target),'python_files':len(expected)-1,
                  'source_fingerprint':manifest['source_fingerprint'],'production_entry_changed':False,
                  'business_data_transferred':False,'model_resources_transferred':False}))
'''
    script = ('BOOT=' + repr(manifest['source_boot']) + '\nPAYLOAD=' + repr(base64.b64encode(archive.read_bytes()).decode()) +
              '\nDIGEST=' + repr(manifest['archive_sha256']) + '\nTARGET=' + repr(Path(manifest['candidate_root']).name) + '\n' + script)
    result = json.loads(ssh('python3 -B -', script, timeout=40))
    write_json(HERE / 'resume_bundle/staged.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', action='store_true', help='Explicit source-only board write; requires a free resource window')
    parser.add_argument('--probe-only', action='store_true', help='Permit absent unfinished optional modules; never a production release')
    args = parser.parse_args()
    archive, manifest = build(probe_only=args.probe_only)
    result = stage(archive, manifest) if args.stage else dict(status='BUILT_ONLY',
        source_fingerprint=manifest['source_fingerprint'], candidate_root=manifest['candidate_root'],
        python_files=len(manifest['source_sha256']), archive_bytes=archive.stat().st_size)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
