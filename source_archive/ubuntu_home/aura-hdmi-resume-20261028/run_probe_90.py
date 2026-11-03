"""Use the existing exclusive console transport and preserve private raw evidence."""
import importlib.util, json, sys
from pathlib import Path
from datetime import datetime, timezone

root=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('wire','/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
wire=importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
src=root/sys.argv[1]
command=wire.wire(src.read_text())
uart=None
status={}
raw_path=src.with_name(src.stem+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'.serial.raw')
with raw_path.open('xb') as raw:
    try:
        uart=wire.transport_module().UART(raw)
        uart.connect()
        rc,body,digest=uart.command(command,'MODELINVENTORY',90)
        status.update(exit_code=rc,sha256=digest)
        if rc==0:
            data=json.loads(body)
            src.with_suffix('.response.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps(data,ensure_ascii=False))
        else:
            print(body.decode(errors='replace')[-1500:])
    finally:
        if uart:
            status['console_echo_restored']=uart.close()
        src.with_suffix('.status.json').write_text(json.dumps(status,indent=2)+'\n')
print(json.dumps(status))
