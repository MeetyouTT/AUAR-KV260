"""Private wheel unpack + fresh-process CPU probe, never a global install.

Unpack checks the explicit official SHA, distribution/version, ARM cp39 tags and
safe ZIP paths. Run preloads the chosen NumPy/ORT before a pinned original
probe; later prepending old deps cannot replace these imported modules.
"""
import argparse
import base64
import email
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import runpy
import stat
import subprocess
import sys
import zipfile


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            result.update(chunk)
    return result.hexdigest()


def platform_guard():
    if (os.name != 'posix' or platform.machine().lower() not in ('aarch64','arm64')
            or sys.version_info[:2] != (3,9)):
        raise RuntimeError('Use the actual ARM64 CPython3.9 subprocess')
    libc = os.confstr('CS_GNU_LIBC_VERSION')
    if not libc or not libc.startswith('glibc ') or tuple(int(v) for v in libc.split()[1].split('.')) < (2,27):
        raise RuntimeError('glibc2.27 or newer is required for the ORT candidate')


def checked_entries(archive,package,version):
    allowed = {package,package+'.libs',package+'-'+version+'.dist-info'}
    seen = set(); total = 0; selected = []; skipped = []
    for entry in archive.infolist():
        name = PurePosixPath(entry.filename)
        if (name.is_absolute() or '..' in name.parts or not name.parts or name.parts[0] not in allowed
                or name.as_posix() != entry.filename.rstrip('/') or name.as_posix() in seen
                or stat.S_ISLNK(entry.external_attr>>16)):
            raise ValueError('Unsafe or unexpected wheel member')
        seen.add(name.as_posix()); total += entry.file_size
        if total > 256*1024*1024:
            raise ValueError('Wheel extraction exceeds its bounded size')
        if name.suffix == '.onnx':
            skipped.append(entry.filename)  # Runtime examples are not project models.
        elif not entry.is_dir():
            selected.append(entry)
    return selected,skipped


