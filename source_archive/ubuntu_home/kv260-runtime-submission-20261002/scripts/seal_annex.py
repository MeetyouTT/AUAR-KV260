#!/usr/bin/env python3
"""Seal this continuation and recheck preserved input indexes. No target access."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
DAILY=Path('/home/ghmd/AMD_Smart/logs/daily/2026-10-03-RUNTIME-SUBMISSION.md')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def main():
    index=ROOT/'CONTINUATION.sha256'
    receipt=ROOT/'CONTINUATION_VERIFY.json'
    if index.exists() or receipt.exists():
        raise RuntimeError('Continuation already sealed; preserve it')
    checks=[]
    original=json.loads((ROOT/'evidence/export_state.json').read_text())
    inputs=[(Path(v['index']),v['sha256']) for v in original['preserved_indexes']]
    inputs+=[(ROOT/p/'SHA256SUMS',None) for p in ['payload','payload_v2']]
    for path,expected in inputs:
        if expected is not None and sha(path)!=expected:
            raise RuntimeError('Input index changed: '+str(path))
        process=subprocess.run(['sha256sum','-c','--quiet',str(path)],cwd=str(path.parent),
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        checks.append({'index':str(path),'sha256':sha(path),
                       'entries':len(path.read_text().splitlines()),'exit_code':process.returncode,
                       'stderr':process.stderr})
        if process.returncode:
            raise RuntimeError('Input verification failed: '+str(path))
    files=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    lines=['{}  {}\n'.format(sha(p),p.relative_to(ROOT)) for p in files]
    lines.append('{}  ../AMD_Smart/logs/daily/{}\n'.format(sha(DAILY),DAILY.name))
    index.write_text(''.join(lines))
    process=subprocess.run(['sha256sum','-c','--quiet',str(index)],cwd=str(ROOT),capture_output=True,text=True)
    if process.returncode:raise RuntimeError('Continuation index verification failed')
    result={'passed':True,'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'continuation_entries':len(lines),'index_sha256':sha(index),'input_checks':checks,
            'board_access':False,'uart_by_id_directory_exists':Path('/dev/serial/by-id').exists()}
    receipt.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:result[k] for k in ['passed','continuation_entries','index_sha256',
                                           'board_access','uart_by_id_directory_exists']}))


if __name__=='__main__':
    main()
