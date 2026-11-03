from common import *
import datetime
for k in ('board/config/startup.snapshot.json','build/scripts/fpga.py','board/scripts/stage.py','build/reports/clean_directory_validation.json'):
    if not (ROOT/k).is_file():raise FileNotFoundError(k)
manifest=[]
for p in sorted(ROOT.rglob('*'),key=lambda x:x.relative_to(ROOT).as_posix()):
    if p.is_file() and p!=ROOT/'checksums.sha256':
        n=p.relative_to(ROOT).as_posix()
        if '__pycache__' in p.parts or not n.isascii() or ' ' in n:raise ValueError(n)
        if p.suffix.lower() in ('.db','.sqlite3','.sqlite','.pem','.key','.pyc') or p.name in ('id_rsa','id_ed25519','.env'):raise ValueError(n)
        manifest.append(sha(p)+'  '+n)
(ROOT/'checksums.sha256').write_bytes(('\n'.join(manifest)+'\n').encode())
print(len(manifest),'checked')
r=subprocess.run([sys.executable,'-B',str(ROOT/'build/scripts/verify.py')],cwd=ROOT,capture_output=True)
(QA/'windows_integrity.txt').write_bytes(r.stdout+r.stderr)
print(r.returncode,(r.stdout+r.stderr).decode(errors='replace')[-520:]);sys.exit(r.returncode)
