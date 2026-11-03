#!/usr/bin/env python3
"""Export unchanged runtime core files; preserve the full upstream archive outside the payload."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT=Path(__file__).resolve().parents[1]
PAYLOAD=ROOT/'payload'
XRT=Path('/home/ghmd/kv260-overlay-repair-20261002/sources/XRT_patched')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if (PAYLOAD/'SHA256SUMS').exists():
        raise RuntimeError('Payload is sealed')
    archive=PAYLOAD/'sources/xrt_baseline.tar.gz'
    manifest=PAYLOAD/'sources/xrt_tree.json'
    original=ROOT/'evidence/full_xrt_fixed_snapshot.tar.gz'
    original_manifest=ROOT/'evidence/full_xrt_fixed_tree.json'
    if original.exists() or original_manifest.exists():
        raise RuntimeError('Source export already prepared; preserve evidence')
    versions=json.loads((PAYLOAD/'config/source_lock.json').read_text())
    if sha(archive)!=versions['xrt_archive_sha256']:
        raise RuntimeError('Original snapshot hash mismatch')
    archive.rename(original)
    manifest.rename(original_manifest)
    tree=json.loads(original_manifest.read_text())
    selected={name:data for name,data in tree.items()
              if name=='LICENSE' or name.startswith('src/runtime_src/core/')}
    with tarfile.open(original,'r:gz') as source, archive.open('xb') as target:
        with gzip.GzipFile(filename='',fileobj=target,mode='wb',mtime=0) as compressed:
            with tarfile.open(fileobj=compressed,mode='w') as exported:
                for member in source.getmembers():
                    if member.name=='LICENSE' or member.name.startswith('src/runtime_src/core/'):
                        exported.addfile(member,source.extractfile(member) if member.isfile() else None)
    manifest.write_text(json.dumps(selected,indent=2)+'\n')
    required=set()
    generated=set()
    pattern=re.compile(re.escape(str(XRT))+r'/[^\s\\]+')
    commands=list((XRT/'src/runtime_src/core').rglob('.*.cmd'))
    for command in commands:
        for token in pattern.findall(command.read_text(errors='replace')):
            relative=str(Path(token).resolve().relative_to(XRT))
            if relative.endswith(('.c','.h','.S','.s')) or Path(relative).name=='Makefile':
                if relative.endswith('.mod.c'):
                    generated.add(relative)
                else:
                    required.add(relative)
    if not commands or not required:
        raise RuntimeError('No previous build dependencies found')
    missing=sorted(required-set(selected))
    if missing:
        raise RuntimeError('Missing previous build dependency: '+repr(missing))
    versions.update(full_xrt_snapshot_sha256=sha(original),xrt_archive_sha256=sha(archive),
                    xrt_snapshot_scope='Original root LICENSE and runtime_src/core subtree; unchanged files at fixed commit',
                    xrt_snapshot_files=len(selected),
                    full_xrt_snapshot_files=len(tree))
    (PAYLOAD/'config/source_lock.json').write_text(json.dumps(versions,indent=2,ensure_ascii=False)+'\n')
    receipt={'passed':True,'fixed_commit':versions['xrt_commit'],
             'full_snapshot_preserved':str(original),'full_snapshot_sha256':sha(original),
             'full_snapshot_files':len(tree),'exported_snapshot_files':len(selected),
             'exported_snapshot_sha256':sha(archive),
             'source_file_content_changed':False,'previous_dependency_command_files':len(commands),
             'previous_xrt_source_dependencies':len(required),'missing_dependencies':missing,
             'generated_module_sources_not_upstream_inputs':sorted(generated),
             'excluded_files':sorted(set(tree)-set(selected)),
             'scope':'Runtime core export, not full XRT project; board and original repositories unchanged'}
    (ROOT/'evidence/runtime_source_export.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (PAYLOAD/'evidence/runtime_source_export.json').write_text(json.dumps(
        {k:v for k,v in receipt.items() if k!='excluded_files'},indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ['passed','full_snapshot_files','exported_snapshot_files',
                                            'previous_xrt_source_dependencies','missing_dependencies']}))


if __name__=='__main__':
    main()
