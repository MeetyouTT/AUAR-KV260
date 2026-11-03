"""One user-authorized board capture; verifies bytes before local exclusive save."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import subprocess
import threading

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import KEY


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True)
    parser.add_argument('--clip',type=int,required=True,choices=(1,2,3,4))
    parser.add_argument('--audible-cues',action='store_true',help='Start/end tones on this Windows PC')
    args=parser.parse_args()
    if not re.fullmatch('[a-f0-9]{32}',args.session): parser.error('Random session token required')
    directory=HERE.parents[1]/'声纹测试录音'/args.session
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/('clip-%02d.wav'%args.clip)
    if path.exists(): raise ValueError('Local recording already exists')
    script=(HERE/'capture_board_clip.py').read_text(encoding='utf-8').replace(
        'SESSION_TOKEN_PLACEHOLDER',args.session).replace('CLIP_NUMBER_PLACEHOLDER',str(args.clip))
    process=subprocess.Popen(['C:/Windows/System32/OpenSSH/ssh.exe','-i',str(KEY),'-o','IdentitiesOnly=yes',
        '-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=4',
        'root@192.168.50.2','python3 -'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,text=True,encoding='utf-8')
    timer=threading.Timer(35,process.kill);timer.daemon=True;timer.start()
    try:
        process.stdin.write(script);process.stdin.close()
        first=process.stdout.readline()
        if not first: raise RuntimeError(process.stderr.read())
        event=json.loads(first)
        if event.get('event')!='CAPTURE_STARTED':raise ValueError('Missing actual capture start')
        print(json.dumps(event),flush=True)
        if args.audible_cues:
            import winsound
            winsound.Beep(880,150)
        result=json.loads(process.stdout.readline())
        if process.wait(timeout=3)!=0:raise RuntimeError(process.stderr.read())
        if args.audible_cues:
            winsound.Beep(660,120);winsound.Beep(660,120)
    finally:
        timer.cancel()
        if process.poll() is None:process.kill();process.wait(timeout=3)
    raw=base64.b64decode(result['wav_base64'],validate=True);meta=result['metadata']
    if hashlib.sha256(raw).hexdigest()!=meta['wav_sha256'] or meta['session_id']!=args.session or meta['clip_number']!=args.clip:
        raise ValueError('Capture transport mismatch')
    with path.open('xb') as output:output.write(raw)
    path.with_suffix('.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print(json.dumps({'state':'CAPTURED','clip':args.clip,'local_wav':str(path),
                      'duration_seconds':meta['duration_seconds'],'wav_sha256':meta['wav_sha256']},ensure_ascii=False))


if __name__=='__main__':main()
