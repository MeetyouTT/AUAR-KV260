"""User-authorized normal KV260 shutdown before all three hosts lose power.

Run on the already authenticated Ubuntu host. Existing exclusive UART owns the
board console. Raw serial stays in Ubuntu's private local evidence directory;
only bounded metadata is copied to the shared project. No firmware, boot file,
model, identity or business-database content is changed by this script.
"""
import datetime
import importlib.util
import json
import os
from pathlib import Path
import uuid

SHARED = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-30_board_owner/ubuntu')
LOCAL = Path('/home/ghmd/aura-poweroff-20261030')
TRANSPORT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
WIRE = Path('/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREPARE = '''import json,os,platform,subprocess
from pathlib import Path
assert platform.machine() == 'aarch64', 'Expected the KV260 ARM console'
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
listing=subprocess.run(['systemctl','list-units','--type=service','--state=active','--no-legend','--plain','--no-pager'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=5)
assert listing.returncode==0, 'Service inspection failed'
units=[line.split()[0] for line in listing.stdout.splitlines() if line.split() and line.split()[0].startswith('aura-') and line.split()[0].endswith('.service')]
assert len(units)<=20 and all(all(c.isalnum() or c in '-_.@' for c in unit) for unit in units)
stops=[]
for unit in units:
 result=subprocess.run(['systemctl','stop','--no-block',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
 stops.append({'unit':unit,'stop_requested':result.returncode==0})
os.sync()
print(json.dumps({'boot_id':boot,'normal_project_service_stop_requests':stops,'files_synced':True,'firmware_or_boot_changed':False,'business_database_commands':False}))
'''


def main():
    job = uuid.uuid4().hex
    out = LOCAL / job
    out.mkdir(parents=True, mode=0o700)
    report = dict(job_id=job, started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  purpose='normal_shutdown_before_user_power_cut', poweroff_sent=False,
                  powerdown_confirmed=False, raw_serial_exported=False, local_evidence=str(out))
    uart = None
    def save():
        encoded = (json.dumps(report, ensure_ascii=True, indent=2)+'\n').encode()
        for path in (out/'status.json', SHARED/'shutdown_board_result.json'):
            temporary = path.with_suffix('.json.partial')
            with temporary.open('wb') as stream:
                stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
            os.replace(str(temporary), str(path))
    save()
    try:
        transport, wire = load('shutdown_uart_transport', TRANSPORT), load('shutdown_board_wire', WIRE)
        with (out/'serial.raw').open('xb') as raw:
            uart = transport.UART(raw)
            uart.connect()
            rc, data, digest = uart.command(wire.wire(PREPARE), 'NORMAL_SHUTDOWN_PREPARE', 30)
            report['preparation_exit_code'] = rc
            report['preparation_output_sha256'] = digest
            if rc != 0:
                raise RuntimeError('Normal shutdown preparation failed')
            report['preparation'] = json.loads(data)
            save()
            report['poweroff_sent'] = True
            save()
            report.update(uart.poweroff())
            # poweroff() already restored board echo before losing its shell.
            # close() must now restore only host termios, never await a dead shell.
            uart.shell_ready = False
            report['console_echo_restored'] = uart.close()
            uart = None
    except Exception as exc:
        report['error_type'] = type(exc).__name__
        report['error'] = str(exc)[:200]
    finally:
        if uart is not None:
            report['console_echo_restored'] = uart.close()
        report['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
        os.sync()
    print(json.dumps(report), flush=True)
    return 0 if report['powerdown_confirmed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
