"""Independent-port copy of the exact old portrait service, never production.

Default --check-only performs no socket/renderer work. --execute is an explicit
benchmark action for the coordinator after reserving the test window. It keeps
the existing service/config untouched and instantiates a separate renderer.
"""
from pathlib import Path
import argparse
import hashlib
import importlib
import json
import os
import sys
import time

SOURCE_KEYS=('tools/portrait_host.py','tools/portrait_renderer.py','common/portrait_wire.py')

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aura',type=Path,required=True)
    parser.add_argument('--source-config',type=Path,required=True)
    parser.add_argument('--board-manifest',type=Path,required=True)
    parser.add_argument('--port',type=int,default=0,help='0 lets the OS select an unused port')
    parser.add_argument('--expected-revision',required=True)
    parser.add_argument('--ready-file',type=Path)
    action=parser.add_mutually_exclusive_group()
    action.add_argument('--check-only',action='store_true')
    action.add_argument('--execute',action='store_true')
    args=parser.parse_args(argv)
    aura=args.aura.resolve(strict=True)
    config=json.loads(args.source_config.read_text(encoding='utf8'))
    pins=json.loads(args.board_manifest.read_text(encoding='utf8'))['component_pins']
    hashes={key:digest(aura/key) for key in SOURCE_KEYS}
    if any(hashes[key]!=pins[key] for key in SOURCE_KEYS):raise ValueError('Old server source pin mismatch')
    if config['listen']!='192.168.50.1':raise ValueError('Unexpected production interface')
    if (args.port!=0 and not 1024<=args.port<=65535) or args.port==int(config['port']) or args.port==8796:
        raise ValueError('Isolation port must differ from the production portrait port')
    if (config['width'],config['height'])!=(423,438):raise ValueError('Baseline viewport is not423x438')
    snapshot=Path(config['snapshot']).resolve(strict=True)
    manifest_path=snapshot/'manifest.json'
    snapshot_manifest=json.loads(manifest_path.read_text(encoding='utf8'))
    if snapshot_manifest['revision']!=args.expected_revision:raise ValueError('Board/server revision differs')
    proof=dict(schema='aura.paired_ab.isolated_old_server.v1',status='CHECKED_NO_SERVER',
        production_port=int(config['port']),requested_port=args.port,isolated_port=None,listen=config['listen'],
        allowed_peer='192.168.50.2',
        revision=args.expected_revision,size=[config['width'],config['height']],background=config['background'],
        source_config_sha256=digest(args.source_config),source_hashes=hashes,
        snapshot=str(snapshot),snapshot_manifest_sha256=digest(manifest_path),
        production_modified=False,rpc_sent=False)
    if not args.execute:
        print(json.dumps(proof,ensure_ascii=True),flush=True);return 0
    if args.ready_file is None:raise ValueError('--execute requires a dedicated --ready-file')
    ready=args.ready_file.resolve(strict=False)
    if (os.path.lexists(args.ready_file) or ready.is_relative_to(aura) or ready.is_relative_to(snapshot)
            or ready==args.source_config.resolve() or ready==args.board_manifest.resolve()):
        raise ValueError('Ready file must be a new diagnostic path outside live source/config/snapshot')
    # Imports/asset decoding occur only after the coordinator's explicit execute.
    # No model API, audio, camera, or mechanical code is started by this service.
    sys.path.insert(0,str(aura))
    host=importlib.import_module('tools.portrait_host')
    render=importlib.import_module('tools.portrait_renderer')
    wire=importlib.import_module('common.portrait_wire')
    for module,key in ((host,SOURCE_KEYS[0]),(render,SOURCE_KEYS[1]),(wire,SOURCE_KEYS[2])):
        if Path(module.__file__).resolve()!=aura/key:raise ValueError('Imported a different portrait module')
    began=time.monotonic()
    renderer=render.PortraitRenderer(aura,snapshot,tuple(proof['size']),config['background'])
    class IsolatedServer(host.PortraitServer):
        # The old renderer/handler/stream lock stay unchanged. Only this new
        # instance's admission policy is narrowed to the dedicated board peer.
        def verify_request(self,request,address):return address[0]=='192.168.50.2'
    with IsolatedServer((config['listen'],args.port),renderer) as server:
        actual_port=int(server.server_address[1])
        if actual_port in (8796,int(config['port'])):raise ValueError('OS selected a production port')
        proof.update(status='READY_INDEPENDENT_PROCESS',pid=os.getpid(),
                     isolated_port=actual_port,
                     initialization_seconds=time.monotonic()-began,ready_monotonic=time.monotonic())
        # Creating this diagnostic file never edits the live server config.
        ready.parent.mkdir(parents=True,exist_ok=True)
        ready.write_text(json.dumps(proof,ensure_ascii=True,indent=2),encoding='utf8')
        print(json.dumps(proof,ensure_ascii=True),flush=True)
        try:server.serve_forever(poll_interval=.2)
        except KeyboardInterrupt:pass
        finally:
            proof.update(status='STOPPED_INDEPENDENT_PROCESS',stopped_monotonic=time.monotonic())
            ready.write_text(json.dumps(proof,ensure_ascii=True,indent=2),encoding='utf8')
    return 0

if __name__=='__main__':raise SystemExit(main())
