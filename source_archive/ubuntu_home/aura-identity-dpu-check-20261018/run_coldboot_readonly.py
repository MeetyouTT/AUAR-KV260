"""Guarded diagnostic runner with passive boot observation before console input."""
import base64,hashlib,importlib.util,json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent
spec=importlib.util.spec_from_file_location('wire','/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
source=ROOT/'board_coldboot_flicker_readonly.py';code=source.read_text();command=wire.wire(code)
out=ROOT/'evidence'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-coldboot-flicker-readonly');out.mkdir(mode=0o700)
(out/'source.py').write_text(code)
status={'evidence':str(out),'source_sha256':hashlib.sha256(code.encode()).hexdigest(),'complete':False};uart=None
try:
 with (out/'serial.raw').open('xb') as raw:
  try:
   uart=wire.transport_module().UART(raw);uart.receive(3)
   if re.search(rb'U-Boot|ZynqMP>|Hit any key|Starting kernel',uart.buf) and not wire.transport_module().PROMPT.search(uart.buf):
    raise RuntimeError('Boot activity observed; no console input sent')
   uart.connect();rc,body,digest=uart.command(command,'COLDREAD',40)
   (out/'response.output').write_bytes(body);status.update(exit_code=rc,sha256=digest,complete=rc==0)
   if rc==0:
    value=json.loads(body);(out/'response.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value),flush=True)
   else:print('Diagnostic failed; raw output retained privately')
  finally:
   if uart:status['console_echo_restored']=uart.close()
except Exception as e:status['error']=str(e)
(out/'status.json').write_text(json.dumps(status,indent=2)+'\n');(ROOT/'latest-coldboot-flicker-readonly.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps(status),flush=True)
raise SystemExit(0 if status['complete'] else 1)
