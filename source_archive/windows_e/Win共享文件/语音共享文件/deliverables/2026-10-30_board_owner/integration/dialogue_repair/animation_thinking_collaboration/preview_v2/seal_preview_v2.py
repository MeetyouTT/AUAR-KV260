"""Local ordering/failure tests and immutable v2 preview package seal."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace as S
import zipfile

HERE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def test_capture_order():
    tree=ast.parse((HERE/'preview_public_states.py').read_text(encoding='utf-8'))
    main=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main')
    defs={node.name:node for node in main.body if isinstance(node,ast.FunctionDef)}
    for width,expected_error in ((423,False),(422,True)):
        with tempfile.TemporaryDirectory(prefix='public-render-order-') as directory:
            events=[];diagnostics=[];errors=[]
            state=dict(rendered=False)
            def native_render(*_):
                events.append('render');state['rendered']=True
                return dict(sequence=7,eye=10.,mouth=0.)
            def native_capture(path,*_):
                assert state['rendered'],'Readback is after swap or before render'
                events.append('capture');Path(path).write_bytes(b'PUBLIC_FAKE_FRAMEBUFFER')
            def swap():events.append('swap');state['rendered']=False
            area=S(native=S(render=native_render,capture=native_capture,offer=lambda _:True),
                egl=S(current=lambda:events.append('current'),resize=lambda *_:events.append('resize'),
                    swap=swap,e=S(eglGetCurrentContext=lambda:123),context=123),
                get_allocated_width=lambda:width,get_allocated_height=lambda:516,get_scale_factor=lambda:1,
                frame_observer=lambda _:events.append('observe'))
            env=dict(area=area,mailbox=S(consume=lambda:None,lock=threading.Lock(),latest_stats={}),
                controls={7:dict(phase='THINKING',phase_elapsed=.7)},args=S(capture_character=True),
                CAPTURE_PHASES={'THINKING'},captures={},evidence=Path(directory),sha=sha,
                time=time,diagnostics=diagnostics,errors=errors,
                quit_preview=lambda code:errors.append(code))
            for name in ('diagnose','capture_before_swap','render_once_before_capture'):
                exec(compile(ast.Module(body=[defs[name]],type_ignores=[]),str(HERE/'preview_public_states.py'),'exec'),env)
            env['render_once_before_capture'](area,None)
            if not expected_error:
                assert events==['current','resize','render','capture','swap','observe'],events
                assert not errors and not diagnostics
            else:
                assert events==['current','resize','render'],events
                assert diagnostics==[dict(stage='CAPTURE_SIZE_CHECK',exception_class='ValueError',width=422,
                    height=516,context_current=True,allocation_width=422,allocation_height=516,scale=1)]
                assert errors==['PREVIEW_NATIVE_OR_CAPTURE_FAILED']


def main():
    test_capture_order()
    parent=HERE.parent
    original=json.loads((parent/'PREVIEW_SPEC.json').read_text(encoding='utf-8'))
    for relative,expected in original['overlay_pins'].items():
        assert sha(HERE/'paired_overlay/aura'/relative)==sha(parent/'paired_overlay/aura'/relative)==expected
    assert sha(parent/'public_preview_source.zip')=='e73b2c4a00af116e471802837019869d0606ce748ce857c52f0c6b55ad780c6a'
    original.update(script_sha256=sha(HERE/'preview_public_states.py'),revision='capture-before-swap-v2',
        capture_order='same native render, then renderer.capture, then egl.swap',
        diagnostics_scope='fixed stage enum, whitelisted exception class and numeric dimensions/context only')
    save(HERE/'PREVIEW_SPEC.json',original)
    names=['preview_public_states.py','PREVIEW_SPEC.json','PREVIEW_PLAN.txt',
           'paired_overlay/PAIRING_RECEIPT.json','PAIRED_TEST_RESULTS.json']
    names+=['paired_overlay/aura/'+name for name in original['overlay_pins']]
    archive=HERE/'public_preview_source_v2.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
        for name in names:output.write(HERE/name,name)
    receipt=dict(schema='aura.animation-thinking-preview-capture-v2.v1',
        status='LOCAL_RENDER_ORDER_TESTED_REQUIRES_BOARD_PREVIEW',
        script_sha256=sha(HERE/'preview_public_states.py'),spec_sha256=sha(HERE/'PREVIEW_SPEC.json'),
        archive=dict(name=archive.name,sha256=sha(archive),bytes=archive.stat().st_size),
        overlay_pins=original['overlay_pins'],original_overlay_byte_identical=True,
        v1_failed_package_retained=True,capture_order_test_passed=True,numeric_size_failure_diagnostic_test_passed=True,
        local_public_input_validation='run --validate-only against existing public assets',
        gtk_or_egl_opened_locally=False,device_access=False,production_modified=False,
        actual_v1_cause_confirmed=False,native_capture_or_visual_pass_claimed=False)
    save(HERE/'PREVIEW_V2_HANDOFF.json',receipt)
    print(json.dumps(receipt))


if __name__=='__main__':main()
