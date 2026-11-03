"""Merge reviewed candidates in a new directory; frozen inputs stay unchanged."""
import ast,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PRODUCER=Path('/home/ghmd/aura-sface-producer-20261022')
TIMING=Path('/home/ghmd/aura-optional-timing-v2-20261022')
CAL=Path('/home/ghmd/aura-sface-calibration-20261022')
OUTPUT=ROOT/'candidate/aura'
OLD='image=np.frombuffer(data,dtype=np.uint8).reshape(h,w,3).copy()'
NEW='image=np.frombuffer(data,dtype=np.uint8).reshape(h,w,3)'


def main():
    before={}
    for root in (TIMING,CAL):
        for line in (root/'FILES.sha256').read_text().splitlines():
            digest,name=line.split('  ',1)
            assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,(root,name)
    files={}
    for source in (PRODUCER/'candidate/aura').rglob('*.py'):
        name=str(source.relative_to(PRODUCER/'candidate/aura'))
        files[name]=source.read_text();before['producer:'+name]=hashlib.sha256(source.read_bytes()).hexdigest()
    for source in (TIMING/'candidate/aura').rglob('*.py'):
        name=str(source.relative_to(TIMING/'candidate/aura'));body=source.read_text()
        before['timing:'+name]=hashlib.sha256(source.read_bytes()).hexdigest()
        if name=='board/vision/ui_camera_service.py':
            assert body.count('    return Handler\n')==1
            body=body.replace('    return Handler\n','    from board.identity.calibration_http import wrap_handler\n    return wrap_handler(Handler,state)\n',1)
            assert body.count(OLD)==1
            body=body.replace(OLD,NEW,1)
        files[name]=body
    assert len(files)==13
    for name,body in files.items():
        ast.parse(body,filename=name)
        path=OUTPUT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
    value={'status':'MERGED_SOFTWARE_CANDIDATE_NOT_BOARD_DEPLOYED',
        'includes':['SFace producer and calibration observer','normal wall and thread CPU diagnostics','single redundant capture copy removal'],
        'default_auxiliary_features_enabled':False,'formal_sface_identity_migrated':False,
        'upstream_source_hashes':before,
        'merge_rule':'Producer/calibration identity modules; timing runtime/schedule/metrics; measured UI + two-line calibration wrapper + single copy removal',
        'files':{name:{'sha256':hashlib.sha256(body.encode()).hexdigest(),'bytes':len(body.encode())} for name,body in sorted(files.items())}}
    (ROOT/'manifest.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'source_files':len(files),'status':value['status']}))


if __name__=='__main__':main()
