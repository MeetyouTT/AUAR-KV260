"""Resume terminal output once; do not interrupt, reset, or guess login."""
from datetime import datetime,timezone
import importlib.util,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('checked_wire','/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
transport=wire.transport_module()
out=ROOT/'evidence'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-uart-output-resume')
out.mkdir(mode=0o700)
(out/'source.py').write_bytes(Path(__file__).read_bytes())
report={'status':'UART_OUTPUT_RESUME_PROBE','root_confirmed':False,'board_command_sent':False}
uart=None
try:
 with (out/'serial.raw').open('xb') as raw:
  try:
   uart=transport.UART(raw)
   base=Path('/sys/class/tty/ttyUSB1/device').resolve().parent
   report['interface_runtime_status_while_open']=(base/'power/runtime_status').read_text().strip()
   # XON only resumes paused console output; no Ctrl-C, break, reset or login.
   uart.write(b'\x11\r')
   if not uart.receive(6,transport.PROMPT):
    raise RuntimeError('No root prompt after output resume; no board command sent')
   uart.connect();report['root_confirmed']=True
   command="import json;from pathlib import Path;p=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93/activation-final-result.json');print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'activation_result':json.loads(p.read_text()) if p.exists() else None}))"
   report['board_command_sent']=True
   rc,body,sha=uart.command(wire.wire(command),'RESUMEPROBE',12)
   report.update(exit_code=rc,response_sha256=sha)
   if rc==0:
    value=json.loads(body)
    if value.get('activation_result'):
     value['activation_result']['camera_samples_count']=len(value['activation_result'].pop('camera_samples',[]))
    report['result']=value
  finally:
   if uart:report['console_echo_restored']=uart.close()
except Exception as exc:
 report['error']=str(exc)
report['raw_bytes']=(out/'serial.raw').stat().st_size if (out/'serial.raw').exists() else 0
report['evidence']=str(out)
(out/'status.json').write_text(json.dumps(report,indent=2)+'\n')
(ROOT/'latest-uart-output-resume.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
