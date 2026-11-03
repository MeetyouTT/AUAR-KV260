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
PREVIOUS = REPAIR / 'release_v18_minor_ui_candidate'
BASE_SPEC_SHA = 'c46d44e8583a8ccb8e02d9321b5c6edb9a681474913ba2689dd681d912c50cb2'
BASE_MAPPING_SHA = 'df6b26927ad60d6d3513429c697d70bd15c84cfdca6d16c5527e9992cb7b04e2'
BASE_STARTUP_SHA = '90f6c6c40f6501362aa77483235a7260a212de6e3357615311bdaa5cc193ebbe'
BASE_MANIFEST_SHA = '6d03c1d7aa95a9c5615f540606699f67c4ee7a44be1e50dcb2983c6c555e3637'
BASE_CONFIG_SHA = '5518b6705083eb9e2fae7e19a47c003182995fe8660cbc6031860c9905da9786'
PUBLISHER_SHA = 'af19ae0b99cde0307a58bae5c543ec8c67e9bda782e6294abae8dd492c228683'
MINOR_REVISION = 'response-stability-v19-social-off-audio-drain'
ALLOWED_PATHS = {'tools/board_avatar_gtk.py','tools/board_recording.py'}
# Exact author manifests and source bytes reviewed before this closure was sealed.
APPROVED_PAYLOAD_SHA = 'cc782df3d1680ad4963c9c41d94498e0828ec38a03138a4889c534002e861819'
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
    spec=json.loads(pinned(PREVIOUS/'minor_evidence/spec.json',BASE_SPEC_SHA))
    mapping=json.loads(pinned(PREVIOUS/'minor_evidence/source_mapping.json',BASE_MAPPING_SHA))
    if (spec['startup_sha256']!=BASE_STARTUP_SHA or spec['source_manifest_sha256']!=BASE_MANIFEST_SHA
            or spec['configuration_sha256']!=BASE_CONFIG_SHA or spec['component_pins']!=379
            or mapping['component_pins']!=spec['component_sha256'] or len(spec['component_sha256'])!=379):
        raise ValueError('current_sealed_379_baseline_required')
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
        if set(row)!={'before_sha256','sha256','local_source'} or row['before_sha256']!=pins[rel]:
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
    startup=previous_publisher().inputs()[1]
    startup['component_sha256']=spec['component_sha256']
    spec['startup_sha256']=sha(encoded(startup));spec['source_manifest_sha256']='0'*64
    return spec


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
    sys.path.insert(0,str(REPAIR/'release_v18_candidate'))
    from v18_common import publisher_script,ssh_json
    return ssh_json(publisher_script(remote,values),timeout=timeout)
