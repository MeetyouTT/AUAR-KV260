"""Create a restorable project snapshot, ZIP64, manifest and integrity report."""
import argparse
import hashlib
import json
import os
import re
import shutil
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from verify_archive import digest_file, verify

EXCLUDE_DIRS = {'.venv', 'venv', '__pycache__', '.pytest_cache', '.verysync'}
EXCLUDE_SUFFIXES = {'.pyc', '.pyo'}
STORED_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.zip', '.7z', '.gz',
                   '.mp4', '.mkv', '.pdf', '.docx', '.pptx', '.xlsx'}


def inventory(source):
    paths = []
    exclusions = []
    empty_dirs = []
    for current, dirs, files in os.walk(source, followlinks=False):
        directory = Path(current)
        for name in list(dirs):
            path = directory / name
            if name.casefold() in EXCLUDE_DIRS:
                exclusions.append({'path': path.relative_to(source).as_posix(), 'kind': 'directory', 'reason': 'machine environment, cache or sync metadata'})
                dirs.remove(name)
            elif path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
                raise ValueError('Review filesystem link before archiving: ' + str(path))
        included_files = []
        for name in files:
            path = directory / name
            if path.suffix.casefold() in EXCLUDE_SUFFIXES:
                exclusions.append({'path': path.relative_to(source).as_posix(), 'kind': 'file', 'reason': 'Python bytecode cache'})
            elif path.is_symlink():
                raise ValueError('Review filesystem link before archiving: ' + str(path))
            else:
                included_files.append(path)
        paths.extend(included_files)
        if not dirs and not included_files and directory != source:
            empty_dirs.append(directory.relative_to(source).as_posix())
    return sorted(paths, key=lambda path: path.relative_to(source).as_posix()), exclusions, sorted(empty_dirs)


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def build(source, output, name):
    started = time.perf_counter()
    source = source.resolve(strict=True)
    output = output.resolve()
    if not source.is_dir() or output.is_relative_to(source):
        raise ValueError('Archive destination must be outside the source directory')
    if not re.fullmatch(r'[\w\-]+', name) or name.casefold() in {'con', 'nul', 'prn', 'aux'}:
        raise ValueError('Invalid archive name')
    folder = output / name
    zip_path = output / (name + '.zip')
    if folder.exists() or zip_path.exists():
        raise FileExistsError('Choose a new archive name; existing baselines are preserved')
    paths, exclusions, empty_dirs = inventory(source)
    output.mkdir(parents=True, exist_ok=True)
    folder.mkdir()
    snapshot = folder / '共享文件夹'
    snapshot.mkdir()
    entries = []
    for number, path in enumerate(paths, 1):
        relative = path.relative_to(source).as_posix()
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before = path.stat()
        digest = hashlib.sha256()
        with path.open('rb') as reader, target.open('xb') as writer:
            for chunk in iter(lambda: reader.read(4 * 1024 * 1024), b''):
                writer.write(chunk)
                digest.update(chunk)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError('Source changed while copying: ' + relative)
        os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
        entries.append({'path': relative, 'size_bytes': before.st_size,
                        'mtime_ns': before.st_mtime_ns, 'sha256': digest.hexdigest()})
        if number % 500 == 0:
            print(f'SNAPSHOT {number}/{len(paths)} files', flush=True)
    for relative in empty_dirs:
        (snapshot / relative).mkdir(parents=True, exist_ok=True)
    current, _, _ = inventory(source)
    if {path.relative_to(source).as_posix() for path in current} != {entry['path'] for entry in entries}:
        raise RuntimeError('Source file set changed during snapshot')
    for entry in entries:
        current_stat = (source / entry['path']).stat()
        if (current_stat.st_size, current_stat.st_mtime_ns) != (entry['size_bytes'], entry['mtime_ns']):
            raise RuntimeError('Source changed during snapshot: ' + entry['path'])
    manifest = {
        'format_version': 1,
        'baseline': name,
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'environment': 'PC / SIMULATED; hardware port pending',
        'source_directory_at_creation': str(source),
        'source_subdirectory': '共享文件夹',
        'hash_algorithm': 'SHA-256',
        'file_count': len(entries),
        'source_bytes': sum(entry['size_bytes'] for entry in entries),
        'empty_directories': empty_dirs,
        'files': entries,
    }
    dump(folder / 'archive_manifest.json', manifest)
    dump(folder / 'archive_exclusions.json', {'rules': {'directories': sorted(EXCLUDE_DIRS), 'suffixes': sorted(EXCLUDE_SUFFIXES)}, 'excluded': exclusions})
    shutil.copy2(Path(__file__).with_name('verify_archive.py'), folder / 'verify_archive.py')
    (folder / '归档说明.md').write_text(f'''# {name}

本归档冻结当前共享项目，包含源码、正式素材／RGB565、模型、候选与原始素材、工作流、提示词和验证证据。PC 演示可用，板端移植及硬件验收待做。

本快照保存 {len(entries)} 个源文件，共 {manifest['source_bytes']:,} 字节。原项目未移动或删除。排除仅限机器环境、Python 缓存和 VerySync 状态，具体路径见 archive_exclusions.json。虚拟环境需要重建。

## 接手入口

1. 共享文件夹/deliverables/2026-10-06_avatar_reuse/流畅度复核与保留意见_2026-10-06.md
2. 同目录 板端移植交接_2026-10-06.md
3. 同目录 README.md、runtime_environment.json、requirements-demo-validated.txt

保持共享文件夹/aura 与 deliverables 的相对结构。最新临时剧本默认三档局部口型；正式板端合同仍为 1.2，尚未接入五套新口型。当前 RGB565 大端、面板底色 #FCFCF3，以归档中的 manifest 与 ui_tokens 为准。

## 校验与恢复

用任意可用 Python 3 在本目录运行：python -B verify_archive.py .

验证完成应输出 status=PASS，逐文件 SHA-256 匹配。校验工具只读，不恢复或删除文件。解压后首次校验宜在运行项目之前进行，以免新增缓存或演示输出影响“额外文件”检查。

ZIP 旁的 .sha256 是完整压缩包指纹；旁边的 _integrity_report.json 保存制作时的目录、ZIP 内逐文件及 CRC 验证结果。archive_manifest.json 校验共享项目文件；归档元数据自身由整个 ZIP 的 SHA-256 保护。

如需新一轮归档，使用新名称运行交付目录 build_board_port_archive.py --source <共享目录> --output-dir <共享目录之外的存档目录> --name <新名称>；不会覆盖既有基线。
''', encoding='utf-8')
    folder_check = verify(folder)
    if folder_check['status'] != 'PASS':
        raise RuntimeError('Snapshot verification failed: ' + json.dumps(folder_check))
    print(f'SNAPSHOT_SHA256_PASS {len(entries)} files', flush=True)
    snapshot_files = sorted(path for path in folder.rglob('*') if path.is_file())
    with zipfile.ZipFile(zip_path, mode='x', compression=zipfile.ZIP_DEFLATED, compresslevel=3, allowZip64=True) as packed:
        for number, path in enumerate(snapshot_files, 1):
            compression = zipfile.ZIP_STORED if path.suffix.casefold() in STORED_SUFFIXES else zipfile.ZIP_DEFLATED
            packed.write(path, (Path(name) / path.relative_to(folder)).as_posix(), compress_type=compression, compresslevel=3)
            if number % 500 == 0:
                print(f'ZIP {number}/{len(snapshot_files)} files', flush=True)
        for relative in empty_dirs:
            packed.writestr(name + '/共享文件夹/' + relative + '/', b'')
    expected = {name + '/共享文件夹/' + entry['path']: entry for entry in entries}
    seen = set()
    zip_files_checked = 0
    with zipfile.ZipFile(zip_path) as packed:
        all_names = packed.namelist()
        if len(all_names) != len(set(all_names)):
            raise RuntimeError('Duplicate ZIP entries')
        embedded = json.loads(packed.read(name + '/archive_manifest.json').decode('utf-8'))
        if embedded != manifest:
            raise RuntimeError('Embedded manifest mismatch')
        for info in packed.infolist():
            parts = PurePosixPath(info.filename)
            if parts.is_absolute() or '..' in parts.parts or '\\' in info.filename:
                raise RuntimeError('Unsafe ZIP entry: ' + info.filename)
            if info.is_dir():
                continue
            digest = hashlib.sha256()
            with packed.open(info) as stream:
                for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                    digest.update(chunk)  # ZipFile checks CRC when fully read.
            if info.filename in expected:
                entry = expected[info.filename]
                if info.file_size != entry['size_bytes'] or digest.hexdigest() != entry['sha256']:
                    raise RuntimeError('ZIP SHA-256 mismatch: ' + info.filename)
                seen.add(info.filename)
            else:
                original = folder / Path(*PurePosixPath(info.filename).parts[1:])
                if digest.hexdigest() != digest_file(original):
                    raise RuntimeError('ZIP metadata mismatch: ' + info.filename)
            zip_files_checked += 1
            if zip_files_checked % 500 == 0:
                print(f'ZIP_VERIFY {zip_files_checked}/{len(snapshot_files)} files', flush=True)
    if seen != set(expected):
        raise RuntimeError('ZIP missing source files')
    zip_hash = digest_file(zip_path)
    zip_path.with_suffix('.zip.sha256').write_text(zip_hash + '  ' + zip_path.name + '\n', encoding='utf-8')
    report = {
        'status': 'PASS', 'baseline': name,
        'verified_utc': datetime.now(timezone.utc).isoformat(),
        'source_unchanged_during_snapshot': True,
        'snapshot_source_sha256': folder_check,
        'zip_source_sha256_files': len(seen), 'zip_crc_and_metadata_files': zip_files_checked,
        'source_files': len(entries), 'source_bytes': manifest['source_bytes'],
        'zip_bytes': zip_path.stat().st_size, 'zip_sha256': zip_hash,
        'excluded_entries': len(exclusions),
        'elapsed_seconds': time.perf_counter() - started,
        'snapshot_directory': str(folder), 'zip_path': str(zip_path),
        'hardware_verified': False,
    }
    dump(output / (name + '_integrity_report.json'), report)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    build(args.source, args.output_dir, args.name)
