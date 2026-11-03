"""Run the original frozen sampler body with only new source/owner context supplied externally."""
from pathlib import Path
import hashlib
import json
import sys
import time

HERE=Path(__file__).resolve().parents[1]
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh


def main():
    root=HERE/'package/single_projection'
    manifest=json.loads((root/'BUNDLE_MANIFEST.json').read_bytes())
    for name,pin in manifest['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==pin
    spec=json.loads((root/'candidate_spec.json').read_bytes())
    ready_path=HERE/'evidence/single_projection_forward_ready_1793533601945768100.json'
    ready=json.loads(ready_path.read_bytes())['result'];assert ready['status']=='PRODUCTION_BOARD_BUSINESS_READY'
    assert ready['startup_sha256']==spec['startup_sha256']
    before=json.loads((HERE/'evidence/baseline_1793532356967963000.json').read_bytes())['result']
    owners=dict(camera=before['after']['owners']['camera'])
    for role in ('supervisor','gtk'):
        row=ready[role];owners[role]=dict(pid=row['pid'],birth_ticks=int(row['birth']),command_sha256=row['cmdline_sha256'])
    body=(HERE/'remote/baseline.py').read_bytes()
    assert hashlib.sha256(body).hexdigest()=='e89c6cc14eb00342ffda480b2ddd126a9381c49afe0c1b0b3b821cf282a2d7ae'
    common=(HERE/'remote/common.py').read_text('utf-8')
    old_manifest='8ff79452570385921e06c098b5d42c2ea1ef5dfb84d81dfa7f53a9295373d0e8'
    assert common.count(old_manifest)==2
    common=common.replace(old_manifest,spec['source_manifest_sha256'])
    marker="before,initial,health=preflight();original_page=before['state']['page']"
    text=body.decode('utf-8');assert text.count(marker)==1
    definitions,tail=text.split(marker,1);tail=marker+tail
    source=(root/'camera_binding_runtime.py').read_text('utf-8')+'\n'+common+'\n'
    source+='STARTUP_SHA='+repr(spec['startup_sha256'])+'\nEXPECTED_OWNERS='+repr(owners)+'\n'
    source+=definitions+'\n'
    # The unchanged sampler contains the old GTK PID only at the thread-sampling
    # boundary. Remap that context argument without changing its sampling body.
    source+="_original_thread_sample=thread_sample\ndef thread_sample(pid,tid):\n if pid==496789:pid=EXPECTED_OWNERS['gtk']['pid']\n if tid==496789:tid=EXPECTED_OWNERS['gtk']['pid']\n return _original_thread_sample(pid,tid)\n"
    source+=tail
    result=json.loads(ssh('python3 -B -',source,timeout=115))
    value=dict(step='single_projection_post_baseline',utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
               source_sha256=hashlib.sha256(source.encode()).hexdigest(),original_sampler_body_sha256=hashlib.sha256(body).hexdigest(),
               original_sampler_body_unchanged=True,context_only_changes=dict(startup=spec['startup_sha256'],
                 source_manifest=spec['source_manifest_sha256'],owners=owners,thread_pid_context_remap={496789:owners['gtk']['pid']}),
               result=result)
    output=HERE/'evidence'/('single_projection_post_baseline_'+str(time.time_ns())+'.json')
    raw=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    with output.open('xb') as f:f.write(raw)
    print(json.dumps(dict(evidence=str(output),sha256=hashlib.sha256(raw).hexdigest(),status=result['status'],
                          error=result['error'],restore_error=result['restore_error'],after_error=result['after_error'],
                          summary=result['summary']),ensure_ascii=False))


if __name__=='__main__':main()
