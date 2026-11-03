"""Prepare or root-execute the exact 13-file v16 -> v17 closed revision.

Default validates local source bytes only. Original publisher/spec are never
edited. Execution preserves original normal-close, publisher/writer locks,
bootstrap/private-root checks, complete before pins and fsync/backup sequence.
"""
import argparse
import ast
import base64
import json
from pathlib import Path
import time
from release_common import (HERE, INTEGRATION, PROJECT, APPLY_SHA, V16_STARTUP,
    V16_MANIFEST, V16_CONFIG, OLD_NATIVE, NEW_NATIVE, OLD_PAIR, NEW_PAIR, STAGE,
    create_json, encoded, frozen_v16_spec, pinned, remote_from, replace_once, sha, ssh_json)

REPAIR = HERE.parent
FEATURE = REPAIR / 'feature_trigger_collaboration/candidate_v3'
ANIM = REPAIR / 'animation_thinking_collaboration'
FEATURE_SHA = '395eda57127551cd788c112ef1a8001f8d75c40d46b400d4a9a2af417702bb7e'
ANIM_SHA = 'ac34e8c51b988d69110e1c82d9fc1c11ec8c6ab39cd08a5deae95a2260b52dea'
PAIR_RECEIPT_SHA = '04ea05e54da8a83837ea6072ae540c5078373fa2901570e246f475507d2cc838'
BUILD_RECEIPT_SHA = '85579d297cc61b1f52a241267c415500bd4fb4493689ca1dd6dd5f4f22d7cd79'
MAPPING_SHA = 'c56a5920d55ca99cbe46680a6d5fffd3174e00bb09c7dae52084ce7de0f5640b'
NON_PY = {'tools/libaura_yuki.so': NEW_NATIVE, 'config/yuki_pair.formal.json': NEW_PAIR}


def artifacts():
    paths = {
        'feature': (FEATURE/'SOURCE_MANIFEST.json', FEATURE_SHA),
        'animation': (ANIM/'SOURCE_MANIFEST.json', ANIM_SHA),
        'pair': (ANIM/'paired_overlay/PAIRING_RECEIPT.json', PAIR_RECEIPT_SHA),
        'build': (ANIM/'native_build_result/native_build_receipt.json', BUILD_RECEIPT_SHA),
    }
    return {key:dict(sha256=digest, base64=base64.b64encode(pinned(path,digest)).decode())
            for key,(path,digest) in paths.items()}


