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
PREVIOUS = REPAIR / 'release_v18_newboot_candidate'
BASE_SPEC_SHA = '07e7d0762c79ad76832fba5f33be25f0822b53963a1512e5f1eb26c2d8483e5b'
BASE_MAPPING_SHA = '7daeff19d784ba69d31bd9911ebd461a5b987e5a51f7da76d0a74f0bcab8a3a8'
BASE_STARTUP_SHA = '70a2f7fa5440f2b65004d66d5c4984b664ccc2b60131a0abd9a8351591c8d4e6'
BASE_MANIFEST_SHA = 'e105159fea9a71a347b6564ef77d1db23f6596199ed27a5e8684d6b025b5bacb'
BASE_CONFIG_SHA = '5518b6705083eb9e2fae7e19a47c003182995fe8660cbc6031860c9905da9786'
PUBLISHER_SHA = 'af19ae0b99cde0307a58bae5c543ec8c67e9bda782e6294abae8dd492c228683'
MINOR_REVISION = 'response-latency-v18-ui-worker-followup'
ALLOWED_PATHS = {'tools/board_avatar_gtk.py','tools/production_business_ui.py','tools/board_avatar_worker.py'}
# Exact author manifests and source bytes reviewed before this closure was sealed.
APPROVED_PAYLOAD_SHA = '06fa0931fff7a6d0696c8357af44af1f69d1aece3d2114c71473daa0031b3917'


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
    path=PREVIOUS/'publish_newboot.py'
    pinned(path,PUBLISHER_SHA)
    spec=importlib.util.spec_from_file_location('_pinned_newboot_publisher_for_minor',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def baseline():
    spec=json.loads(pinned(PREVIOUS/'newboot_evidence/spec.json',BASE_SPEC_SHA))
    mapping=json.loads(pinned(PREVIOUS/'newboot_evidence/source_mapping.json',BASE_MAPPING_SHA))
    if (spec['startup_sha256']!=BASE_STARTUP_SHA or spec['source_manifest_sha256']!=BASE_MANIFEST_SHA
            or spec['configuration_sha256']!=BASE_CONFIG_SHA or spec['component_pins']!=379
            or mapping['component_pins']!=spec['component_sha256'] or len(spec['component_sha256'])!=379):
        raise ValueError('current_sealed_379_baseline_required')
    spec.update(minor_state='BASELINE',minor_revision=MINOR_REVISION,minor_overrides={})
    return spec


def approved_sources():
    if APPROVED_PAYLOAD_SHA is None:
        raise ValueError('minor_payload_not_frozen')
    value=json.loads(pinned(HERE/'APPROVED_PAYLOAD.json',APPROVED_PAYLOAD_SHA))
    if value.get('baseline_startup_sha256')!=BASE_STARTUP_SHA or value.get('minor_revision')!=MINOR_REVISION:
        raise ValueError('approved_minor_baseline_changed')
    sources=value.get('sources',{})
    if not isinstance(sources,dict) or not sources or not set(sources)<=ALLOWED_PATHS:
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
