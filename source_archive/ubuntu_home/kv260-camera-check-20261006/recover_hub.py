#!/usr/bin/env python3
"""Rebind only the identified USB5744 I2C control device; record evidence."""
from pathlib import Path
source = (Path(__file__).parent / 'probe.py').read_text()
start = source.index('commands=[')
end = source.index('\nfor p in sorted', start)
recovery = '''
driver=Path('/sys/bus/i2c/drivers/usb5744')
dev=Path('/sys/bus/i2c/devices/1-002d')
assert dev.joinpath('name').read_text().strip()=='usb5744'
assert dev.joinpath('driver').resolve()==driver
assert not list(Path('/sys/class/video4linux').glob('video*'))
assert sorted(x.name for x in Path('/sys/bus/usb/devices').iterdir() if x.name[0].isdigit())==['1-0:1.0','2-0:1.0']
before=run(['lsusb','-t'])
driver.joinpath('unbind').write_text('1-002d')
try:
 driver.joinpath('bind').write_text('1-002d')
finally:
 if not dev.joinpath('driver').exists():
  try:driver.joinpath('bind').write_text('1-002d')
  except Exception as e:print('Driver restore failed:',str(e))
import time
time.sleep(3)
commands=[['lsusb','-t'],['lsusb'],['v4l2-ctl','--list-devices'],['sh','-c',"dmesg | grep -Ei 'usb|uvc|hub' | tail -35"]]
'''
source = source[:start] + recovery + source[end:]
source = source.replace("'CURRENT_INVENTORY.json'", "'CURRENT_HUB_RECOVERY.json'")
source = source.replace('print(data.decode())', "print(json.dumps({'evidence':str(out),'commands':json.loads(data)['commands']},indent=2))")
exec(compile(source, str(Path(__file__).parent / 'probe.py'), 'exec'))
