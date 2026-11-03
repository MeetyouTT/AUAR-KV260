"""Exact v17/v18 normal-close and v18 start/ready. Default dry; root-only execute."""
import argparse
import ast
import json
from pathlib import Path
import time
from v18_common import (HERE, REPAIR, INTEGRATION, CORE, PUBLISH_SHA, NATIVE_SHA, PAIR_SHA,
    STAGE, V17_STAGE, CONFIG_SHA, create_json, pinned, publisher_script,
    remote_from, replace_once, sha, ssh_json, validate_spec)


def build_remote():
    remote = remote_from('production_business_acceptance/publish_business_ui.py', PUBLISH_SHA)
    guard_path = REPAIR / 'release_v17_candidate/guard_v16_paused.py'
    # Only the original, reviewed, literal never-armed predicate is reused.
    raw = pinned(guard_path, '29586c07dff505734d6bdd6cf2613800233f325381fdbc56a0bcf2d133b338e4')
    tree = ast.parse(raw)
    helpers = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'QUIET_HELPER' for t in n.targets)]
    assert len(helpers) == 1
    old = "quiet_capture=(d.get('capture',{}).get('speech_active') is False or\n     h.get('microphone_open') is False and d.get('capture_state') in ('IDLE','CANCELLED','CLOSED','ERROR'))"
    remote = replace_once(remote, old, old[:-1] + ' or\n     never_armed_paused_capture(v))')
    remote = replace_once(remote, '\ndef state():', helpers[0] + '\ndef state():')
    old = " need(cfg['component_sha256']['tools/libaura_yuki.so']=='887546c09eb1897845c8d7f55a9e3f9b9c761448c7410f2b599259ae0b51efd2','waist_native_changed')"
    new = (" need(SPEC.get('native_library_sha256')==NATIVE_SHA,'reviewed_v17_v18_native_required')\n"
        " need(cfg['component_sha256']['tools/libaura_yuki.so']==NATIVE_SHA,'reviewed_native_changed')\n"
        " need(cfg['component_sha256']['config/yuki_pair.formal.json']==PAIR_SHA,'reviewed_pair_changed')\n"
        " c.read(root/'production_source_manifest.json',SPEC['source_manifest_sha256'])\n"
        " need(cfg['component_sha256']['config/board_avatar_gtk.json']==CONFIG_SHA,'gui_configuration_changed')\n"
        " gui=c.parse(c.read(root/'runtime/aura/config/board_avatar_gtk.json',CONFIG_SHA))\n"
        " need(gui['board_business']['asr_variant']=='paraformer_small' and gui['board_business']['asr_threads']==3,'reviewed_small_asr_required')\n"
        " pair=c.parse(c.read(root/'runtime/aura/config/yuki_pair.formal.json',PAIR_SHA))\n"
        " need(pair['native_config']['fps']==16,'reviewed_render_target_changed')\n"
        " selected=CORE_AFTER if SPEC['release_stage']==V18_STAGE else CORE_BEFORE\n"
        " for rel,pin in selected.items():need(cfg['component_sha256'][rel]==pin,'reviewed_release_source_changed')")
    remote = replace_once(remote, old, new)
    remote = replace_once(remote, 'def window():\n j=journal();', 'def window():\n boot();source()\n j=journal();')
    constants = dict(NATIVE_SHA=NATIVE_SHA, PAIR_SHA=PAIR_SHA, CONFIG_SHA=CONFIG_SHA,
        V18_STAGE=STAGE, CORE_BEFORE={k: row[1] for k, row in CORE.items()}, CORE_AFTER={k: row[2] for k, row in CORE.items()})
    remote = "assert ACTION in ('guard','window-inspect','normal-close','start','ready')\n" + '\n'.join(k+'='+repr(v) for k,v in constants.items())+'\n'+remote
    ast.parse(remote, feature_version=(3, 9))
    return remote


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('guard', 'window-inspect', 'normal-close', 'start', 'ready'))
    p.add_argument('--spec', type=Path, default=HERE / 'v18_spec.json')
    p.add_argument('--window-proof', type=Path)
    p.add_argument('--execute-root-only', action='store_true')
    args = p.parse_args()
    remote = build_remote()
    spec = validate_spec(json.loads(args.spec.read_bytes()), allow_v17=args.action not in ('start', 'ready')) if args.spec.exists() else None
    if args.action == 'normal-close' and args.window_proof is None:
        p.error('--window-proof required for exact normal close')
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_SOURCE_VALIDATED_NO_SSH', action=args.action,
            complete_spec_exists=spec is not None, remote_sha256=sha(remote.encode()),
            native_library_sha256=NATIVE_SHA, character_pair_selection_sha256=PAIR_SHA)))
        return
    if spec is None: raise ValueError('Explicit completed spec required')
    values = dict(SPEC=spec, ACTION=args.action, TOKEN=None, WINDOW=None)
    if args.action == 'normal-close':
        checked = json.loads(args.window_proof.read_bytes())
        assert checked['status'] == 'WINDOW_INSPECTED_NO_CLOSE'
        values.update(TOKEN=checked['review_token'], WINDOW=checked['window']['window_id'])
    result = ssh_json(publisher_script(remote, values), timeout=225)
    path = HERE / ('actual_' + spec['release_stage'].split('-')[2] + '_' + args.action + '_' + str(time.time_ns()) + '.json')
    create_json(path, result)
    print(json.dumps(dict(output=str(path), result=result), ensure_ascii=True))


if __name__ == '__main__': main()
