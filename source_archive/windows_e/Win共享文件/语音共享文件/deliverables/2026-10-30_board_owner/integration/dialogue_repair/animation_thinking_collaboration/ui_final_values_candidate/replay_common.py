"""Synthetic production presentation fixture, without devices or private data."""
from collections import Counter
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


FIXTURE=load('frozen_phase1_ui_fixture',HERE.parent/'ui_responsiveness_v18/test_ui_responsiveness.py')


def owner():
    capture=SimpleNamespace(snapshot=lambda:dict(state='RECORDING',input_ready=True))
    recording=SimpleNamespace(capture=capture,monitor_enabled=True,monitor_state='WAITING_SPEECH',
        monitor_reason='CURRENT_TURN_CANCELLED',recording_state='RECORDING',wake_word_required=False,
        monitor_stats={})
    runtime=SimpleNamespace(config=SimpleNamespace(data_origin='board',model_host='192.0.2.1',model_port=8797),
        public=lambda:dict(started=True,mode='board-business-board'))
    return SimpleNamespace(recording=recording,runtime=runtime)


def make_stage(module,production=True):
    stage=FIXTURE.FakeStage(module)
    stage.module=module;stage._ui_set=lambda *args:module.BoardAvatarStage._ui_set(stage,*args)
    stage.board_business=owner() if production else None
    snapshot=dict(source_kind='live',preview=None,capabilities={},modules=dict(
        camera=dict(state='READY'),identity=dict(state='UNKNOWN'),
        target=dict(state='NONE'),vision=dict(state='READY',people_count=0,count_kind='faces')))
    stage.services=SimpleNamespace(read=lambda:dict(snapshot=copy.deepcopy(snapshot),link='READY',
        error='',results=[],pending_count=0,connection={}))
    for name in ('edit_host','edit_port','connect','disconnect'):stage.controls[name]
    stage.host_entry.values.setdefault('editable',True)
    stage.port_entry.values.setdefault('editable',True)
    return stage


def state():
    value=FIXTURE.state_for()
    value['automatic_conversation']={}
    value['local_recording'].update(state='RECORDING',can_start=False,can_stop=True)
    return value


def refresh(stage,value,business_module):
    FIXTURE.render(stage,value)
    business_module.project_business_ui(stage,value)


def trace_applied(stage,module):
    counts=Counter()
    def write(widget,method,value):
        applied=module.BoardAvatarStage._ui_set(stage,widget,method,value)
        if applied:
            names=[name for name,obj in stage.widgets.items() if obj is widget]
            names += ['controls.'+name for name,obj in stage.controls.items() if obj is widget]
            names += ['device_cards.'+name for name,obj in stage.device_cards.items() if obj is widget]
            names += ['insight_labels.'+name for name,obj in stage.insight_labels.items() if obj is widget]
            label=names[0] if names else 'unmapped_widget'
            counts[(label,method)] += 1
        return applied
    stage._ui_set=write
    return counts
