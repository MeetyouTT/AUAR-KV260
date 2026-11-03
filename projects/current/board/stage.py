#!/usr/bin/env python3
"""Materialize checked board or historical model-host files in a new offline directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def saved(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def relative(value, absolute=False):
    p = PurePosixPath(value)
    if not p.parts or p.is_absolute() != absolute or '..' in p.parts or '\\' in value:
        raise ValueError('Invalid manifest path ' + value)
    return Path(*p.parts[int(absolute):])


def external_inputs(deploy):
    wanted = dict(deploy['external_inputs'])
    for meta in deploy['templates'].values():
        if meta['site_fields']:
            wanted.setdefault(meta['original_sha256'], {'example_basename': Path(meta['target']).name})
    return wanted


def make_index(roots, deploy):
    wanted = external_inputs(deploy)
    names = {row['example_basename'] for row in wanted.values()}
    sizes = {row['bytes'] for row in wanted.values() if 'bytes' in row}
    found = {}
    for root in roots:
        root = root.resolve(strict=True)
        if not root.is_dir() or root == Path(root.anchor):
            raise ValueError('Select a dedicated input directory')
        for parent, folders, files in os.walk(root, followlinks=False):
            folders[:] = [d for d in folders if not d.startswith('.') and d not in ('__pycache__', 'node_modules', 'venv')]
            for name in files:
                p = Path(parent) / name
                if p.is_symlink() or not p.is_file():
                    continue
                if name not in names and p.stat().st_size not in sizes:
                    continue
                key = sha(p)
                if key in wanted:
                    found.setdefault(key, str(p))
    return {'schema': 'auar.input-index.1', 'files': found, 'unmatched': sorted(set(wanted) - set(found))}


def apply_values(obj, types, supplied):
    if isinstance(obj, dict) and set(obj) == {'$site'}:
        key = obj['$site']
        if key not in supplied:
            raise ValueError('Supply the site field ' + key)
        value = supplied[key]
        if type(value).__name__ != types[key] or isinstance(value, (str, dict)) and not value:
            raise ValueError('Invalid value for site field ' + key)
        return value
    if isinstance(obj, dict):
        return {k: apply_values(v, types, supplied) for k, v in obj.items()}
    if isinstance(obj, list):
        return [apply_values(v, types, supplied) for v in obj]
    return obj


class Stage:
    def __init__(self, dest, deploy, index, site):
        self.dest, self.deploy, self.index, self.site = dest, deploy, index, site
        self.hashes = {}
        self.source_hashes = {}

    def path(self, target):
        return self.dest / relative(target, absolute=True)

    def file(self, target, source=None, expected=None, data=None, mode=0o644):
        if data is None:
            source = source.resolve(strict=True)
            actual = self.source_hashes.get(source)
            if actual is None:
                actual = self.source_hashes[source] = sha(source)
        else:
            actual = hashlib.sha256(data).hexdigest()
        if expected and actual != expected:
            raise ValueError('Input SHA-256 mismatch for ' + target)
        if target in self.hashes and self.hashes[target] != actual:
            raise ValueError('Conflicting destination ' + target)
        p = self.path(target)
        if target not in self.hashes:
            p.parent.mkdir(parents=True, exist_ok=True)
            if data is None:
                shutil.copyfile(str(source), str(p))
            else:
                p.write_bytes(data)
            if sha(p) != actual:
                raise OSError('Staged file verification failed ' + target)
            self.hashes[target] = actual
        p.chmod(mode)
        return actual

    def add(self, target, row):
        if 'template' in row:
            meta = self.deploy['templates'][row['template_key']]
            expected = meta['original_sha256']
            p = ROOT / relative(meta['template'])
            if not meta['site_fields']:
                return self.file(target, p, expected, mode=0o600)
            if expected in self.index:
                return self.file(target, Path(self.index[expected]), expected, mode=0o600)
            types = {item['name']: item['type'] for item in meta['site_fields']}
            return self.file(target, data=saved(apply_values(read(p), types, self.site)), mode=0o600)
        if 'source' in row:
            return self.file(target, ROOT / relative(row['source']), row.get('sha256'))
        key = row['external_sha256']
        if key not in self.index:
            raise ValueError('Missing required input ' + key + ' for ' + target)
        return self.file(target, Path(self.index[key]), key)


def stage_audio(stage, cfg, archive):
    roots = {'asr': cfg['asr_directory'], 'speaker': cfg['speaker']['model_directory'],
             'frontend': cfg['frontend_directory'], 'wheels_arm64': '/opt/auar/wheels'}
    rows = read(ROOT / 'src/models/inputs/board_audio_dependencies.json')
    with zipfile.ZipFile(archive) as z:
        if len(set(z.namelist())) != len(z.namelist()):
            raise ValueError('Duplicate audio archive member')
        for row in rows:
            kind, name = row['path'].split('/', 1)
            member = 'board_audio/' + row['path']
            if z.getinfo(member).file_size != row['bytes']:
                raise ValueError('Audio member size mismatch ' + member)
            stage.file(roots[kind] + '/' + relative(name).as_posix(), data=z.read(member), expected=row['sha256'])
    return len(rows)


def stage_board(st, audio):
    d = st.deploy
    base = d['business_root']
    ref = ROOT / 'board/startup/config.9a4f.reference.json'
    release = read(ROOT / 'board/release_9a4f.json')
    cfg = read(ref)
    if sha(ref) != release['baseline_startup_sha256'] or cfg['component_sha256'] != release['component_sha256']:
        raise ValueError('9a4f reference mismatch')
    components = {name: st.add(base + '/' + name, row) for name, row in release['runtime_files'].items()}
    for target, row in d['mapping'].items():
        st.add(target, row)
    settings = read(st.path(base + '/config/board_avatar_gtk.json'))
    for kind, target in settings['formal_settings_paths'].items():
        st.file(target, ROOT / 'board/settings' / ('avatar_' + kind + '_settings.json'), mode=0o600)
    for name in ('index.html', 'player.js'):
        if not st.path(settings['formal_stage_root'] + '/' + name).is_file():
            raise ValueError('Missing formal stage ' + name)
    formal = read(st.path(base + '/config/yuki_pair.formal.json'))
    for name, key in formal['runtime_pins'].items():
        if components.get(name) != key:
            raise ValueError('Formal renderer pin mismatch ' + name)
    for unit, paths in d['systemd_order'].items():
        if paths != sorted(paths) or not st.path('/etc/systemd/system/' + unit).is_file() or not all(st.path(p).is_file() for p in paths):
            raise ValueError('Missing service definition/drop-in ' + unit)
    for command in d['public_camera_prestart']:
        for p in command.get('paths', []):
            if not st.path(p).is_file():
                raise ValueError('Missing camera prestart input ' + p)
    same = components == cfg['component_sha256']
    cfg['component_sha256'] = components
    startup = str(PurePosixPath(release['runtime']).parent / 'startup')
    startup_hash = st.file(startup + '/config.json', data=ref.read_bytes() if same else saved(cfg), mode=0o600)
    st.file(startup + '/launcher.py', ROOT / 'board/startup/launcher.py')
    count = stage_audio(st, settings['board_business'], audio) if audio else 0
    return {'profile': 'board', 'components': len(components), 'exact_9a4f': same, 'startup_sha256': startup_hash,
            'camera_components': len(read(ROOT / 'board/camera_release.json')['files_sha256']),
            'dropins': {k: len(v) for k, v in d['systemd_order'].items()}, 'formal_settings': 4,
            'formal_native_pins': len(formal['runtime_pins']), 'audio_members_verified': count,
            'firmware': 'separate build/export_firmware.py output', 'live_board': 'NOT_RUN'}


def stage_host(st):
    for name, row in st.deploy['host_files'].items():
        st.add('/' + name, row)
    for name in ('host_llm.json', 'host_tts.json', 'host_tts_files.json'):
        st.file('/model_inputs/' + name, ROOT / 'src/models/inputs' / name)
    upstream = ROOT / 'src/third_party/omnivoice_source'
    for p in upstream.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            st.file('/omnivoice_source/' + p.relative_to(upstream).as_posix(), p)
    return {'profile': 'windows', 'host_manifest_entries': len(st.deploy['host_files']),
            'runtime': 'NOT_RUN', 'historical_model_service_port': 8797}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile', choices=['plan', 'index', 'board', 'windows', 'bench'])
    p.add_argument('--out', type=Path)
    p.add_argument('--input-root', type=Path, action='append', default=[])
    p.add_argument('--index', type=Path, help='private auar.input-index.1 file')
    p.add_argument('--site', type=Path, help='private JSON object of typed site values')
    p.add_argument('--audio', type=Path, help='authorized auar_board_audio_dependencies.zip')
    args = p.parse_args()
    d = read(ROOT / 'board/deploy.json')
    if args.profile == 'plan':
        print(json.dumps({'board_sources': len(d['mapping']), 'external_inputs': d['external_inputs'],
                          'site_fields': {k: m['site_fields'] for k, m in d['templates'].items() if m['site_fields']}},
                         ensure_ascii=False, indent=2))
        return
    if not args.out:
        p.error('--out is required')
    out = args.out.resolve()
    if out.exists() or out == ROOT or ROOT in out.parents:
        p.error('choose a new destination outside this package')
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.profile == 'index':
        if not args.input_root:
            p.error('supply at least one dedicated --input-root')
        prepared = make_index(args.input_root, d)
        with out.open('x', encoding='utf-8') as f:
            out.chmod(0o600)
            json.dump(prepared, f, indent=2)
        print('Saved private input index', out)
        return
    index = read(args.index) if args.index else {'schema': 'auar.input-index.1', 'files': {}}
    if index['schema'] != 'auar.input-index.1':
        raise ValueError('Unexpected input index')
    with tempfile.TemporaryDirectory(prefix='.auar-staging-', dir=str(out.parent)) as temp:
        tree = Path(temp) / 'stage'
        tree.mkdir(mode=0o700)
        st = Stage(tree, d, index['files'], read(args.site) if args.site else {})
        if args.profile == 'board':
            result = stage_board(st, args.audio)
        elif args.profile == 'windows':
            result = stage_host(st)
        else:
            for target, row in read(ROOT / 'board/bench.json').items():
                st.add('/' + target, row)
            result = {'profile': 'bench', 'operation': 'stage reference ID/STOP bench', 'board_test': 'NOT_RUN'}
        result.update(status='PASS', scope='offline file materialization', staged_files=len(st.hashes))
        (tree / 'stage_result.json').write_bytes(saved(result))
        tree.rename(out)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, zipfile.BadZipFile) as exc:
        print('ERROR', exc, file=sys.stderr)
        sys.exit(1)

