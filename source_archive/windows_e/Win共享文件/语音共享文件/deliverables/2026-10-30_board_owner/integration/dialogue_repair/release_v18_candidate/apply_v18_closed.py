"""Fixed five-source v17 -> v18. Default dry; no optional AB/D01/config changes."""
import argparse
import ast
import base64
import json
from pathlib import Path
import time
from v18_common import (HERE, REPAIR, PROJECT, INTEGRATION, APPLY_SHA, CORE, MAPPING_SHA,
    V17_STARTUP, V17_MANIFEST, CONFIG_SHA, NATIVE_SHA, PAIR_SHA, STAGE,
    pinned, sha, remote_from, replace_once, frozen_v17_spec, create_json, ssh_json)


def local_bundle():
    mapping = json.loads(pinned(REPAIR / 'release_v17_candidate/v17_evidence/source_mapping.json', MAPPING_SHA))
    assert mapping['startup_sha256'] == V17_STARTUP and mapping['source_manifest_sha256'] == V17_MANIFEST
    assert mapping['configuration_sha256'] == CONFIG_SHA and len(mapping['component_pins']) == 379
    sources, payload = {}, {}
    for rel, (source, before, after) in CORE.items():
        assert mapping['component_pins'][rel] == before
        path = REPAIR / source
        assert path.resolve(strict=True).is_relative_to(PROJECT.resolve(strict=True))
        raw = pinned(path, after)
        assert 0 < len(raw) < 2 * 1024 * 1024
        ast.parse(raw, feature_version=(3, 9))
        sources[rel] = dict(source=path.relative_to(PROJECT).as_posix(), before_sha256=before, sha256=after, bytes=len(raw))
        payload[rel] = dict(before_sha256=before, sha256=after, base64=base64.b64encode(raw).decode('ascii'))
    revision = dict(stage=STAGE, before_startup_sha256=V17_STARTUP, before_manifest_sha256=V17_MANIFEST,
        sources=sources, business_options={}, native_library_sha256=NATIVE_SHA,
        character_pair_selection_sha256=PAIR_SHA, private_data_replayed=False)
    return revision, payload


PREFLIGHT = r'''
assert SPEC['startup_sha256']==V17_STARTUP and SPEC['configuration_sha256']==CONFIG_SHA and SPEC['component_pins']==379
assert SPEC['source_manifest_sha256']==V17_MANIFEST
assert REVISION['stage']==V18_STAGE and REVISION['before_startup_sha256']==V17_STARTUP
assert REVISION['before_manifest_sha256']==V17_MANIFEST and REVISION['business_options']=={} and not gui_options
assert 'wake_word_required' not in REVISION and 'conversation_mode' not in REVISION
assert REVISION['character_pair_selection_sha256']==PAIR_SHA and REVISION['native_library_sha256']==NATIVE_SHA
assert sha(old_cfg)==CONFIG_SHA
assert cfg['board_business']['asr_variant']=='paraformer_small' and cfg['board_business']['asr_threads']==3
assert cfg['board_business']['asr_directory']=='/home/root/aura-board-asr-models/paraformer-small-63ddc3cd0f2810b6'
assert cfg['board_business']['frontend_optimization']=='combined' and cfg['board_business']['frontend_threads']==1
assert cfg['board_business']['capture_priority_nice']==-10
assert cfg['character_pair']['selection_sha256']==PAIR_SHA
assert startup['component_sha256']['tools/libaura_yuki.so']==NATIVE_SHA
assert startup['component_sha256']['config/yuki_pair.formal.json']==PAIR_SHA
pair=json.loads(read(root/'runtime/aura/config/yuki_pair.formal.json',PAIR_SHA));assert pair['native_config']['fps']==16
assert set(PAYLOAD)==set(EXPECTED_PAYLOAD) and len(PAYLOAD)==5
for rel,item in PAYLOAD.items():
 assert rel.endswith('.py') and (item['sha256'],item['before_sha256'])==tuple(EXPECTED_PAYLOAD[rel])
 assert startup['component_sha256'][rel]==item['before_sha256']
 raw=base64.b64decode(item['base64'],validate=True);assert sha(raw)==item['sha256'] and 0<len(raw)<2*1024*1024
 ast.parse(raw,feature_version=(3,9))
'''


