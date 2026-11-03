"""Resume the existing U-Boot bootcmd after an accidental autoboot stop."""
from datetime import datetime,timezone
import importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('transport','/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
out=ROOT/'evidence'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-resume-boot')
out.mkdir(parents=True,mode=0o700)
status={'boot_command_sent':False,'environment_modified':False,'flash_commands_sent':False};uart=None
with (out/'serial.raw').open('xb') as raw:
 try:
  uart=t.UART(raw)
  uart.line('printenv bootcmd')
  assert uart.receive(4,re.compile(rb'(?m)^ZynqMP> ')),'U-Boot prompt not confirmed; no boot command sent'
  value=uart.buf.decode(errors='replace')
  assert re.search(r'(?m)^bootcmd=',value),'No bootcmd found; no boot command sent'
  status['bootcmd_readback']=next(line.strip() for line in value.splitlines() if line.startswith('bootcmd='))
  print(json.dumps({'status':'UBOOT_BOOTCMD_CONFIRMED','bootcmd':status['bootcmd_readback']}),flush=True)
  uart.line('boot');status['boot_command_sent']=True
  ready=uart.receive(30,t.PROMPT)
  status['root_prompt_seen']=ready
  status['kernel_started']=b'Linux version ' in uart.buf or b'Starting kernel' in uart.buf
  uart.shell_ready=ready
  print(json.dumps({'status':'ROOT_READY' if ready else 'BOOT_CONTINUING','kernel_started':status['kernel_started']}),flush=True)
 except Exception as exc:
  status['error']=str(exc)
 finally:
  if uart:status['console_echo_restored']=uart.close()
(out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
(ROOT/'latest-resume-boot.json').write_text(json.dumps(dict(status,evidence=str(out)),indent=2)+'\n')
print(json.dumps(status),flush=True)
