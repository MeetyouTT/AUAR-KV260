from pathlib import Path
import argparse,hashlib,json,sys,time
HERE=Path(__file__).resolve().parents[1];PROJECT=HERE.parents[3]
LIVE=HERE.parent/'live_follow_test_20261101'
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
def main():
 p=argparse.ArgumentParser();p.add_argument('step');p.add_argument('--timeout',type=int,default=45);a=p.parse_args()
 assert a.step.replace('_','').isalnum() and 1<=a.timeout<=120
 raw=(HERE/'remote/_new_boot_common.py').read_bytes()+b'\n'+(HERE/'remote'/(a.step+'.py')).read_bytes()
 result=json.loads(ssh('python3 -B -',raw.decode('utf-8'),timeout=a.timeout))
 report=dict(step=a.step,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),source_sha256=hashlib.sha256(raw).hexdigest(),result=result)
 path=HERE/'evidence'/(a.step+'_'+str(time.time_ns())+'.json');data=(json.dumps(report,indent=2,allow_nan=False)+'\n').encode()
 with path.open('xb') as f:f.write(data)
 print(json.dumps(dict(evidence=str(path),sha256=hashlib.sha256(data).hexdigest(),result=result)))
if __name__=='__main__':main()
