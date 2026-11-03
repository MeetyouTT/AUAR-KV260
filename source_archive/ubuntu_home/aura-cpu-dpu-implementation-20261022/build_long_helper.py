import ast,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
library=Path('/home/ghmd/aura-sface-shadow-candidate-20261021/deploy-preparation/board_shadow_pilot.py')
assert hashlib.sha256(library.read_bytes()).hexdigest()=='4bbc86bff5ebd75842940da5b788a43467d54e3905cc95f666f5ae74b958bdb3'
prefix=library.read_text().split('\ndef main():',1)[0]
body=(ROOT/'board_shadow_long.py').read_text()
launcher='''
if __name__=='__main__':
    import sys
    source=Path(sys._getframe().f_code.co_filename).resolve()
    key=digest(source)[:16]
    launch=Path('/home/root/aura-dpu-vision-20261021/shadow-long-launches')/key
    launch.mkdir(parents=True,exist_ok=True)
    if os.environ.get('AURA_RUN_SFACE_SHADOW_LONG')=='1':
        try:
            main()
            result={'finished':True,'scope':'Read shadow-long deployment-result.json for actual status and restoration'}
        except Exception as exc:
            result={'finished':True,'error':type(exc).__name__+': '+str(exc)[:500]}
        (launch/'launch-result.json').write_text(json.dumps(result,indent=2)+'\\n')
    else:
        assert not (launch/'launch-result.json').exists(),'Already completed; refuse implicit repeated deployment'
        unit='aura-sface-shadow-long-'+key
        command(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=2100',
            '--setenv=AURA_RUN_SFACE_SHADOW_LONG=1','/usr/bin/python3','-B',str(source)])
        print(json.dumps({'started':True,'unit':unit,'launch_result':str(launch/'launch-result.json')}),flush=True)
'''
source=prefix+'\n'+body+'\n'+launcher
ast.parse(source)
out=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_sface_shadow_long_20261022_v3.py')
if out.exists():assert out.read_text()==source,'Refusing to change staged source; use a new revision'
else:out.write_text(source)
print(json.dumps({'source':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))
