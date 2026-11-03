"""Retrieve only the verified isolated native library and its public build receipt."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[4]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh,KEY

if __name__=='__main__':
    evidence=json.loads((HERE/'ACTUAL_NATIVE_BUILD_1793456935427236300.json').read_bytes())
    assert evidence['exit_code']==0 and evidence['manual_pause_preserved'] and evidence['owners_unchanged']
    stage='/home/root/aura-animation-thinking-20261031/935cb9b30f726fbb/native_build'
    names=['libaura_yuki.so','native_build_receipt.json']
    script='import pathlib,hashlib,json\np=pathlib.Path('+repr(stage)+')\nrows={}\n'
    script+='for name in '+repr(names)+':\n q=p/name\n assert not any(x.is_symlink() for x in (q,*q.parents))\n raw=q.read_bytes()\n assert len(raw)<16*1024*1024\n rows[name]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))\nprint(json.dumps(rows))\n'
    rows=json.loads(ssh('python3 -B -',script,timeout=20))
    assert rows['libaura_yuki.so']['sha256']==evidence['result']['library_sha256']
    destination=HERE/'native_build_result';destination.mkdir(exist_ok=False)
    for name in names:
        target=destination/name
        result=subprocess.run(['scp','-O','-q','-i',str(KEY),'-o','BatchMode=yes','-o','IdentitiesOnly=yes',
            '-o','StrictHostKeyChecking=yes','root@192.168.50.2:'+stage+'/'+name,str(target)],
            capture_output=True,timeout=60)
        assert result.returncode==0,'verified_native_artifact_transfer_failed'
        raw=target.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==rows[name]['sha256'] and len(raw)==rows[name]['bytes']
    receipt=json.loads((destination/'native_build_receipt.json').read_bytes())
    assert receipt['status']=='ISOLATED_COMPILED_CPU_POLICY_PASSED_NOT_INSTALLED'
    assert receipt['library_sha256']==rows['libaura_yuki.so']['sha256']
    report=dict(status='VERIFIED_PUBLIC_NATIVE_ARTIFACTS_RETRIEVED',board_directory=stage,files=rows,production_installed=False)
    (destination/'FETCH_RECEIPT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=report['status'],directory=str(destination),files=rows)))
