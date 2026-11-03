import importlib.util,json,re,sys
from datetime import datetime,timezone
from pathlib import Path
spec=importlib.util.spec_from_file_location('wire','/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
transport=wire.transport_module();root=Path(__file__).resolve().parent
source=Path('/home/ghmd/aura-model-inventory-20261021/native_hdmi_cached_compare.py')
raw_path=root/('passive-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'.serial.raw')
status={'bootloader_input_sent':False,'snapshot_sent':False}
uart=None
with raw_path.open('xb') as raw:
 try:
  uart=transport.UART(raw)
  seen=uart.receive(20,transport.PROMPT)
  if seen:
   uart.connect()
   rc,body,digest=uart.command(wire.wire(source.read_text()),'HDMICACHED',35)
   status.update(exit_code=rc,sha256=digest,snapshot_sent=True)
   if rc==0:
    value=json.loads(body);(root/'current-cached-snapshot.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'boot':value['boot'],'uptime':value['uptime'],'connectors':value['connectors'],'scanout':value['scanout'],'xorg_initial_mode':value['xorg_initial_mode'],'camera':value.get('camera'),'gui':value.get('gui')}))
  else:status['reason']='No passive root prompt observed; no task command or bootloader input sent'
 finally:
  if uart:status['console_echo_restored']=uart.close()
  (root/'passive-status.json').write_text(json.dumps(status,indent=2)+'\n')
print(json.dumps(status))
