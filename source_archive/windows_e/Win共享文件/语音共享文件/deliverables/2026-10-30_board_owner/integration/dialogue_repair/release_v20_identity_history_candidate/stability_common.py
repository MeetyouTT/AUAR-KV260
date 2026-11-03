"""Local pinned source preparation for one exact follow-up revision."""
import ast
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
PREVIOUS = REPAIR / 'release_v19_stability_candidate'
BASE_SPEC_SHA = '49ffbc82a4b9543d92234f055fce8af055de29764ca6f688ae0a36fe7a35a904'
BASE_MAPPING_SHA = 'ef8db220fde3b70a62ff1ff7cf2e9471a199a6d43b9234a18f8701eff58448f7'
BASE_READY_SHA = 'c0a129d24ef48f670d2f2ade4ac6fe3804566b16edd55d9dd36ef28026de0bab'
BASE_STARTUP_SHA = 'de7772b898378d2263b0809d18c095a60585a672690371d2f072b2e04c2f574f'
BASE_MANIFEST_SHA = 'e1e5947f6f054760650f36fb51726305478dbd394cb89096a0338aeb92989c41'
BASE_CONFIG_SHA = '5518b6705083eb9e2fae7e19a47c003182995fe8660cbc6031860c9905da9786'
PUBLISHER_SHA = 'af19ae0b99cde0307a58bae5c543ec8c67e9bda782e6294abae8dd492c228683'
MINOR_REVISION = 'identity-history-v20-cooperation-and-delete'
ALLOWED_PATHS = {'board/runtime/board_business.py', 'board/runtime/board_speaker_business.py',
    'tools/provisional_voice.py', 'board/runtime/history_delete.py', 'tools/production_memory_presentation.py',
    'common/board_memory.py'}
NEW_PATHS = {'board/runtime/history_delete.py'}
# Exact author manifests and source bytes reviewed before this closure was sealed.
APPROVED_PAYLOAD_SHA = 'a5292563af466470c9a501bd0b35e7314c9f15653da78fd452be724a31e6a430'
PAYLOAD_FINALIZED = True
PREFERENCE_SHA = '304af4e4aa4022797931111df47d0b4a8f5c8754a99b5076c50d95b77a684c69'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8')


def pinned(path,expected):
    path=Path(path)
    raw=path.read_bytes()
    if path.resolve()!=path or path.is_symlink() or sha(raw)!=expected:
        raise ValueError('pinned_source_changed')
    return raw