def unpack(args):
    platform_guard()
    if sha(args.wheel) != args.sha256:
        raise ValueError('Official wheel fingerprint mismatch')
    root,output = Path(args.private_root).absolute(),Path(args.output).absolute()
    if (root.resolve() != root or output.resolve() != output or root not in output.parents
            or output.exists() or any(p.casefold() == 'win共享文件' for p in output.parts)):
        raise ValueError('Use a new regular board-private candidate directory')
    info = root.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise PermissionError('Candidate root must be owned by this user and mode0700')
    with zipfile.ZipFile(args.wheel) as archive:
        metadata = args.package+'-'+args.version+'.dist-info/METADATA'
        wheel = args.package+'-'+args.version+'.dist-info/WHEEL'
        meta = email.message_from_bytes(archive.read(metadata))
        if meta['Name'].replace('-','_').lower() != args.package or meta['Version'] != args.version:
            raise ValueError('Wheel distribution/version mismatch')
        tags = email.message_from_bytes(archive.read(wheel)).get_all('Tag') or []
        if not any(t.startswith('cp39-cp39-manylinux') and t.endswith('_aarch64') for t in tags):
            raise ValueError('Wheel is not the intended CP39 ARM64 build')
        entries,skipped = checked_entries(archive,args.package,args.version)
        output.mkdir(mode=0o700)
        files = []
        for entry in entries:
            target = output.joinpath(*PurePosixPath(entry.filename).parts)
            target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            raw = archive.read(entry)
            fd = os.open(str(target),os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
            with os.fdopen(fd,'wb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            files.append(dict(path=entry.filename,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    report = dict(status='UNPACKED_NOT_IMPORTED',package=args.package,version=args.version,wheel_sha256=args.sha256,
                  tags=tags,requires_dist=meta.get_all('Requires-Dist') or [],files=files,
                  skipped_package_example_models=skipped,project_models_changed=False,system_packages_changed=False)
    (output/'isolation-manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(report,files_count=len(files),files=None)))


def native_maps():
    result = set()
    for line in Path('/proc/self/maps').read_text().splitlines():
        parts = line.split(None,5)
        if len(parts) == 6 and ('.so' in parts[5]) and any(name in parts[5] for name in ('onnxruntime','sherpa','numpy')):
            result.add(parts[5])
    return sorted(result)


def child(config):
    platform_guard()
    if any(name in sys.modules for name in ('onnxruntime','numpy')):
        raise RuntimeError('A chosen runtime was imported before the fresh-process preload')
    ort_root = Path(config['ort_root']).resolve(strict=True)
    selected = ([config['numpy_root']] if config.get('numpy_root') else []) + [str(ort_root)] + config['paths']
    sys.path[:0] = selected
    numpy = __import__('numpy'); ort = __import__('onnxruntime')
    binding = __import__('onnxruntime.capi.onnxruntime_pybind11_state',fromlist=['onnxruntime_pybind11_state'])
    if ort_root not in Path(ort.__file__).resolve().parents or ort_root not in Path(binding.__file__).resolve().parents:
        raise RuntimeError('Imported a different Python ORT core')
    if ort.__version__ != config['ort_version']:
        raise RuntimeError('Imported ORT version differs from the chosen case')
    if config.get('numpy_root') and (Path(config['numpy_root']).resolve() not in Path(numpy.__file__).resolve().parents
                                    or numpy.__version__ != config['numpy_version']):
        raise RuntimeError('Imported NumPy differs from the paired candidate')
    origins = dict(ort=str(Path(ort.__file__).resolve()),numpy=str(Path(numpy.__file__).resolve()),
                   pybind=str(Path(binding.__file__).resolve()),ort_version=ort.__version__,numpy_version=numpy.__version__,
                   pybind_sha256=sha(binding.__file__),available_providers=ort.get_available_providers())
    before = native_maps()
    probe = Path(config['probe']).resolve(strict=True)
    if sha(probe) != config['probe_sha256']:
        raise ValueError('Reviewed original probe source fingerprint mismatch')
    print('ORT_PRELOAD_PROOF '+json.dumps(dict(**origins,maps=before),sort_keys=True),file=sys.stderr)
    sys.argv = [str(probe)] + config['probe_args']
    exit_code = 0
    try:
        runpy.run_path(str(probe),run_name='__main__')
    except SystemExit as exc:
        exit_code = 0 if exc.code is None else exc.code if type(exc.code) is int else 1
    if (sys.modules.get('onnxruntime') is not ort or sys.modules.get('numpy') is not numpy
            or str(Path(ort.__file__).resolve()) != origins['ort']
            or str(Path(numpy.__file__).resolve()) != origins['numpy']
            or ort.__version__ != origins['ort_version'] or numpy.__version__ != origins['numpy_version']
            or sha(probe) != config['probe_sha256']):
        raise RuntimeError('Probe replaced its preloaded runtime or reviewed source')
    proof = dict(status='FRESH_PROCESS_RUNTIME_ORIGINS_VERIFIED',**origins,maps_before_probe=before,
                 maps_after_probe=native_maps(),hot_reload_performed=False,project_models_changed=False)
    print('ORT_ISOLATION_PROOF '+json.dumps(proof,sort_keys=True),file=sys.stderr)
    if exit_code:
        raise SystemExit(exit_code)


def run(args):
    platform_guard()
    paths = args.dependency_path+args.code_path
    if any(not Path(p).is_absolute() or not Path(p).is_dir() for p in paths+[args.ort_root]):
        raise ValueError('Provide explicit existing runtime/dependency/source directories')
    argv = args.probe_args[1:] if args.probe_args[:1] == ['--'] else args.probe_args
    config = dict(ort_root=args.ort_root,ort_version=args.ort_version,numpy_root=args.numpy_root,
                  numpy_version=args.numpy_version,paths=paths,probe=args.probe,
                  probe_sha256=args.probe_sha256,probe_args=argv)
    environment = dict(os.environ)
    for key in ('PYTHONHOME','PYTHONSTARTUP','LD_PRELOAD'):
        environment.pop(key,None)
    environment.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',
        PYTHONPATH=os.pathsep.join(([args.numpy_root] if args.numpy_root else [])+[args.ort_root]+paths),
        LD_LIBRARY_PATH=os.pathsep.join([str(Path(args.ort_root)/'onnxruntime/capi')]+args.native_lib_path))
    token = base64.b64encode(json.dumps(config).encode()).decode('ascii')
    result = subprocess.run([sys.executable,'-B','-S',str(Path(__file__).resolve()),'_child',token],env=environment)
    raise SystemExit(result.returncode)


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='mode',required=True)
    stage = subs.add_parser('unpack')
    stage.add_argument('--wheel',required=True); stage.add_argument('--sha256',required=True)
    stage.add_argument('--package',choices=('onnxruntime','numpy'),required=True)
    stage.add_argument('--version',required=True); stage.add_argument('--private-root',required=True)
    stage.add_argument('--output',required=True)
    invoke = subs.add_parser('run')
    invoke.add_argument('--ort-root',required=True); invoke.add_argument('--ort-version',required=True)
    invoke.add_argument('--numpy-root'); invoke.add_argument('--numpy-version')
    invoke.add_argument('--dependency-path',action='append',default=[])
    invoke.add_argument('--code-path',action='append',default=[])
    invoke.add_argument('--native-lib-path',action='append',default=[])
    invoke.add_argument('--probe',required=True); invoke.add_argument('--probe-sha256',required=True)
    invoke.add_argument('probe_args',nargs=argparse.REMAINDER)
    internal = subs.add_parser('_child'); internal.add_argument('config')
    args = parser.parse_args()
    if args.mode == 'unpack':
        unpack(args)
    elif args.mode == 'run':
        run(args)
    else:
        child(json.loads(base64.b64decode(args.config)))


if __name__ == '__main__':
    main()
