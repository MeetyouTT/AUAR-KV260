"""Use the same exclusive UART with a bounded long maintenance response."""
import datetime,importlib.util,json,sys
from pathlib import Path
root=Path(__file__).resolve().parent;source=Path(sys.argv[1]).resolve()
assert root in source.parents
spec=importlib.util.spec_from_file_location('wire','/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
command=wire.wire(source.read_text());uart=None;status={}
with source.with_name(source.stem+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.serial.raw').open('xb') as raw:
 try:
  uart=wire.transport_module().UART(raw);uart.connect();rc,body,digest=uart.command(command,'WIDERESUME',110)
  status.update(exit_code=rc,sha256=digest)
  if rc==0:source.with_suffix('.response.json').write_text(json.dumps(json.loads(body),indent=2)+'\n');print(body.decode())
  else:source.with_suffix('.error.private.txt').write_bytes(body);raise RuntimeError('Maintenance command failed; private error retained')
 finally:
  if uart:status['console_echo_restored']=uart.close()
  source.with_suffix('.status.json').write_text(json.dumps(status,indent=2)+'\n')