def previous_publisher():
    path=REPAIR/'release_v18_newboot_candidate/publish_newboot.py'
    pinned(path,PUBLISHER_SHA)
    spec=importlib.util.spec_from_file_location('_pinned_newboot_publisher_for_minor',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def baseline():
    if BASE_MAPPING_SHA is None or BASE_READY_SHA is None:
        raise ValueError('v19_final_evidence_binding_required')
    spec=json.loads(pinned(PREVIOUS/'stability_evidence/spec.json',BASE_SPEC_SHA))
    mapping=json.loads(pinned(PREVIOUS/'stability_evidence/source_mapping.json',BASE_MAPPING_SHA))
    ready=json.loads(pinned(PREVIOUS/'stability_evidence/ready.json',BASE_READY_SHA))
    if (spec['startup_sha256']!=BASE_STARTUP_SHA or spec['source_manifest_sha256']!=BASE_MANIFEST_SHA
            or spec['configuration_sha256']!=BASE_CONFIG_SHA or spec['component_pins']!=379
            or mapping['component_pins']!=spec['component_sha256'] or len(spec['component_sha256'])!=379):
        raise ValueError('current_sealed_379_baseline_required')
    if (mapping.get('startup_sha256')!=BASE_STARTUP_SHA or mapping.get('source_manifest_sha256')!=BASE_MANIFEST_SHA
            or mapping.get('current_publication_committed') is not True
            or ready.get('status')!='PRODUCTION_BOARD_BUSINESS_READY' or ready.get('guard_removed') is not True
            or ready.get('listening_enabled') is not False or ready.get('listening_state')!='PAUSED'
            or ready.get('physical_microphone_opened') is not False or ready.get('root')!=spec['target']):
        raise ValueError('committed_v19_ready_and_saved_pause_required')
    choice=json.loads(pinned(HERE/'FROZEN_LISTENING_PREFERENCE.json',PREFERENCE_SHA))
    if (choice.get('preference')!={'version':1,'enabled':False} or choice.get('enabled') is not False
            or choice.get('state')!='PAUSED' or choice.get('microphone_open') is not False):
        raise ValueError('saved_user_pause_evidence_required')
    spec.update(minor_state='BASELINE',minor_revision=MINOR_REVISION,minor_overrides={},expected_final_listening_enabled=False)
    return spec


def approved_sources():
    if APPROVED_PAYLOAD_SHA is None:
        raise ValueError('minor_payload_not_frozen')
    value=json.loads(pinned(HERE/'APPROVED_PAYLOAD.json',APPROVED_PAYLOAD_SHA))
    if value.get('baseline_startup_sha256')!=BASE_STARTUP_SHA or value.get('minor_revision')!=MINOR_REVISION:
        raise ValueError('approved_minor_baseline_changed')
    sources=value.get('sources',{})
    if not isinstance(sources,dict) or not sources or set(sources)!=ALLOWED_PATHS:
        raise ValueError('approved_minor_source_paths_required')
    pins=baseline()['component_sha256']
    for rel,row in sources.items():
        if (set(row)!={'before_sha256','sha256','local_source'} or row['before_sha256']!=pins.get(rel)
                or (rel not in pins)!=(rel in NEW_PATHS)):
            raise ValueError('approved_minor_source_baseline_changed')
        raw=pinned(row['local_source'],row['sha256'])
        if not 0<len(raw)<2097152:
            raise ValueError('bounded_reviewed_python_source_required')
        ast.parse(raw,feature_version=(3,9))
    return sources


def proposed():
    spec=baseline();sources=approved_sources()
    spec.update(minor_state='PROPOSED',minor_overrides=sources,
        minor_previous_startup_sha256=BASE_STARTUP_SHA,minor_previous_manifest_sha256=BASE_MANIFEST_SHA)
    for rel,row in sources.items():
        spec['component_sha256'][rel]=row['sha256']
        spec['release_sources'][rel]=row['sha256']
    spec['component_pins']=len(spec['component_sha256'])
    if spec['component_pins']!=380:
        raise ValueError('exact_380_component_proposal_required')
    startup=previous_publisher().inputs()[1]
    startup['component_sha256']=spec['component_sha256']
    spec['startup_sha256']=sha(encoded(startup));spec['source_manifest_sha256']='0'*64
    return json.loads(encoded(spec))


def validate_spec(spec,*,allow_baseline=False,allow_proposed=False):
    if type(spec.get('expected_final_listening_enabled')) is not bool:
        raise ValueError('explicit_boolean_listening_preference_required')
    state=spec.get('minor_state')
    if state=='BASELINE' and allow_baseline:
        expected=baseline()
    elif state=='PROPOSED' and allow_proposed:
        expected=proposed()
    elif state=='APPLIED':
        manifest=spec.get('source_manifest_sha256')
        if not re.fullmatch('[a-f0-9]{64}',str(manifest)) or manifest=='0'*64:
            raise ValueError('actual_minor_manifest_sha_required')
        expected=proposed();expected.update(minor_state='APPLIED',source_manifest_sha256=manifest)
    else:
        raise ValueError('minor_publication_phase_rejected')
    if spec!=expected:
        raise ValueError('only_exact_frozen_minor_sources_allowed')
    return spec


def payload_for(spec):
    return {rel:dict(row,base64=base64.b64encode(pinned(row['local_source'],row['sha256'])).decode())
        for rel,row in spec['minor_overrides'].items()}


def replace_once(source,old,new):
    if source.count(old)!=1:
        raise ValueError('unique_frozen_anchor_required')
    return source.replace(old,new)


def publisher_remote(spec):
    source=previous_publisher().build_remote(spec)
    source=replace_once(source,"assert ACTION in ('guard-failed','guard','window-inspect','normal-close','start','ready')",
        "assert ACTION in ('guard','window-inspect','normal-close','start','ready')")
    tree=ast.parse(source)
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='guard_failed')
    lines=source.splitlines(keepends=True);del lines[function.lineno-1:function.end_lineno]
    source=''.join(lines)
    source=replace_once(source," if ACTION=='guard-failed':result=guard_failed()\n elif ACTION=='guard':result=guard()",
        " if ACTION=='guard':result=guard()")
    source=replace_once(source,
        " if SPEC['release_stage']==V18_STAGE:need(enabled is True,'latest_user_listening_preference_true_required')",
        " need(type(SPEC.get('expected_final_listening_enabled')) is bool,'valid_expected_listening_preference_required')\n"
        " if SPEC['release_stage']==V18_STAGE:need(enabled is SPEC['expected_final_listening_enabled'],'latest_user_listening_preference_required')")
    path=HERE/'ownerless_port_wait.py'
    pinned(path,'c9d38b5c7a17ecea206af466c1728b5979bdff756d7e74cbfc0f3e5401283664')
    module_spec=importlib.util.spec_from_file_location('_v19_pinned_port_release_wait',path)
    module=importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source=module.patch_ownerless(source)
    ast.parse(source,feature_version=(3,9))
    return source


def write_new_json(path,value):
    raw=encoded(value)
    with Path(path).open('xb') as stream:
        stream.write(raw)
    return sha(raw)


def execute_remote(remote,values,*,timeout):
    # Only root's explicit execute branches call this lazy transport import.
    if PAYLOAD_FINALIZED is not True:
        raise ValueError('root_final_source_payload_seal_required')
    sys.path.insert(0,str(REPAIR/'release_v18_candidate'))
    from v18_common import publisher_script,ssh_json
    return ssh_json(publisher_script(remote,values),timeout=timeout)
