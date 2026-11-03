"""Local AST/source-only trace of the failed candidate HTTP bind."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
AURA=ROOT.parent/'resume_yuki_business_candidate_v2/candidate/aura'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def cls_method(source,cls,name):
    owner=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.ClassDef) and n.name==cls)
    return next(n for n in owner.body if isinstance(n,ast.FunctionDef) and n.name==name)
def super_init_count(node):
    return sum(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='__init__'
        and isinstance(n.func.value,ast.Call) and isinstance(n.func.value.func,ast.Name)
        and n.func.value.func.id=='super' for n in ast.walk(node))


def main():
    paths=['tools/board_avatar_pan.py','tools/face_pan_controls.py','tools/pan_controls.py',
           'tools/board_avatar_gtk.py','tools/realtime_bridge.py','tools/yuki_business_gui.py']
    texts={name:(AURA/name).read_text(encoding='utf-8') for name in paths}
    init=cls_method(texts['tools/board_avatar_gtk.py'],'BoardAvatarStage','__init__')
    bridges=[n for n in ast.walk(init) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='StageBridge']
    window=[n for n in ast.walk(init) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
            and n.func.attr=='build_window']
    base=json.loads((ROOT/'actual_ui_baseline.json').read_text(encoding='utf-8'))
    launcher=base['launcher']['content']
    assert sha(launcher.encode())==base['launcher']['sha256']
    tree=ast.parse(launcher)
    port_guard=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='check_port_unused')
    supervisor=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='supervise')
    calls=[n for n in ast.walk(supervisor) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='check_port_unused']
    spawn=[n for n in ast.walk(supervisor) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='Popen']
    bind_class=next(n for n in ast.walk(ast.parse(texts['tools/realtime_bridge.py'])) if isinstance(n,ast.ClassDef) and n.name=='ExclusiveServer')
    reuse=next(ast.literal_eval(n.value) for n in bind_class.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='allow_reuse_address' for t in n.targets))
    failure=json.loads((ROOT/'actual_startup_failure.json').read_text(encoding='utf-8'))
    result=dict(status='LOCAL_SOURCE_TRACE_ONLY_NO_DEVICE_CALL',
        source_zip_sha256='2c25b6a91a635a9bb70eef00cdc180829c503cdba3382135f8366c72e3242334',
        source_sha256={name:sha((AURA/name).read_bytes()) for name in paths},
        failure_input_sha256=sha((ROOT/'actual_startup_failure.json').read_bytes()),candidate_pid=failure['candidate_pid'],
        initialization=dict(chain=['board_avatar_pan.main stage_type(original)',
            'FaceStage.__init__ single super','PanStage.__init__ single super','BoardAvatarStage.__init__'],
            face_super_init_calls=super_init_count(cls_method(texts['tools/face_pan_controls.py'],'FaceStage','__init__')),
            pan_super_init_calls=super_init_count(cls_method(texts['tools/pan_controls.py'],'PanStage','__init__')),
            board_stage_bridge_calls=len(bridges),bridge_line=bridges[0].lineno,
            build_window_line=window[0].lineno,
            failure_before_window_and_native_first_swap=bridges[0].lineno<window[0].lineno,
            business_activate_before_failure=False),
        bind=dict(module='tools/realtime_bridge.py',server='ExclusiveServer',allow_reuse_address=reuse,
                  address='127.0.0.1',port=8783,error='EADDRINUSE'),
        original_supervisor=dict(sha256=base['launcher']['sha256'],port_wait_default_seconds=ast.literal_eval(port_guard.args.defaults[0]),
            port_wait_call_line=calls[0].lineno,child_spawn_line=spawn[0].lineno,
            waits_before_spawn=calls[0].lineno<spawn[0].lineno,
            source_note='Explicit original comment: exclusive HTTP can leave TIME_WAIT; waits without killing another process.'),
        direct_candidate_launch=dict(helper='launch_v2.py',
            source_sha256=sha((ROOT/'launch_v2.py').read_bytes()),
            port_wait_implemented='check_port_unused' in (ROOT/'launch_v2.py').read_text(encoding='utf-8')),
        conclusion='Pinned source has one GTK initializer path and one StageBridge bind; no source evidence of double initialization.',
        inference='Exclusive rebind during old8783 TIME_WAIT is a strong candidate because direct launch skips the existing supervisor port wait. Live owner/state metadata is required to confirm it.',
        parent_readonly_followup='Classify /proc/net/tcp{,6} local port224F: state0A LISTEN needs exact owner proof; state06 TIME_WAIT without LISTEN supports wait. Preserve exclusive bind semantics and all other owners.',
        next_candidate_source_option='Before future direct launch, under same flock/guard/source checks and original finite startup budget, wait for a bind probe with the same no-reuse semantics. Do not enable reuse, change ports blindly, kill an owner or modify TCP sysctls.',
        actual_inference_or_gles_test=False,device_calls=0,service_calls=0,source_changed=False)
    assert result['initialization']['face_super_init_calls']==result['initialization']['pan_super_init_calls']==1
    assert len(bridges)==1 and reuse is False and result['original_supervisor']['waits_before_spawn']
    (ROOT/'startup_bind_source_trace.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(status=result['status'],single_bridge=True,single_super_chain=True,
        exclusive_no_reuse=True,original_wait_seconds=result['original_supervisor']['port_wait_default_seconds'],
        direct_launch_has_wait=result['direct_candidate_launch']['port_wait_implemented'],
        failed_before_build_window=result['initialization']['failure_before_window_and_native_first_swap'])))


if __name__=='__main__':main()
