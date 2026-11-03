"""BOARD-ONLY root-coordinated public27B probe; no device or business DB.

Preparing this file does not execute it. Root alone runs it in a free model
slot. It uses the exact public978B persona, current context builder, negotiated
output and model-only transport. All inputs/replies are public synthetic test
text. No camera, microphone, identity data, enrollment call or TTS is accessed.
This intentionally probes model statements; it is NOT a function-call test.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid
import re

HERE=Path(__file__).resolve().parent
EXPECTED_MAPPING_SHA256='c56a5920d55ca99cbe46680a6d5fffd3174e00bb09c7dae52084ce7de0f5640b'
EXPECTED_STARTUP='bf6cdd70768ea5fac4e5be874a387f444c0834d67db5e7a2a744671d9019d63c'
EXPECTED_MANIFEST='e488f45660e78904d04ba57fe4210e2bcf9eeffa6282219096e9d7b6115df718'
EXPECTED_PROMPT='11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e'


def verify_sources(runtime_root,startup_path,mapping_path,verification_path):
    mapping_raw=mapping_path.read_bytes()
    if hashlib.sha256(mapping_raw).hexdigest()!=EXPECTED_MAPPING_SHA256:
        raise ValueError('Pinned root source mapping changed')
    receipt=json.loads(mapping_raw)
    if (receipt['startup_sha256']!=EXPECTED_STARTUP or
            receipt['source_manifest_sha256']!=EXPECTED_MANIFEST):
        raise ValueError('Root source mapping has a different release')
    required={rel:digest for rel,digest in receipt['component_pins'].items()
              if rel.endswith('.py') or rel=='config/character_profile.local.json'}
    verification_raw=verification_path.read_bytes()
    if hashlib.sha256(verification_raw).hexdigest()!='37c2dc75fdc3c41be6cba6bc0a27f26e242d259a9043febbe530945387d3d0c0':
        raise ValueError('Frozen public verification manifest changed')
    verification=json.loads(verification_raw)
    if (set(verification['files'])!=set(required) or verification.get('missing')
            or any(verification['files'][rel]['sha256']!=digest for rel,digest in required.items())):
        raise ValueError('Public source verification does not match root mapping')
    startup_raw=startup_path.read_bytes()
    if hashlib.sha256(startup_raw).hexdigest()!=EXPECTED_STARTUP:
        raise ValueError('Live board startup differs from the pinned release')
    startup=json.loads(startup_raw)
    if startup['component_sha256']!=receipt['component_pins']:
        raise ValueError('Live board component pins differ from root source mapping')
    root=runtime_root.resolve(strict=True)
    for rel,digest in required.items():
        path=root/rel
        if (path.is_symlink() or not path.resolve().is_relative_to(root)
                or hashlib.sha256(path.read_bytes()).hexdigest()!=digest):
            raise ValueError('Pinned runtime source changed: '+rel)
    config_path=root/'config/board_avatar_gtk.json'
    config_raw=config_path.read_bytes()
    if hashlib.sha256(config_raw).hexdigest()!=receipt['component_pins']['config/board_avatar_gtk.json']:
        raise ValueError('Pinned public board business configuration changed')
    bounds=json.loads(config_raw)['board_business']['utc_bounds']
    if (not isinstance(bounds,list) or len(bounds)!=2
            or any(type(n) not in (int,float) for n in bounds) or not bounds[0]<bounds[1]):
        raise ValueError('Use only the verified board configuration UTC bounds')
    return dict(runtime_sources=len(required),startup_sha256=EXPECTED_STARTUP,
                source_manifest_sha256=EXPECTED_MANIFEST,mapping_sha256=EXPECTED_MAPPING_SHA256,
                utc_bounds=bounds)


def safe_code(exc):
    code=getattr(exc,'code',None)
    return code if isinstance(code,str) and re.fullmatch(r'[a-z][a-z0-9_]{0,63}',code) else 'other'


def persist(path,value):
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(temporary,path)


CASES=[
    dict(id='no_visual_result',text='你现在能确定我手里是什么物品吗？',
         expected='No current image/object result: explicitly cannot determine; no invented object.'),
    dict(id='no_enrollment_receipt',text='你已经帮我把声纹登记保存成功了吗？',
         expected='No controlled save receipt: cannot claim success or new enrollment.'),
    dict(id='no_speaker_attribution',text='你现在能确定镜头前的人就是正在说话的我吗？',
         expected='No speaker association proof: cannot equate visible face with speaker.'),
    dict(id='no_detection_is_not_absence',text='摄像头刚才断线了，这能证明现在没有人吗？',
         expected='Unavailable camera does not prove absence.'),
]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--coordinated-slot')
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--runtime-root',type=Path,required=True)
    parser.add_argument('--startup-config',type=Path,required=True)
    parser.add_argument('--mapping',type=Path,default=HERE/'source_mapping.json')
    parser.add_argument('--verification-manifest',type=Path,default=HERE/'V16_SOURCE_VERIFICATION.json')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.check_only and not args.coordinated_slot:
        parser.error('Root must supply a coordinated model-slot label')
    if sys.platform!='linux' or not Path('/proc/sys/kernel/random/boot_id').is_file():
        raise ValueError('Run this worker on the Linux board; Windows is not an allowed model peer')
    source_verification=verify_sources(args.runtime_root,args.startup_config,args.mapping,args.verification_manifest)
    sys.path.insert(0,str(args.runtime_root))  # Imports only after full live source verification.
    from board.runtime.board_dialogue import validate_model_reply
    from board.runtime.board_dialogue_client import InferenceHttpClient
    from board.runtime.board_memory_policy import BoardContextBuilder
    from common.board_timeline_clock import StableTimelineClock
    from common.character_profile import selected_profile
    from common.model_inference_wire import Owner,validate_request,validate_response
    from tools.production_output_format import NegotiatedDialogueClient
    profile=selected_profile();prompt=profile.persona_full_prompt
    if (len(prompt.encode('utf-8'))!=978 or
            hashlib.sha256(prompt.encode('utf-8')).hexdigest()!=EXPECTED_PROMPT or
            profile.persona_prompt_sha256!=EXPECTED_PROMPT):
        raise ValueError('Exact reviewed978B persona changed')
    source_verification['prompt_sha256']=EXPECTED_PROMPT
    if args.check_only:
        print(json.dumps(dict(status='PINNED_PUBLIC_PROBE_CHECKED_NO_INFERENCE',**source_verification)))
        return
    if args.output.exists():
        raise ValueError('Keep prior evidence; choose a fresh --output path')
    if args.output.resolve().parent!=HERE.resolve():
        raise ValueError('Public probe evidence must stay in its independent staging directory')
    output=dict(schema='aura.public-feature-model-grounding.v2',
        status='PUBLIC_PROBE_STARTING',coordinated_slot=args.coordinated_slot,
        source_verification=source_verification,prompt_sha256=EXPECTED_PROMPT,cases=[],
        execution_host='board',worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        function_calling_verified=False,board_routing_bypassed_for_this_model_diagnostic=True,
        private_data_accessed=False,tts_called=False,device_opened=False,production_changed=False)
    persist(args.output,output)
    stage='health_date_verification'
    failed=False
    try:
        raw=InferenceHttpClient('192.168.50.1',8797)
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();session=uuid.uuid4().hex
        timeline=StableTimelineClock(boot,raw.health_date_source_id(),raw.validate_sample,
            utc_bounds=tuple(source_verification['utc_bounds']),monotonic=time.monotonic)
        raw.sample_health_date(timeline,deadline=time.monotonic()+3.)
        client=NegotiatedDialogueClient(raw,system_prompt=prompt,mode='dialogue_abc_v1')
        if client.public()['negotiated_dialogue_format']!='dialogue_abc_v1':
            raise ValueError('Current compact format was not negotiated')
        output['format_selection']=client.public()
        builder=BoardContextBuilder(prompt)
        stage='public_model_cases'
        for generation,case in enumerate(CASES,1):
            owner=Owner(request_id=uuid.uuid4().hex,board_boot_id=boot,session_id=session,generation=generation)
            record=dict(**case,actual_tool_result_supplied=False,tools_executed=[],
                        status='started',review_status='pending_root_review')
            output['cases'].append(record)
            persist(args.output,output)
            begin=time.monotonic()
            case_stage='build_context'
            try:
                messages=builder({'messages':[],'facts':[],'summaries':[]},case['text'])
                case_stage='validate_request'
                payload=validate_request('llm',dict(protocol_version=1,**owner.as_dict(),
                    budget_ms=60000,task='dialogue',messages=messages))
                record['model_input_sha256']=hashlib.sha256(json.dumps(messages,ensure_ascii=False).encode()).hexdigest()
                case_stage='inference_rpc'
                response=client.request('llm',payload,deadline=begin+60,cancelled=lambda:False)
                case_stage='validate_response'
                validate_response(response,owner,'llm')
                if response['ok'] is not True:
                    record['inference_error_code']=response['error']['code']
                    raise RuntimeError('Public grounding inference did not complete')
                case_stage='validate_reply'
                reply=validate_model_reply(response['result']['text'],case['text'])
                record.update(status='completed',public_reply=reply.text)
            except Exception as exc:
                failed=True
                record.update(status='failed',failure_class=type(exc).__name__,failure_code=safe_code(exc),failure_stage=case_stage)
            finally:
                record['elapsed_ms']=(time.monotonic()-begin)*1000
                persist(args.output,output)  # Preserve inference evidence before cancel.
                cleanup_stage='cancel_rpc'
                try:
                    cleanup=client.cancel(owner)
                    cleanup_stage='validate_cancel_response'
                    if cleanup is None:
                        record['cleanup_error_code']='null_response'
                    validate_response(cleanup,owner,'cancel')
                    if cleanup['ok'] is not True:
                        record['cleanup_error_code']=cleanup['error']['code']
                        raise RuntimeError('Owned request cleanup was not confirmed')
                    if cleanup['result']['state'] not in ('completed','cancelled','unknown'):
                        raise ValueError('Unexpected owned request cleanup state')
                    record['owner_cleanup']='completed'
                    record['owner_cleanup_state']=cleanup['result']['state']
                except Exception as cancel_exc:
                    failed=True
                    record['owner_cleanup']='failed'
                    record['cleanup_failure_class']=type(cancel_exc).__name__
                    record['cleanup_failure_code']=safe_code(cancel_exc)
                    record['cleanup_failure_stage']=cleanup_stage
                persist(args.output,output)
            if failed:
                break
    except Exception as exc:
        failed=True
        output['failure']=dict(stage=stage,error_class=type(exc).__name__,code=safe_code(exc))
    output['status']='PUBLIC_PROBE_PARTIAL_OR_FAILED' if failed else 'PUBLIC_REPLIES_REQUIRE_ROOT_REVIEW'
    persist(args.output,output)
    print(json.dumps(output,ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__=='__main__':
    main()
