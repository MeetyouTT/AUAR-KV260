"""Cancel only the evidenced incomplete UART shell input, not a running task."""
import datetime,importlib.util,json,re
from pathlib import Path
spec=importlib.util.spec_from_file_location('wire','/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
out=Path('/home/ghmd/aura-pan-board-20261024/uart')/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-interrupted-transfer-console')
out.mkdir();status={};u=None
try:
 with (out/'serial.raw').open('xb') as raw:
  u=wire.UART(raw)
  try:
   u.receive(.3);u.buf=b'';u.write(b'\r');u.receive(1)
   if not wire.PROMPT.search(u.buf):
    assert re.fullmatch(rb'(?:[\r\n ]*> )+',u.buf), 'No exact shell continuation; no interrupt sent'
    u.buf=b'';u.write(b'\x03');assert u.receive(3,wire.PROMPT)
    status['incomplete_shell_input_cancelled']=True
   u.shell_ready=True
  finally:status['console_echo_restored']=u.close()
finally:
 (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
print(json.dumps({'evidence':str(out),**status}))
