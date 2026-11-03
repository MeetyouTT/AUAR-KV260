"""Independent start/ready wrapper with the exact new native SHA still gated."""
import argparse
import ast
import json
from pathlib import Path
import time
from release_common import (HERE, PUBLISH_SHA, NEW_NATIVE, NEW_PAIR, STAGE, OLD_NATIVE,
    create_json, publisher_script, remote_from, replace_once, sha, ssh_json)


def build_remote():
    remote=remote_from('production_business_acceptance/publish_business_ui.py',PUBLISH_SHA)
    old=" need(cfg['component_sha256']['tools/libaura_yuki.so']=='"+OLD_NATIVE+"','waist_native_changed')"
    new=(" need(SPEC.get('native_library_sha256')=='"+NEW_NATIVE+"','reviewed_thinking_native_required')\n"
         " need(cfg['component_sha256']['tools/libaura_yuki.so']==SPEC['native_library_sha256'],'reviewed_native_changed')")
    remote=replace_once(remote,old,new)
    remote="assert ACTION in ('start','ready')\n"+remote
    ast.parse(remote,feature_version=(3,9))
    return remote


def validate_spec(spec):
    if (spec.get('release_stage')!=STAGE or spec.get('component_pins')!=379
            or spec.get('native_library_sha256')!=NEW_NATIVE
            or spec.get('character_pair_selection_sha256')!=NEW_PAIR
            or spec.get('automatic_listening') is not True
            or spec.get('wake_word_required') is not False
            or spec.get('conversation_mode')!='half_duplex'
            or spec.get('retention_enabled') is not True):
        raise ValueError('Exact merged v17 spec required')
    return spec


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('start','ready'))
    parser.add_argument('--spec',type=Path,default=HERE/'v17_spec.json')
    parser.add_argument('--execute-root-only',action='store_true')
    args=parser.parse_args()
    remote=build_remote()
    if not args.execute_root_only:
        if args.spec.exists():validate_spec(json.loads(args.spec.read_bytes()))
        print(json.dumps(dict(status='DRY_SOURCE_VALIDATED_NO_SSH',action=args.action,
            remote_sha256=sha(remote.encode()),native_library_sha256=NEW_NATIVE,
            complete_spec_exists=args.spec.exists())))
        return
    spec=validate_spec(json.loads(args.spec.read_bytes()))
    result=ssh_json(publisher_script(remote,dict(SPEC=spec,ACTION=args.action,TOKEN=None,WINDOW=None)),timeout=225)
    path=HERE/('actual_v17_'+args.action+'_'+str(time.time_ns())+'.json')
    create_json(path,result)
    print(json.dumps(dict(output=str(path),result=result),ensure_ascii=True))


if __name__=='__main__':main()
