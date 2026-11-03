#!/usr/bin/env python3
"""Read-only hub, GPIO and device-tree diagnostics over UART."""
from pathlib import Path
source = (Path(__file__).parent / 'probe.py').read_text()
start = source.index('commands=[')
end = source.index('\nfor p in sorted', start)
commands = [
 ['sh', '-c', 'ls -l /sys/bus/platform/drivers/microchip,usb5744/; ls -l /sys/bus/i2c/devices/1-002d/of_node; cat /sys/bus/i2c/devices/1-002d/name'],
 ['cat', '/sys/kernel/debug/gpio'],
 ['sh', '-c', 'ls -l /sys/bus/i2c/drivers/usb5744/; ls -l /sys/bus/platform/drivers/xhci-hcd/'],
 ['sh', '-c', "dmesg | grep -Ei 'usb|hub|regulator|over.current|gpio|fpga' | tail -100"],
 ['sh', '-c', 'cat /proc/uptime; lsusb -t'],
 ['python3', '-c', "from pathlib import Path;import json;root=Path('/sys/firmware/devicetree/base');out={};\nfor p in root.rglob('compatible'):\n b=p.read_bytes();\n if b'usb5744' in b or b'usb-hub' in b or b'usb2734' in b:\n  out[str(p.parent)]={x.name:x.read_bytes().hex() for x in p.parent.iterdir() if x.is_file()}\nprint(json.dumps(out))"],
]
source = source[:start] + 'commands=' + repr(commands) + source[end:]
source = source.replace("'CURRENT_INVENTORY.json'", "'CURRENT_HUB_DIAGNOSTIC.json'")
source = source.replace('print(data.decode())', "print(json.dumps({'evidence':str(out),'commands':json.loads(data)['commands']},indent=2))")
exec(compile(source, str(Path(__file__).parent / 'probe.py'), 'exec'))