def build_remote():
    original = remote_from('listening_entry_fix/apply_closed_revision.py', APPLY_SHA)
    constants = dict(V17_STARTUP=V17_STARTUP, V17_MANIFEST=V17_MANIFEST, CONFIG_SHA=CONFIG_SHA,
        NATIVE_SHA=NATIVE_SHA, PAIR_SHA=PAIR_SHA, V18_STAGE=STAGE,
        EXPECTED_PAYLOAD={rel: [row[2], row[1]] for rel, row in CORE.items()})
    remote = '\n'.join(k + '=' + repr(v) for k, v in constants.items()) + '\n' + original
    anchor = " assert cfg['board_business']['data_origin']=='board' and cfg['board_business']['retention_enabled'] is True\n"
    remote = replace_once(remote, anchor, anchor + '\n'.join(' ' + line if line else '' for line in PREFLIGHT.strip().splitlines()) + '\n')
    old = "  cfg['board_business'].update(REVISION['business_options']);cfg.update(gui_options);cfgraw=encoded(cfg);cfgpin=sha(cfgraw)"
    remote = replace_once(remote, old, "  assert REVISION['business_options']=={} and not gui_options\n  cfgraw=old_cfg;cfgpin=sha(cfgraw);assert cfgpin==CONFIG_SHA")
    anchor = "  create(stage/'completed.json',encoded(result));print(json.dumps(result))"
    remote = replace_once(remote, anchor,
        "  result.update(native_library_sha256=NATIVE_SHA,character_pair_selection_sha256=PAIR_SHA)\n"
        "  assert len(startup['component_sha256'])==379 and cfgpin==CONFIG_SHA\n"
        "  for rel,pin in startup['component_sha256'].items():read(root/'runtime/aura'/rel,pin)\n" + anchor)
    ast.parse(remote, feature_version=(3, 9))
    return remote


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec', type=Path, default=REPAIR / 'release_v17_candidate/v17_spec.json')
    p.add_argument('--execute-root-only', action='store_true')
    args = p.parse_args()
    spec = frozen_v17_spec(args.spec)
    revision, payload = local_bundle()
    remote = build_remote()
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_VALIDATED_NO_SSH', stage=STAGE, payload_files=5,
            configuration_unchanged=True, optional_contract_or_D01_included=False,
            sources={rel: row['sha256'] for rel, row in payload.items()}, remote_sha256=sha(remote.encode()))))
        return
    assert not (HERE / 'v18_spec.json').exists(), 'Do not overwrite an existing v18 spec'
    prefix = '\n'.join(k + '=' + repr(v) for k, v in dict(SPEC=spec, REVISION=revision, PAYLOAD=payload).items()) + '\n'
    result = ssh_json(prefix + remote, timeout=90)
    create_json(HERE / ('actual_apply_v18_' + str(time.time_ns()) + '.json'), result)
    assert result['status'] == 'LISTENING_REVISION_INSTALLED_UI_STOPPED' and result['stage'] == STAGE
    assert result['component_pins'] == 379 and result['configuration_sha256'] == CONFIG_SHA
    assert result['source_files'] == {rel: row['sha256'] for rel, row in payload.items()} and result['business_options'] == {}
    assert result['native_library_sha256'] == NATIVE_SHA and result['character_pair_selection_sha256'] == PAIR_SHA
    next_spec = dict(spec)
    next_spec.update(release_stage=STAGE, previous_startup_sha256=V17_STARTUP, expected_final_listening_enabled=True,
        release_sources={rel: row['sha256'] for rel, row in payload.items()})
    for key in ['startup_sha256', 'source_manifest_sha256', 'component_pins', 'configuration_sha256']:
        next_spec[key] = result[key]
    create_json(HERE / 'v18_spec.json', next_spec)
    print(json.dumps(dict(result=result, next_spec=str(HERE / 'v18_spec.json'), original_v17_spec_changed=False)))


if __name__ == '__main__': main()
