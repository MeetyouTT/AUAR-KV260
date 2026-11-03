"""Guard a normal shutdown so the user can perform a real power-on test."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

PACKAGE=Path(__file__).resolve().parent.parent
PREFLIGHT='''import hashlib,json,os,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='b0a424d4-e8ef-4f96-aaeb-4853219de5ed'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
assert Path('/sys/module/zynqmp_dpsub/parameters/initial_aux_delay_ms').read_text().strip()=='5000'
m=json.loads(Path('/boot/aura-hdmi-preinit-20261021/before.json').read_text())
assert hashlib.sha256(Path('/boot/uEnv.txt').read_bytes()).hexdigest()==m['candidate_uenv_sha256']
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=2) as r:s=json.load(r)
assert s['phase']=='IDLE' and not s.get('playing'), 'Application busy; leave it running'
os.sync()
print(json.dumps({'boot_id':'b0a424d4-e8ef-4f96-aaeb-4853219de5ed','candidate_selected':True,'ui_idle':True,'files_synced':True}))
'''


def main():
    spec=importlib.util.spec_from_file_location('wire','/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
    wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
    mod=wire.transport_module()
    out=Path('/home/ghmd/aura-identity-dpu-check-20261018/evidence')/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-hdmi-coldboot-poweroff')
    out.mkdir(parents=True)
    status=dict(evidence=str(out),poweroff_sent=False,powerdown_confirmed=False)
    uart=None
    try:
        with (out/'serial.raw').open('xb') as raw:
            try:
                uart=mod.UART(raw);uart.connect()
                rc,body,digest=uart.command(wire.wire(PREFLIGHT),'HDMISHUT',20)
                (out/'preflight.output').write_bytes(body)
                assert rc==0,body.decode(errors='replace')[-1000:]
                status['preflight']=json.loads(body)
                status['poweroff_sent']=True
                status.update(uart.poweroff())
            finally:
                if uart:status['console_echo_restored']=uart.close()
    except Exception as exc:status['error']=str(exc)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    (PACKAGE/'evidence/poweroff.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status),flush=True)
    if not status['powerdown_confirmed']:raise SystemExit(1)


if __name__=='__main__':main()