def local_bundle():
    audit=artifacts()
    read=lambda key:json.loads(base64.b64decode(audit[key]['base64'],validate=True))
    feature,animation,pair,build=(read(key) for key in ('feature','animation','pair','build'))
    mapping=json.loads(pinned(REPAIR/'paraformer_small_validation/v16_evidence/source_mapping.json',MAPPING_SHA))
    assert feature['source_baseline_startup_sha256']==mapping['startup_sha256']==V16_STARTUP
    assert feature['source_baseline_manifest_sha256']==mapping['source_manifest_sha256']==V16_MANIFEST
    assert animation['base_startup_sha256']==V16_STARTUP and animation['base_source_manifest_sha256']==V16_MANIFEST
    assert len(feature['files'])==8 and len(pair['files'])==5 and not set(feature['files'])&set(pair['files'])
    assert pair['native_build_receipt_sha256']==BUILD_RECEIPT_SHA
    assert pair['selection_sha256']==NEW_PAIR and pair['base_selection_sha256']==OLD_PAIR
    assert build['status']=='ISOLATED_COMPILED_CPU_POLICY_PASSED_NOT_INSTALLED'
    assert build['source_sha256']==animation['files']['native/yuki_host.cpp']['after_sha256']
    assert build['header_sha256']==animation['files']['native/yuki_host.h']['after_sha256']
    assert build['shared_dependencies_identical'] is True and build['native_policy_test']['status']=='PASS'
    assert build['production_installed'] is False and build['library_sha256']==NEW_NATIVE
    sources,payload={},{}
    for rel,row in feature['files'].items():
        sources[rel]=dict(path=Path(row['source']),sha256=row['sha256'],before_sha256=row['before_sha256'])
    for rel,digest in pair['files'].items():
        sources[rel]=dict(path=ANIM/'paired_overlay/aura'/rel,sha256=digest,
                          before_sha256=mapping['component_pins'][rel])
    for rel,item in sources.items():
        assert rel.endswith('.py') or NON_PY.get(rel)==item['sha256']
        assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
        path=item.pop('path').resolve(strict=True)
        assert path.is_relative_to(PROJECT.resolve())
        raw=pinned(path,item['sha256'])
        assert 0<len(raw)<2*1024*1024
        if rel.endswith('.py'):ast.parse(raw,feature_version=(3,9))
        before=mapping['component_pins'].get(rel)
        assert before==item['before_sha256']
        if before is None:assert rel=='common/feature_intents.py'
        item.update(source=path.relative_to(PROJECT).as_posix(),bytes=len(raw))
        payload[rel]=dict(sha256=item['sha256'],before_sha256=before,base64=base64.b64encode(raw).decode())
    assert len(payload)==13 and [r for r,v in payload.items() if v['before_sha256'] is None]==['common/feature_intents.py']
    old_pair=json.loads(pinned(ANIM/'before/aura/config/yuki_pair.formal.json',OLD_PAIR))
    new_pair=json.loads(base64.b64decode(payload['config/yuki_pair.formal.json']['base64']))
    validate_pair(old_pair,new_pair,payload)
    revision=dict(stage=STAGE,before_startup_sha256=V16_STARTUP,before_manifest_sha256=V16_MANIFEST,
                  sources=sources,business_options={},character_pair_selection_sha256=NEW_PAIR,
                  native_library_sha256=NEW_NATIVE,private_data_replayed=False)
    return revision,payload,audit


def validate_pair(old_pair,new_pair,payload):
    expected=json.loads(json.dumps(old_pair))
    expected['runtime_pins']['tools/native_yuki.py']=payload['tools/native_yuki.py']['sha256']
    expected['runtime_pins']['tools/libaura_yuki.so']=NEW_NATIVE
    assert new_pair==expected, 'Only native adapter/library pair pins may change'
    assert new_pair['native_config']['fps']==16
    assert new_pair['identity']==old_pair['identity'] and new_pair['presentation']==old_pair['presentation']
    native=base64.b64decode(payload['tools/libaura_yuki.so']['base64'],validate=True)
    assert native[:6]==b'\x7fELF\x02\x01' and int.from_bytes(native[18:20],'little')==183
    formal=ast.parse(base64.b64decode(payload['tools/formal_yuki.py']['base64'],validate=True))
    pins=[ast.literal_eval(n.value) for n in formal.body if isinstance(n,ast.Assign)
          and any(isinstance(t,ast.Name) and t.id=='PAIR_CONFIG_SHA256' for t in n.targets)]
    assert pins==[NEW_PAIR]


