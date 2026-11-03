#!/usr/bin/env python3
"""Generate the three display-adapter wire schemas from frozen state enums."""
import json
from pathlib import Path
import sys

REPO = Path('/home/ghmd/Win共享文件/共享文件夹/aura')
sys.path.insert(0,str(REPO))
from board.interaction.ui_contract import ACTIONS, MODULE_STATES, PROTOCOL

ROOT = REPO/'common/schemas'
STRING = {'type':'string','maxLength':96}
ID = dict(STRING,minLength=1)
INT = {'type':'integer','minimum':0,'maximum':2**53-1}
POSITIVE = dict(INT,minimum=1)
TARGET = {'type':'object','additionalProperties':False,
          'required':['camera_epoch','track_id','track_generation'],
          'properties':{'camera_epoch':ID,'track_id':POSITIVE,'track_generation':POSITIVE}}
FRAME = {'type':'object','additionalProperties':False,
         'required':['camera_epoch','frame_id','captured_mono_ms'],
         'properties':{'camera_epoch':ID,'frame_id':POSITIVE,'captured_mono_ms':INT}}
CONTEXT = {'type':'object','additionalProperties':False,
           'required':['session_id','request_id','generation'],
           'properties':{'session_id':ID,'request_id':STRING,'generation':INT}}
OWNER = {'protocol_version':{'const':PROTOCOL},'board_boot_id':ID,'service_epoch':ID,
         'command_id':ID,'ui_epoch':ID,'ui_generation':INT}


def schema(title, properties, required=None):
    return {'$schema':'http://json-schema.org/draft-07/schema#','title':title,
            'type':'object','additionalProperties':False,
            'required':list(properties) if required is None else required,'properties':properties}


def write(name, value):
    (ROOT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    modules = {}
    for name,states in MODULE_STATES.items():
        modules[name] = {'type':'object','required':['state'],
                         'properties':{'state':{'enum':list(states)},'detail':{'type':'string','maxLength':160}}}
    modules['interaction']['properties'].update(
        transcript={'type':'string','maxLength':2000},reply={'type':'string','maxLength':8000},
        timings_ms={'type':'object','additionalProperties':False,
                    'properties':{k:{'type':'number','minimum':0,'maximum':3600000}
                                  for k in ('asr','vlm','tts','first_audio')}})
    modules['vision']['properties']['people_count'] = dict(INT,maximum=1000)
    modules['target']['properties'].update(selected={'anyOf':[TARGET,{'type':'null'}]},
        tracks={'type':'array','maxItems':16,'items':schema('Visible target',{
            'key':TARGET,'label':{'type':'string','minLength':1,'maxLength':48}})})
    modules['identity']['properties'].update(person_id=STRING,display_name=STRING,db_version=INT,
        people={'type':'array','maxItems':32,'items':schema('Identity choice',{
            'person_id':ID,'display_name':{'type':'string','minLength':1,'maxLength':48}})})
    properties = {'protocol_version':{'const':PROTOCOL},'board_boot_id':ID,'service_epoch':ID,
        'sequence':POSITIVE,'observed_mono_ms':INT,'ttl_ms':{'type':'integer','minimum':100,'maximum':5000},
        'source_kind':{'enum':['actual','fixture']},'context':CONTEXT,
        'modules':{'type':'object','additionalProperties':False,'properties':modules},
        'capabilities':{'type':'object','additionalProperties':False,
                        'properties':{k:{'type':'boolean'} for k in ACTIONS}},
        'preview':{'anyOf':[FRAME,{'type':'null'}]}}
    value = schema('AURA touchscreen snapshot adapter v1',properties,[k for k in properties if k != 'preview'])
    value['description'] = 'I03/I04/I05/I07 display adapter. Times use this board monotonic milliseconds. Runtime additionally checks boot, freshness, ordering and retired epochs.'
    write('board_ui_snapshot.schema.json',value)
    properties = dict(OWNER,snapshot_sequence=POSITIVE,context=CONTEXT,
                      issued_mono_ms=INT,deadline_mono_ms=INT,action={'enum':list(ACTIONS)},params={'type':'object'})
    value = schema('AURA touchscreen operation adapter v1',properties)
    choices = []
    for name in ACTIONS:
        params = {}
        if name in ('target_select','identity_enroll'):params['target'] = TARGET
        if name == 'identity_enroll':params.update(display_name={'type':'string','minLength':1,'maxLength':48},confirmed={'const':True})
        if name == 'identity_delete':params.update(person_id=ID,db_version=INT,confirmed={'const':True})
        if name == 'ask_frame':params['frame'] = FRAME
        choices.append({'properties':{'action':{'const':name},'params':schema(name+' parameters',params)}})
    value['oneOf'] = choices
    value['description'] = 'Acceptance is not completion. Provider must recheck deadline, source context, capability, target lifetime and database transaction before applying. No ARM, PWM, raw register or fault clear command.'
    write('board_ui_command.schema.json',value)
    write('board_ui_ack.schema.json',schema('AURA touchscreen acceptance receipt v1',
          dict(OWNER,accepted={'type':'boolean'},detail={'type':'string','maxLength':160})))
    print(json.dumps({'protocol':PROTOCOL,'schemas':3,'module_domains':list(MODULE_STATES),'actions':list(ACTIONS)}))


if __name__ == '__main__':main()
