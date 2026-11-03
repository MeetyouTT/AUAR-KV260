"""Explicit offline native ARM build into a new private candidate deps folder.

No download/pip/system-package operation. Run only in an agreed board CPU
window. The archive is the exact official PyPI source; no substitute VAD/model.
"""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import stat
import subprocess
import sys
import sysconfig
import tarfile
import tempfile


SOURCE_PROFILES = {
    # Exact distribution/version verified in the existing Windows speaker venv.
    '2.0.14': dict(distribution='webrtcvad-wheels',tar_root='webrtcvad_wheels-2.0.14',
                   sha256='5f59c8e291c6ef102d9f39532982fbf26a52ce2de6328382e2654b0960fea397'),
    # Preserve the earlier probe as an explicit historical comparison only.
    '2.0.10': dict(distribution='webrtcvad',tar_root='webrtcvad-2.0.10',
                   sha256='f1bed2fb25b63fb7b1a55d64090c993c9c9167b28485ae0bcdd81cf6ede96aea'),
}
SOURCE_SHA256 = SOURCE_PROFILES['2.0.14']['sha256']


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            value.update(chunk)
    return value.hexdigest()


def checked_archive_members(members,tar_root):
    """Reject links/traversal/duplicates before extraction under a pinned root."""
    seen = set(); total = 0
    for member in members:
        name = PurePosixPath(member.name)
        normalized = name.as_posix()
        if (name.is_absolute() or '..' in name.parts or not name.parts or name.parts[0] != tar_root
                or member.issym() or member.islnk() or not (member.isdir() or member.isfile())
                or normalized != member.name.rstrip('/') or normalized in seen):
            raise ValueError('Unexpected source archive layout')
        seen.add(normalized); total += member.size
        if total > 16*1024*1024:
            raise ValueError('Source archive exceeds its bounded extraction size')
    return members


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--private-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source-version',choices=tuple(SOURCE_PROFILES),default='2.0.14',
                        help='Default is the exact Windows speaker distribution; 2.0.10 is historical only')
    args = parser.parse_args()
    profile = SOURCE_PROFILES[args.source_version]
    if os.name != 'posix' or platform.machine().lower() not in ('aarch64','arm64'):
        raise RuntimeError('Run the native build only on the actual ARM64 board')
    root = args.private_root.absolute()
    if root.resolve() != root or any(part.casefold() == 'win共享文件' for part in root.parts):
        raise ValueError('Use a separate private board candidate root')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    info = root.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077 or not stat.S_ISDIR(info.st_mode):
        raise PermissionError('Candidate root must be private and owned by this user')
    output = args.output.absolute()
    if output.resolve() != output or root not in output.parents or output == root:
        raise ValueError('Output must be a new regular subdirectory of the candidate root')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Refuse to overwrite existing dependency files')
    if args.archive.stat().st_size > 2*1024*1024 or sha(args.archive) != profile['sha256']:
        raise ValueError('Official WebRTC source fingerprint mismatch')
    compiler = shutil.which('cc') or shutil.which('gcc')
    include = Path(sysconfig.get_path('include') or '')/'Python.h'
    if compiler is None or not include.is_file() or importlib.util.find_spec('setuptools') is None:
        raise RuntimeError('Native compiler, matching Python.h and existing setuptools are required; system installation is not performed')
    build = Path(tempfile.mkdtemp(prefix='webrtcvad-build-',dir=str(root)))
    with tarfile.open(args.archive,'r:gz') as archive:
        checked_archive_members(archive.getmembers(),profile['tar_root'])
        archive.extractall(build)  # Exact SHA and every member/target verified above.
    source = build/profile['tar_root']
    output.mkdir(parents=True,exist_ok=True,mode=0o700)
    result = subprocess.run([sys.executable,'setup.py','build_ext','--build-lib',str(output),
                             '--build-temp',str(build/'objects')],cwd=str(source),
                             stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
    (build/'build.log').write_text(result.stdout,encoding='utf-8')
    if result.returncode:
        raise RuntimeError('Official native extension build failed; inspect the private build log')
    metadata = subprocess.run([sys.executable,'setup.py','egg_info','--egg-base',str(output)],
        cwd=str(source), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
    (build/'metadata.log').write_text(metadata.stdout,encoding='utf-8')
    if metadata.returncode:
        raise RuntimeError('Official distribution metadata build failed; inspect the private log')
    shutil.copyfile(source/'webrtcvad.py',output/'webrtcvad.py')
    native = list(output.glob('_webrtcvad*.so'))
    if len(native) != 1:
        raise RuntimeError('Expected exactly one native ARM extension')
    sys.path.insert(0,str(output))
    if 'webrtcvad' in sys.modules or '_webrtcvad' in sys.modules:
        raise RuntimeError('Use a fresh process; a different WebRTC module is already imported')
    distribution = importlib.metadata.distribution(profile['distribution'])
    if distribution.version != args.source_version:
        raise RuntimeError('Built distribution metadata version mismatch')
    if Path(distribution.locate_file('')).resolve() != output.resolve():
        raise RuntimeError('Loaded distribution metadata from a different dependency directory')
    import webrtcvad
    if Path(webrtcvad.__file__).resolve() != (output/'webrtcvad.py').resolve():
        raise RuntimeError('Imported a different WebRTC package')
    if webrtcvad.__version__ != args.source_version:
        raise RuntimeError('Wrapper version differs from the selected original distribution')
    vad = webrtcvad.Vad(2)
    if vad.is_speech(b'\x00\x00'*480,16000):
        raise RuntimeError('Original 30ms mode2 silence sanity failed')
    report = dict(status='BUILT_ISOLATED_SANITY_ONLY',architecture=platform.machine(),python=sys.version.split()[0],
                  source_distribution=profile['distribution'],source_version=args.source_version,
                  source_sha256=profile['sha256'],loaded_distribution_version=distribution.version,
                  loaded_wrapper_version=webrtcvad.__version__,official_egg_info_generated=True,
                  matches_original_windows_version=args.source_version == '2.0.14',
                  mode=2,frame_ms=30,sample_rate=16000,minimum_voiced_seconds=2.5,
                  files={path.name:sha(path) for path in (output/'webrtcvad.py',native[0])},
                  public_pcm_parity_verified=False,production_loaded=False,system_packages_modified=False)
    (output/'build-manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
