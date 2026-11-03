"""Fake scheduler/process tests only: no priority syscall, mic or model."""
import ast
import importlib.util
import io
from pathlib import Path
import sys
import threading
from types import SimpleNamespace as NS

import pytest

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'aura'))


def load(relative,name):
    path=HERE/'after/aura'/relative
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@pytest.fixture
def priority(monkeypatch):
    module=load('board/runtime/audio/board_capture_priority.py','isolated_capture_priority')
    state={'nice':0,'calls':[],'denied':False,'fail_restore':False}
    monkeypatch.setattr(module.sys,'platform','linux')
    monkeypatch.setattr(module.platform,'machine',lambda:'aarch64')
    monkeypatch.setattr(module.threading,'get_native_id',lambda:42)
    monkeypatch.setattr(module.os,'PRIO_PROCESS',0,raising=False)
    def get(which,tid):
        assert which==0 and tid==42
        return state['nice']
    def set_(which,tid,nice):
        assert which==0 and tid==42
        state['calls'].append((which,tid,nice))
        if nice==-10 and state['denied']:raise PermissionError()
        if nice==0 and state['fail_restore']:raise OSError()
        state['nice']=nice
    monkeypatch.setattr(module.os,'getpriority',get,raising=False)
    monkeypatch.setattr(module.os,'setpriority',set_,raising=False)
    return module,state


@pytest.mark.parametrize('kind',['automatic','barge'])
@pytest.mark.parametrize('fail_body',[False,True])
def test_only_current_tid_changes_and_original_priority_is_restored(priority,monkeypatch,kind,fail_body):
    module,state=priority
    parent=module.BoardAutomaticCapture if kind=='automatic' else module.BoardBargeCapture
    cls=module.PriorityBoardAutomaticCapture if kind=='automatic' else module.PriorityBoardBargeCapture
    def body(self,process):
        assert state['nice']==-10
        if fail_body:raise RuntimeError('public-consumer-failure')
        return b'public-pcm'
    monkeypatch.setattr(parent,'_read_pcm',body)
    obj=cls.__new__(cls)
    if fail_body:
        with pytest.raises(RuntimeError,match='public-consumer-failure'):obj._read_pcm(object())
    else:assert obj._read_pcm(object())==b'public-pcm'
    assert state['nice']==0 and state['calls']==[(0,42,-10),(0,42,0)]
    assert obj._capture_priority_report['restored'] and obj._capture_priority_report['native_tid']==42
    assert obj._capture_priority_report['error_code']==''


def test_priority_is_fixed_and_constructor_does_no_scheduler_or_device_operation(priority):
    module,state=priority
    capture=module.PriorityBoardAutomaticCapture(lambda:False,frontend_factory=lambda:None)
    assert state['calls']==[] and capture.state=='IDLE' and capture._process is None
    assert capture.snapshot()['capture_priority']['applied'] is False


def test_original_nonzero_nice_is_restored_exactly(priority,monkeypatch):
    module,state=priority;state['nice']=5
    monkeypatch.setattr(module.BoardAutomaticCapture,'_read_pcm',lambda self,p:b'public-pcm')
    capture=module.PriorityBoardAutomaticCapture.__new__(module.PriorityBoardAutomaticCapture)
    assert capture._read_pcm(object())==b'public-pcm'
    assert state['nice']==5 and state['calls']==[(0,42,-10),(0,42,5)]
    assert capture._capture_priority_report['restored_nice']==5


class FakeProcess:
    def __init__(self):self.stdout=io.BytesIO();self.killed=False;self.waited=False
    def poll(self):return 0 if self.killed else None
    def kill(self):self.killed=True
    def wait(self,timeout=None):self.waited=True;return 0


@pytest.mark.parametrize('kind',['automatic','barge'])
@pytest.mark.parametrize('failure',['unsupported','permission','restore'])
def test_failure_inside_read_reaches_original_mcp_cleanup_and_no_success(priority,monkeypatch,kind,failure):
    module,state=priority
    cls=module.PriorityBoardAutomaticCapture if kind=='automatic' else module.PriorityBoardBargeCapture
    closed=[]
    if kind=='automatic':obj=cls(lambda:False,frontend_factory=lambda:None)
    else:obj=cls(NS(),frontend_factory=lambda:None)
    classifier=NS(close=lambda:closed.append('frontend'))
    obj.endpoint=NS(frame_classifier=classifier)
    if kind=='barge':
        obj.echo=NS(close=lambda:closed.append('echo'))
        obj.unsubscribe=lambda:closed.append('reference')
        obj.verifier=NS(close=lambda:closed.append('verifier'))
    if failure=='unsupported':monkeypatch.setattr(module.platform,'machine',lambda:'x86_64')
    elif failure=='permission':state['denied']=True
    else:
        state['fail_restore']=True
        parent=module.BoardAutomaticCapture if kind=='automatic' else module.BoardBargeCapture
        def body(self,process):
            self._priority_setup_cleanup()
            return b'\x00'*3200
        monkeypatch.setattr(parent,'_read_pcm',body)
    released=[]
    obj._release_owner=lambda:released.append(True)
    process=FakeProcess()
    obj._read(process,io.BytesIO(),'public-capture',1,1000)
    assert obj.state=='ERROR' and obj._result is None
    assert process.killed and process.waited and process.stdout.closed and released==[True]
    assert 'frontend' in closed
    if kind=='barge':assert set(closed)=={'frontend','echo','reference','verifier'}
    report=obj._capture_priority_report
    assert report['error_code'].startswith('capture_thread_priority_')
    if failure=='permission':assert state['nice']==0 and report['restored']


