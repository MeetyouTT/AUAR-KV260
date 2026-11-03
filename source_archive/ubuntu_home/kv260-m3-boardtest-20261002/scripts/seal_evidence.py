#!/usr/bin/env python3
"""Seal new M3 board evidence and recheck every preserved input index."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()


def main():
    run=Path(sys.argv[1]).resolve()
    summary=json.loads((run/'board_validation_summary.json').read_text())
    assert summary['board_verified'] and summary['baseline_file_hashes_unchanged']
    original=json.loads((run/'run.json').read_text())['preserved_indexes']
    verification=ROOT/'EVIDENCE_VERIFY.json';index=ROOT/'EVIDENCE.sha256'
    metadata=run/'seal_manifest.json'
    assert not any(path.exists() for path in [index,verification,metadata])
    checks=[]
    for name,expected in sorted(original.items()):
        path=Path(name);assert sha(path)==expected,'An original index changed'
        base=path.parents[1] if 'kv260-m3-axilite' in name and path.parent.name=='evidence' else path.parent
        if path.name=='SUPPLEMENT.sha256':base=Path('/home/ghmd/kv260-m3-axilite-20261002')
        command=['sha256sum','-c','--quiet',str(path)]
        result=subprocess.run(command,cwd=str(base),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        checks.append({'index':str(path),'sha256':sha(path),'entries':len(path.read_text().splitlines()),
                       'argv':command,'cwd':str(base),'exit_code':result.returncode,
                       'stdout':result.stdout,'stderr':result.stderr})
    assert all(check['exit_code']==0 for check in checks),'Preserved file check failed'
    journal=Path(sys.argv[2]).resolve()
    assert journal.is_file()
    selected=[path for path in ROOT.rglob('*') if path.is_file() and '__pycache__' not in path.parts]
    assert all(not path.is_symlink() for path in selected)
    selected.append(journal)
    metadata.write_text(json.dumps({'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'original_index_checks':checks,'scope':'Independent M3 run, scripts, reports and additive daily journal',
        'entries_including_this_manifest':len(selected)+1,
        'note':'The checksum index and subsequent verification record do not include themselves.'},indent=2,ensure_ascii=False)+'\n')
    selected.append(metadata)
    selected=sorted(set(selected),key=lambda path:os.path.relpath(str(path),str(ROOT)))
    index.write_text(''.join(sha(path)+'  '+os.path.relpath(str(path),str(ROOT))+'\n' for path in selected))
    command=['sha256sum','-c','--quiet',index.name]
    result=subprocess.run(command,cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    own={'index':str(index),'sha256':sha(index),'entries':len(selected),'argv':command,
         'cwd':str(ROOT),'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
    record={'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'passed':result.returncode==0,'preserved_input_checks':checks,'new_index_check':own}
    verification.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n')
    assert record['passed'],'New checksum validation failed'
    print(json.dumps({'passed':True,'preserved_input_indexes':len(checks),'new_entries':len(selected),'index_sha256':sha(index)}))


if __name__=='__main__':
    main()