PREFLIGHT = r'''
assert SPEC['startup_sha256']==V16_STARTUP and SPEC['configuration_sha256']==V16_CONFIG and SPEC['component_pins']==378
assert REVISION['stage']==V17_STAGE and REVISION['business_options']=={} and not gui_options
assert 'wake_word_required' not in REVISION and 'conversation_mode' not in REVISION
assert REVISION['character_pair_selection_sha256']==NEW_PAIR and REVISION['native_library_sha256']==NEW_NATIVE
assert cfg['board_business']['asr_variant']=='paraformer_small' and cfg['board_business']['asr_threads']==3
assert cfg['board_business']['asr_directory']=='/home/root/aura-board-asr-models/paraformer-small-63ddc3cd0f2810b6'
assert cfg['character_pair']['selection_sha256']==OLD_PAIR
assert set(PAYLOAD)==set(EXPECTED_PAYLOAD) and len(PAYLOAD)==13
decoded={}
for rel,item in PAYLOAD.items():
 assert (item['sha256'],item['before_sha256'])==tuple(EXPECTED_PAYLOAD[rel])
 raw=base64.b64decode(item['base64'],validate=True);assert sha(raw)==item['sha256'] and 0<len(raw)<2*1024*1024
 if rel.endswith('.py'):ast.parse(raw,feature_version=(3,9))
 else:assert NON_PY.get(rel)==item['sha256']
 if item['before_sha256'] is None:assert rel=='common/feature_intents.py'
 decoded[rel]=raw
assert set(ARTIFACTS)==set(EXPECTED_ARTIFACTS)
evidence={}
for key,pin in EXPECTED_ARTIFACTS.items():
 raw=base64.b64decode(ARTIFACTS[key]['base64'],validate=True)
 assert sha(raw)==pin==ARTIFACTS[key]['sha256'];evidence[key]=json.loads(raw)
feature,animation,pair,build=[evidence[k] for k in ('feature','animation','pair','build')]
assert feature['source_baseline_startup_sha256']==V16_STARTUP and feature['source_baseline_manifest_sha256']==V16_MANIFEST
assert animation['base_startup_sha256']==V16_STARTUP and animation['base_source_manifest_sha256']==V16_MANIFEST
assert set(feature['files'])|set(pair['files'])==set(PAYLOAD) and not set(feature['files'])&set(pair['files'])
for rel,row in feature['files'].items():assert (row['sha256'],row['before_sha256'])==tuple(EXPECTED_PAYLOAD[rel])
for rel,pin in pair['files'].items():assert pin==EXPECTED_PAYLOAD[rel][0]
assert pair['selection_sha256']==NEW_PAIR and pair['base_selection_sha256']==OLD_PAIR
assert pair['native_build_receipt_sha256']==EXPECTED_ARTIFACTS['build']
assert build['status']=='ISOLATED_COMPILED_CPU_POLICY_PASSED_NOT_INSTALLED'
assert build['source_sha256']==animation['files']['native/yuki_host.cpp']['after_sha256']
assert build['header_sha256']==animation['files']['native/yuki_host.h']['after_sha256']
assert build['shared_dependencies_identical'] is True and build['native_policy_test']['status']=='PASS'
assert build['production_installed'] is False and build['library_sha256']==NEW_NATIVE
old_pair=json.loads(read(root/'runtime/aura/config/yuki_pair.formal.json',OLD_PAIR))
new_pair=json.loads(decoded['config/yuki_pair.formal.json'])
expected_pair=json.loads(json.dumps(old_pair))
expected_pair['runtime_pins']['tools/native_yuki.py']=EXPECTED_PAYLOAD['tools/native_yuki.py'][0]
expected_pair['runtime_pins']['tools/libaura_yuki.so']=NEW_NATIVE
assert new_pair==expected_pair and new_pair['native_config']['fps']==16
assert new_pair['identity']==old_pair['identity'] and new_pair['presentation']==old_pair['presentation']
native=decoded['tools/libaura_yuki.so'];assert native[:6]==b'\x7fELF\x02\x01' and int.from_bytes(native[18:20],'little')==183
formal=ast.parse(decoded['tools/formal_yuki.py'])
formal_pair_pins=[ast.literal_eval(n.value) for n in formal.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PAIR_CONFIG_SHA256' for t in n.targets)]
assert formal_pair_pins==[NEW_PAIR]
'''


