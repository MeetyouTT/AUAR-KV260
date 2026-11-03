import hashlib
import zipfile
from pathlib import Path

root = Path('/home/ghmd/kv260_readonly_audit_20260927_7sM1wd')
docs = ['REPORT.md', 'SUMMARY.md', 'INVENTORY.tsv', 'COMMANDS.md']
excluded = {'xilinx_install.txt', 'reset_query.txt'}
logs = [p.relative_to(root).as_posix() for p in (root/'logs').iterdir() if p.is_file() and p.name not in excluded]
included = sorted(docs + logs)
with (root/'SHA256SUMS.txt').open('w') as f:
    for rel in included:
        h = hashlib.sha256()
        with (root/rel).open('rb') as src:
            while chunk := src.read(4*1024*1024):
                h.update(chunk)
        f.write(f'{h.hexdigest()}  {rel}\n')
with zipfile.ZipFile(root/'kv260_readonly_audit_20260927.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for rel in included + ['SHA256SUMS.txt']:
        z.write(root/rel, arcname=rel)
print(f'included_files={len(included)+1}')
print(f'archive_bytes={(root/"kv260_readonly_audit_20260927.zip").stat().st_size}')
