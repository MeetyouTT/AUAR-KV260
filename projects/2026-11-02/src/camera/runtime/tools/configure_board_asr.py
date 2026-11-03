"""Configure the local GTK recorder's ASR endpoint; run on the KV260."""
import argparse
import json
from pathlib import Path
import sys
import time
import urllib.request

AURA=Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))
from board.runtime.audio.transcription import configuration


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',required=True,help='Recognition computer IPv4 address')
    parser.add_argument('--port',type=int,default=8791)
    parser.add_argument('--timeout-ms',type=int,default=30000)
    parser.add_argument('--disable',action='store_true')
    args=parser.parse_args(argv)
    values=configuration({'enabled':not args.disable,'host':args.host,'port':args.port,'timeout_ms':args.timeout_ms})
    base='http://127.0.0.1:8783'
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    data=json.dumps({'type':'asr_config','values':values}).encode()
    req=urllib.request.Request(base+'/api/command',data=data,
        headers={'Origin':base,'Content-Type':'application/json'})
    with opener.open(req,timeout=4) as reply:result=json.load(reply)
    if not result.get('ok'):raise RuntimeError(str(result))
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        with opener.open(base+'/api/state',timeout=2) as reply:state=json.load(reply)
        commands=state.get('avatar_renderer',{}).get('command_results',[])
        command=next((row for row in commands if row['command_id']==result['command_id']),None)
        if command:
            if not command['ok']:raise RuntimeError(command.get('error','Configuration failed'))
            print(json.dumps({'configured':values,'recognition_not_yet_verified':True},ensure_ascii=False))
            return 0
        time.sleep(.1)
    raise TimeoutError('GTK configuration acknowledgement was not observed')


if __name__=='__main__':raise SystemExit(main())