def build_remote(revision,payload,audit):
    original=remote_from('listening_entry_fix/apply_closed_revision.py',APPLY_SHA)
    constants=dict(V16_STARTUP=V16_STARTUP,V16_CONFIG=V16_CONFIG,V16_MANIFEST=V16_MANIFEST,
                   V17_STAGE=STAGE,OLD_PAIR=OLD_PAIR,NEW_PAIR=NEW_PAIR,NEW_NATIVE=NEW_NATIVE,
                   NON_PY=NON_PY,EXPECTED_PAYLOAD={r:[v['sha256'],v['before_sha256']] for r,v in payload.items()},
                   EXPECTED_ARTIFACTS={k:v['sha256'] for k,v in audit.items()})
    remote='\n'.join(k+'='+repr(v) for k,v in constants.items())+'\n'+original
    anchor=" assert cfg['board_business']['data_origin']=='board' and cfg['board_business']['retention_enabled'] is True\n"
    remote=replace_once(remote,anchor,anchor+'\n'.join(' '+line if line else '' for line in PREFLIGHT.strip().splitlines())+'\n')
    old="   assert not Path(rel).is_absolute() and '..' not in Path(rel).parts and rel.endswith('.py')\n   raw=base64.b64decode(item['base64']);assert sha(raw)==item['sha256'];ast.parse(raw,feature_version=(3,9))"
    new="   assert not Path(rel).is_absolute() and '..' not in Path(rel).parts and (rel.endswith('.py') or NON_PY.get(rel)==item['sha256'])\n   raw=decoded[rel];assert sha(raw)==item['sha256']\n   if rel.endswith('.py'):ast.parse(raw,feature_version=(3,9))\n   else:assert NON_PY.get(rel)==item['sha256']"
    remote=replace_once(remote,old,new)
    old="  cfg['board_business'].update(REVISION['business_options']);cfg.update(gui_options);cfgraw=encoded(cfg);cfgpin=sha(cfgraw)"
    new="  expected_cfg=json.loads(old_cfg);expected_cfg['character_pair']['selection_sha256']=NEW_PAIR\n  cfg['character_pair']['selection_sha256']=NEW_PAIR\n  assert cfg==expected_cfg\n  cfgraw=encoded(cfg);cfgpin=sha(cfgraw)"
    remote=replace_once(remote,old,new)
    anchor="  create(stage/'completed.json',encoded(result));print(json.dumps(result))"
    new="  result.update(native_library_sha256=NEW_NATIVE,character_pair_selection_sha256=NEW_PAIR)\n  assert len(startup['component_sha256'])==379\n  for rel,pin in startup['component_sha256'].items():read(root/'runtime/aura'/rel,pin)\n"+anchor
    remote=replace_once(remote,anchor,new)
    ast.parse(remote,feature_version=(3,9))
    return remote


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',type=Path,default=INTEGRATION/'production_business_acceptance/spec.json')
    parser.add_argument('--execute-root-only',action='store_true')
    args=parser.parse_args()
    spec=frozen_v16_spec(args.spec)
    revision,payload,audit=local_bundle();remote=build_remote(revision,payload,audit)
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_VALIDATED_NO_SSH',stage=STAGE,payload_files=len(payload),
            new_files=[r for r,v in payload.items() if v['before_sha256'] is None],business_options={},
            gui_change='character_pair.selection_sha256',remote_sha256=sha(remote.encode()),
            native_library_sha256=NEW_NATIVE,character_pair_selection_sha256=NEW_PAIR)))
        return
    assert not (HERE/'v17_spec.json').exists(), 'Do not overwrite an existing v17 release spec'
    prefix='\n'.join(k+'='+repr(v) for k,v in dict(SPEC=spec,REVISION=revision,PAYLOAD=payload,ARTIFACTS=audit).items())+'\n'
    result=ssh_json(prefix+remote,timeout=90)
    create_json(HERE/('actual_apply_v17_'+str(time.time_ns())+'.json'),result)
    assert result['status']=='LISTENING_REVISION_INSTALLED_UI_STOPPED'
    assert result['stage']==STAGE and result['component_pins']==379 and result['business_options']=={}
    assert result['source_files']=={r:v['sha256'] for r,v in payload.items()}
    assert result['native_library_sha256']==NEW_NATIVE and result['character_pair_selection_sha256']==NEW_PAIR
    next_spec=dict(spec)
    for key in ('startup_sha256','component_pins','configuration_sha256','source_manifest_sha256',
                'native_library_sha256','character_pair_selection_sha256'):
        next_spec[key]=result[key]
    next_spec['release_stage']=STAGE
    create_json(HERE/'v17_spec.json',next_spec)
    print(json.dumps(dict(result=result,next_spec=str(HERE/'v17_spec.json'),original_spec_changed=False)))


if __name__=='__main__':main()
