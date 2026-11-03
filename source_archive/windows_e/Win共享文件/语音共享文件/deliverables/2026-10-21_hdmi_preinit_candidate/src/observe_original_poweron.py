"""Passively observe user power-on; never send input during bootloader startup."""
import importlib.util,json,re,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent
spec=importlib.util.spec_from_file_location('wire','/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire);mod=wire.transport_module()
out=ROOT/'evidence'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-hdmi-original-poweron-observe');out.mkdir()
v={'evidence':str(out),'root_prompt_seen':False,'bootloader_input_sent':False};uart=None
try:
 with (out/'serial.raw').open('xb') as raw:
  try:
   uart=mod.UART(raw);start=last=time.monotonic()
   while time.monotonic()-start<180:
    uart.receive(1)
    if mod.PROMPT.search(uart.buf):v['root_prompt_seen']=True;break
    if time.monotonic()-last>20:
     print(json.dumps({'passive_wait_seconds':round(time.monotonic()-start,1),'bytes_received':len(uart.buf)}),flush=True);last=time.monotonic()
   text=uart.buf.decode(errors='replace')
   v['milestones']=[x for x in text.splitlines() if 'Linux version ' in x or 'root (automatic login)' in x or 'Starting kernel' in x or 'AURA initial AUX' in x]
   if v['root_prompt_seen']:
    uart.shell_ready=True
    code="import json;from pathlib import Path;print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'cmdline':Path('/proc/cmdline').read_text().strip(),'version':Path('/proc/version').read_text().strip()}))"
    rc,body,digest=uart.command(wire.wire(code),'HDMIBACK',15)
    assert rc==0;v['linux']=json.loads(body)
  finally:
   if uart:v['console_echo_restored']=uart.close()
except Exception as e:v['error']=str(e)
(out/'status.json').write_text(json.dumps(v,indent=2)+'\n');(ROOT/'latest-original-poweron-observe.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v),flush=True)
