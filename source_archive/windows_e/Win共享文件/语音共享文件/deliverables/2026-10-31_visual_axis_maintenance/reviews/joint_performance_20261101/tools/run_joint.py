"""Run a serialized metadata-only board step; no model invocation or private payload export."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

HERE = Path(__file__).resolve().parents[1]
LIVE = HERE.parent / 'live_follow_test_20261101'
PROJECT = HERE.parents[3]
sys.path.insert(0, str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh


def main():
    p=argparse.ArgumentParser();p.add_argument('step');p.add_argument('--timeout',type=int,default=45);p.add_argument('--compact',action='store_true')
    a=p.parse_args();assert a.step.replace('_','').isalnum() and 1<=a.timeout<=150
    binding=LIVE/'package/original_direction_fix/camera_binding_runtime.py'
    assert hashlib.sha256(binding.read_bytes()).hexdigest()=='7e6a08fd97aec82cc0326c6d31d9a745b75bfa218a506ba5e8d3b3be29616878'
    source=binding.read_text('utf-8')+'\n'+(HERE/'remote/common.py').read_text('utf-8')+'\n'+(HERE/'remote'/(a.step+'.py')).read_text('utf-8')
    raw=ssh('python3 -B -',source,timeout=a.timeout)
    value=json.loads(raw)
    envelope=dict(step=a.step,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),source_sha256=hashlib.sha256(source.encode()).hexdigest(),result=value)
    target=HERE/'evidence'/(a.step+'_'+str(time.time_ns())+'.json');target.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(envelope,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    with target.open('xb') as f:f.write(data)
    preview={k:value.get(k) for k in ('status','error','restore_error','after_error','original_page','summary')} if a.compact else value
    print(json.dumps(dict(evidence=str(target),sha256=hashlib.sha256(data).hexdigest(),result=preview),ensure_ascii=False))


if __name__=='__main__':main()
