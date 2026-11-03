#!/usr/bin/env python3
"""Read-only USB kernel diagnostics through the existing inventory transport."""
from pathlib import Path
source = (Path(__file__).parent / 'probe.py').read_text()
start = source.index('commands=[')
end = source.index('\nfor p in sorted', start)
source = source[:start] + "commands=[['lsusb','-t'],['sh','-c',\"dmesg | grep -Ei 'usb|xhci|uvc|video' | tail -100\"],['sh','-c',\"lsmod | grep -Ei 'uvc|video|xhci|usb'\"],['modinfo','uvcvideo']]" + source[end:]
source = source.replace("print(data.decode())", "print(data.decode())")
source = source.replace("'CURRENT_INVENTORY.json'", "'CURRENT_USB_DIAGNOSTIC.json'")
exec(compile(source, str(Path(__file__).parent / 'probe.py'), 'exec'))
