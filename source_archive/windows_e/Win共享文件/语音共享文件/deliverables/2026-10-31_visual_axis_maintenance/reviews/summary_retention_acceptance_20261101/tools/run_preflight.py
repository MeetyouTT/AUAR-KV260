"""One fresh read-only inventory for the resumed retention acceptance task."""
from pathlib import Path
import hashlib,json,sys,time
HERE=Path(__file__).resolve().parents[1];PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

def main():
 spec_path=PROJECT/'deliverables/2026-10-30_board_owner/integration/production_business_acceptance/spec.json'
 spec_raw=spec_path.read_bytes();spec=json.loads(spec_raw)
 assert hashlib.sha256(spec_raw).hexdigest()=='62b99e24560229c78a3be000fed5752b6a50c4fb16ab6bc2c88e987561831177'
 common=HERE.parent/'live_follow_test_20261101/remote/_session_common.py'
 source=common.read_text('utf-8')+'\nSPEC='+repr(spec)+'\n'+(HERE/'remote/preflight.py').read_text('utf-8')
 result=json.loads(ssh('python3 -B -',source,timeout=55))
 envelope=dict(schema='aura-resumed-acceptance-preflight-envelope-1',utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
               spec_sha256=hashlib.sha256(spec_raw).hexdigest(),source_sha256=hashlib.sha256(source.encode()).hexdigest(),result=result)
 output=HERE/'evidence'/('preflight_'+str(time.time_ns())+'.json');output.parent.mkdir(parents=True,exist_ok=True)
 data=(json.dumps(envelope,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
 with output.open('xb') as f:f.write(data)
 latest=HERE/'LATEST.json';latest.write_text(json.dumps(dict(status=result['status'],preflight=str(output),sha256=hashlib.sha256(data).hexdigest(),no_live_window_started=True),indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(evidence=str(output),sha256=hashlib.sha256(data).hexdigest(),result=result),ensure_ascii=False))

if __name__=='__main__':main()
