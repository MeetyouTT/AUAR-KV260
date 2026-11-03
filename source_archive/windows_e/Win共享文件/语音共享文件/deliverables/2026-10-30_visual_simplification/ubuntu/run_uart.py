#!/usr/bin/env python3
"""Run an explicitly reviewed task script through the existing exclusive UART.

Preserves framed SHA256 evidence, never guesses a login, and restores echo
before closing the raw evidence handle. No automatic interrupt or retry.
"""
import argparse
import base64
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import wave

HERE = Path(__file__).resolve().parent
TRANSPORT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
WIRE = Path('/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('script', type=Path)
    parser.add_argument('--timeout', type=int, default=55)
    parser.add_argument('--upload-public-wav',action='store_true')
    parser.add_argument('--use-uploaded-public-wav')
    args = parser.parse_args()
    source = args.script.resolve()
    assert source.parent == HERE, 'Only this handoff task scripts are accepted'
    assert 1 <= args.timeout <= 600
    raw_source = source.read_bytes()
    compile(raw_source, str(source), 'exec')
    encoded = base64.b64encode(gzip.compress(raw_source, mtime=0)).decode('ascii')
    sha = hashlib.sha256(raw_source).hexdigest()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    evidence = HERE/'evidence'/(stamp+'-'+source.stem)
    evidence.mkdir(parents=True, exist_ok=False)
    target = '/tmp/aura-visual-ubuntu-'+sha[:16]+'-'+stamp+'.b64'
    uart_module = load_module('task_uart', TRANSPORT)
    wire_module = load_module('task_wire', WIRE)
    status = dict(script=source.name, script_sha256=sha, port=uart_module.PORT,
                  started_utc=stamp, complete=False, commands=[], remote_payload=target)
    uart = None
    public_path = None
    if args.use_uploaded_public_wav:
        assert not args.upload_public_wav
        assert re.fullmatch(r'/tmp/aura-visual-public-[0-9a-f]{16}-[0-9TZ]+\.wav',args.use_uploaded_public_wav)
        public_path = args.use_uploaded_public_wav
    try:
        with (evidence/'serial.raw').open('xb') as raw:
            try:
                uart = uart_module.UART(raw)
                uart.connect()

                if args.upload_public_wav:
                    audio = HERE.parents[2]/'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav'
                    audio_bytes = audio.read_bytes()
                    with wave.open(str(audio),'rb') as wav:
                        assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate()) == (1,2,16000)
                    audio_sha = hashlib.sha256(audio_bytes).hexdigest()
                    public_path = '/tmp/aura-visual-public-'+audio_sha[:16]+'-'+stamp+'.wav'
                    receiver = '''import os,termios,tty,time,select,hashlib
from pathlib import Path
p=Path(DEST);tmp=p.with_suffix('.partial')
assert not p.exists() and not p.is_symlink() and not tmp.exists() and not tmp.is_symlink()
fd=0;old=termios.tcgetattr(fd);total=0;h=hashlib.sha256()
try:
 tty.setraw(fd)
 with tmp.open('xb') as out:
  os.write(1,b'VISUAL_PUBLIC_READY\\n');deadline=time.monotonic()+45
  while total<COUNT:
   if time.monotonic()>deadline:raise TimeoutError('Public file transfer expired')
   if select.select([fd],[],[],.1)[0]:
    part=os.read(fd,min(4096,COUNT-total));out.write(part);h.update(part);total+=len(part)
  out.flush();os.fsync(out.fileno())
 assert h.hexdigest()==EXPECTED,'Public audio hash mismatch'
 os.link(str(tmp),str(p));tmp.unlink()
 os.write(1,('VISUAL_PUBLIC_DONE '+h.hexdigest()+'\\n').encode())
finally:termios.tcsetattr(fd,termios.TCSANOW,old)
'''.replace('DEST',repr(public_path)).replace('COUNT',str(len(audio_bytes))).replace('EXPECTED',repr(audio_sha))
                    uart.line(wire_module.wire(receiver))
                    assert uart.receive(10,re.compile(rb'(?m)^VISUAL_PUBLIC_READY\r?$')), 'Public receiver not ready'
                    uart.buf = b''
                    uart.write(audio_bytes)
                    assert uart.receive(50,re.compile(rb'(?m)^VISUAL_PUBLIC_DONE '+audio_sha.encode()+rb'\r?$')), 'Public file SHA not confirmed'
                    assert uart.receive(5,uart_module.PROMPT), 'Public transfer missing shell prompt'
                    uart.shell_ready = True
                    status['public_audio'] = dict(source='existing_upstream_public_test_wavs/0.wav',
                                                  bytes=len(audio_bytes),sha256=audio_sha,remote_path=public_path)

                def send(label, body, timeout=25):
                    marker = 'VU'+str(len(status['commands'])).zfill(3)
                    rc, response, digest = uart.command(wire_module.wire(body), marker, timeout)
                    (evidence/(label+'.output')).write_bytes(response)
                    status['commands'].append(dict(label=label, exit_code=rc,
                                                   bytes=len(response), sha256=digest))
                    if rc:
                        raise RuntimeError(label+' failed; inspect '+str(evidence/(label+'.output')))
                    return response

                for offset in range(0, len(encoded), 900):
                    chunk = encoded[offset:offset+900]
                    end = offset+len(chunk)
                    body = ("import hashlib,json,os\nfrom pathlib import Path\n"
                            f"p=Path({target!r});assert not p.is_symlink()\n"
                            f"d=p.read_bytes() if p.exists() else b'';assert len(d)=={offset}\n"
                            f"with p.open({'xb' if offset == 0 else 'ab'!r}) as f:"
                            f"f.write({chunk.encode()!r});f.flush();os.fsync(f.fileno())\n"
                            f"assert hashlib.sha256(p.read_bytes()).hexdigest()=="
                            f"{hashlib.sha256(encoded[:end].encode()).hexdigest()!r}\n"
                            f"print(json.dumps(dict(offset={end})))\n")
                    send('chunk-'+str(offset), body)
                body = ("import base64,gzip,hashlib\nfrom pathlib import Path\n"
                        f"p=Path({target!r});assert not p.is_symlink()\n"
                        "data=gzip.decompress(base64.b64decode(p.read_bytes(),validate=True))\n"
                        f"assert hashlib.sha256(data).hexdigest()=={sha!r}\n"
                        f"exec(compile(data,{source.name!r},'exec'),"
                        f"{{'__name__':'__main__','__file__':{source.name!r},"
                        f"'PUBLIC_WAV_PATH':{public_path!r}}})\n")
                response = send('result', body, args.timeout)
                parsed = json.loads(response)
                (evidence/'result.json').write_text(json.dumps(parsed,ensure_ascii=False,indent=2)+'\n')
                status.update(complete=True, result_file=str(evidence/'result.json'))
            finally:
                if uart is not None:
                    status['console_echo_restored'] = uart.close()
    except Exception as exc:
        status['error'] = type(exc).__name__+': '+str(exc)
    (evidence/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(status,ensure_ascii=False))
    raise SystemExit(0 if status['complete'] and status.get('console_echo_restored') else 1)


if __name__ == '__main__':
    main()