def test_options_do_not_enable_combined_or_priority_by_default():
    selection=load('tools/production_frontend_selection.py','isolated_frontend_selection')
    assert selection.validate_frontend_options({})==('baseline',0)
    assert selection.validate_frontend_options({'capture_priority_nice':-10})==('baseline',-10)
    assert selection.validate_frontend_options({'frontend_optimization':'combined'})==('combined',0)
    for value in (True,-20,1,'-10'):
        with pytest.raises(ValueError):selection.validate_frontend_options({'capture_priority_nice':value})


def test_pool_constructs_exactly_one_gate_and_combined_remains_separate(monkeypatch):
    selection=load('tools/production_frontend_selection.py','isolated_frontend_selection')
    import board.runtime.audio.board_capture as capture
    import board.runtime.audio.board_gtcrn_fft as original
    calls=[]
    monkeypatch.setattr(capture,'BoardFrontendPool',lambda gate:NS(gate=gate))
    monkeypatch.setattr(original,'BoardFftSpeechGate',lambda directory,**kw:calls.append(('baseline',directory,kw)) or 'baseline')
    combined=NS(ReuseFftSpeechGate=lambda directory,**kw:calls.append(('combined',directory,kw)) or 'combined')
    monkeypatch.setitem(sys.modules,'board.runtime.audio.board_gtcrn_reuse',combined)
    assert selection.create_frontend_pool('public-resource',optimization='baseline',num_threads=1).gate=='baseline'
    assert selection.create_frontend_pool('public-resource',optimization='combined',num_threads=1).gate=='combined'
    assert calls==[('baseline','public-resource',{'num_threads':1}),
                   ('combined','public-resource',{'num_threads':1,'buffer_reuse':True,'io_binding':True})]
    with pytest.raises(ValueError):selection.create_frontend_pool('public-resource',optimization='combined',num_threads=2)


def test_both_capture_factories_use_existing_runtime_hooks_and_no_base_mutation(monkeypatch):
    selection=load('tools/production_frontend_selection.py','isolated_frontend_selection')
    constructed=[];barge=[]
    types=NS(PriorityBoardAutomaticCapture=lambda *a,**kw:constructed.append((a,kw)) or 'auto',PriorityBoardBargeCapture=object())
    monkeypatch.setitem(sys.modules,'board.runtime.audio.board_capture_priority',types)
    acquire=lambda:None
    gui=NS(frontend=NS(acquire=acquire),runtime=NS(make_barge_capture_factory=lambda *a,**kw:barge.append((a,kw)) or 'barge'))
    output=object();visual=NS(output=output,reply='public reply')
    options=selection.priority_recording_options(gui,visual)
    assert options['audio_frontend'] is None and options['barge_capture_factory']=='barge'
    assert options['auto_capture_factory']('playback-owner')=='auto'
    assert constructed==[(('playback-owner',),{'frontend_factory':acquire})]
    assert barge[0][0][0] is output and barge[0][0][2] is acquire
    assert barge[0][1]=={'capture_type':types.PriorityBoardBargeCapture}
    assert barge[0][0][1]()=='public reply'


def test_factory_patch_is_narrow_and_python39_compatible():
    for path in (HERE/'after/aura').rglob('*.py'):ast.parse(path.read_bytes(),filename=str(path),feature_version=(3,9))
    tree=ast.parse((HERE/'after/aura/tools/production_board_business_gui.py').read_bytes())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='recording_options')
    ns={}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'<factory-options>','exec'),ns)
    class Parent:
        def recording_options(self,visual):return 'unchanged-baseline-capture'
    # __class__ cell would be bound by the real class; inspect its AST rather
    # than fabricate a different production constructor or load any models.
    assert 'capture_priority_nice' in ast.unparse(method) and 'super().recording_options' in ast.unparse(method)
