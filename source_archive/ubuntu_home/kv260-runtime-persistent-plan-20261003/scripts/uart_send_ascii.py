#!/usr/bin/env python3
"""Send newline-safe ASCII to an active board-console `cat` receiver."""
import os
import sys
import termios
import time

if len(sys.argv) != 3:
    raise SystemExit("usage: uart_send_ascii.py SERIAL_DEVICE BASE64_FILE")
device, source = sys.argv[1:]
with open(source, "rb") as f:
    payload = f.read()
if any(c not in b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\r\n" for c in payload):
    raise SystemExit("input contains non-base64 characters")
fd = os.open(device, os.O_WRONLY | os.O_NOCTTY)
try:
    offset = 0
    while offset < len(payload):
        offset += os.write(fd, payload[offset:offset + 1024])
    termios.tcdrain(fd)
    time.sleep(0.25)
    os.write(fd, b"\x04")  # canonical-mode EOF after final newline
    termios.tcdrain(fd)
finally:
    os.close(fd)
print(f"sent {len(payload)} ASCII bytes; sent EOF")
