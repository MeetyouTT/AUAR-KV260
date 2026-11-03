"""Run only the fixed read-only CPU probe through the existing exclusive UART."""
import datetime,hashlib,importlib.util,json
from pathlib import Path

root=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('reviewed_wire','/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
source=(root/'probe.py').read_text();command=wire.wire(source)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
directory=root/'evidence'/stamp;directory.mkdir(parents=True,mode=0o700)
status={'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'complete':False};uart=None
try:
    with (directory/'serial.raw').open('xb') as raw:
        try:
            uart=wire.transport_module().UART(raw);uart.connect()
            rc,body,digest=uart.command(command,'CPUOBSERVE',45)
            (directory/'response.output').write_bytes(body)
            status.update(exit_code=rc,sha256=digest,complete=(rc==0))
            if rc==0:
                value=json.loads(body);value['verified_host_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
                (root/'latest.json').write_text(json.dumps(value,indent=2)+'\n')
                a=[s['cpu_busy_percent']['cpu'] for s in value['samples']]
                print(json.dumps({'host_utc':value['verified_host_utc'],'boot':value['boot_id'],'before':value['before'],'after':value['after'],'board_cpu_average_percent':sum(a)/len(a),'board_cpu_peak_one_second_percent':max(a),'per_core_peaks':{k:max(s['cpu_busy_percent'][k] for s in value['samples']) for k in value['samples'][0]['cpu_busy_percent'] if k!='cpu'},'temperatures':value['samples'][-1]['temperature_c'],'memory':value['memory'],'duration_s':value['duration_s']}))
        finally:
            if uart:status['console_echo_restored']=uart.close()
except Exception as error:status.update(error_type=type(error).__name__,error=str(error)[:300])
(directory/'status.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps(status))
raise SystemExit(0 if status['complete'] else 1)
