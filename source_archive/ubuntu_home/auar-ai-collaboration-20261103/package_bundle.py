from pathlib import Path
import datetime as dt
import hashlib
import json
import subprocess
import tempfile
import zipfile
from collect_evidence import OUT, WORK

sha=lambda b:hashlib.sha256(b).hexdigest()


def main():
    validation=json.loads((OUT/'checks/validation.json').read_text())
    if validation['status']!='PASS':raise SystemExit('Refusing package: document validation failed')
    excluded={'ai_collaboration_bundle.zip','sha256sums.txt','bundle_verification.json'}
    files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name not in excluded)
    manifest=''.join(sha(p.read_bytes())+'  '+str(p.relative_to(OUT))+'\n' for p in files)
    (OUT/'sha256sums.txt').write_text(manifest)
    local=subprocess.run(['python3','-B','checks/verify_package.py'],cwd=str(OUT),capture_output=True,text=True,check=True)
    files.append(OUT/'sha256sums.txt')
    archive=OUT/'ai_collaboration_bundle.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:z.write(p,'ai_collaboration/'+str(p.relative_to(OUT)))
    expanded=Path(tempfile.mkdtemp(prefix='bundle_reproduction_',dir=str(WORK)))
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise RuntimeError('Archive CRC failed')
        expected={'ai_collaboration/'+str(p.relative_to(OUT)):p for p in files}
        if set(z.namelist())!=set(expected):raise RuntimeError('Archive path mismatch')
        for name,path in expected.items():
            if sha(z.read(name))!=sha(path.read_bytes()):raise RuntimeError('Archive SHA mismatch: '+name)
        z.extractall(expanded)
    reproduction=subprocess.run(['python3','-B','checks/verify_package.py'],cwd=str(expanded/'ai_collaboration'),capture_output=True,text=True,check=True)
    result={'status':'PASS','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'archive':archive.name,'sha256':sha(archive.read_bytes()),'bytes':archive.stat().st_size,'files':len(files),'sole_root':'ai_collaboration','crc_passed':True,'all_member_sha_matched':True,'document_validation_checks':validation['checks_total'],'local_self_check':local.stdout.strip(),'fresh_directory_self_check':reproduction.stdout.strip(),'fresh_directory':str(expanded/'ai_collaboration'),'notes':'Verification does not load models, access boards, or use the original private history database.'}
    (OUT/'bundle_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
