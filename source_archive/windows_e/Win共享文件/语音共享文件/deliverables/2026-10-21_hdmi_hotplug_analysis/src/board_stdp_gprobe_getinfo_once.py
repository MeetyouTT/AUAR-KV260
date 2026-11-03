"""Send one read-only GProbe identity request, once per command/index record.

B03 schematic page 9 connects CDBUS0/1 through U65 to STDP4320 UART.
DDBUS0 is NC; DDBUS1 is EEPROM write-control. Do not use interface 03.
"""
import fcntl
import argparse
import glob
import hashlib
import json
import os
from pathlib import Path
import select
import termios
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--query', choices=['information', 'device-id'], default='information')
parser.add_argument('--index', type=int, choices=range(8), default=0)
args = parser.parse_args()
assert args.query == 'device-id' or args.index == 0
command_code = 0x40 if args.query == 'information' else 0x30
command_name = 'GetInformation index 0' if args.query == 'information' else 'GetDeviceId index '+str(args.index)
record_name = 'getinfo' if args.query == 'information' else 'getdeviceid'+str(args.index)
paths = glob.glob('/dev/serial/by-id/usb-Xilinx_ML_Carrier_Card_*-if02-port0')
assert len(paths) == 1, 'expected exactly one KV260 FTDI interface C serial path'
port = paths[0]
real = Path(os.path.realpath(port))
assert real.name.startswith('ttyUSB')
q = Path(os.path.realpath(Path('/sys/class/tty')/real.name/'device'))
parents = [q, *q.parents]
iface = next((p for p in parents if (p/'bInterfaceNumber').exists()), None)
assert iface is not None and (iface/'bInterfaceNumber').read_text().strip() == '02'
usb_device = next((p for p in parents if (p/'idVendor').exists() and (p/'idProduct').exists()), None)
assert usb_device is not None
assert (usb_device/'idVendor').read_text().strip().lower() == '0403'
assert (usb_device/'idProduct').read_text().strip().lower() == '6011'

# GProbe Serial1 frame: length, approved identity command, bounded index, checksum.
request_body = bytes([0x04, command_code, args.index])
request = request_body + bytes([(-sum(request_body)) & 0xff])
record_dir = Path(__file__).resolve().parent
marker = record_dir/('gprobe-if02-'+record_name+'-once-request.json')
with marker.open('x') as f:
    f.write(json.dumps({'command':command_name,'interface':'02',
                        'attempt_reserved':True,'automatic_retries':0})+'\n')
fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
old = termios.tcgetattr(fd)
sent = False
pre_count = 0
received = bytearray()
valid = None
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    attrs = termios.tcgetattr(fd)
    attrs[0] = attrs[1] = attrs[3] = 0
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[4] = attrs[5] = termios.B115200
    attrs[6][termios.VMIN] = attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)

    # Preserve any already queued bytes in memory; never flush the UART RX queue.
    if select.select([fd], [], [], 0.05)[0]:
        data = os.read(fd, 512)
        received.extend(data)
        pre_count = len(data)

    n = os.write(fd, request)
    assert n == len(request)
    sent = True
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and len(received) < 512:
        ready, _, _ = select.select([fd], [], [], max(0, min(0.05, deadline-time.monotonic())))
        if ready:
            data = os.read(fd, 512-len(received))
            if not data:
                break
            received.extend(data)
            # A bounded single-response query; stop after first valid info frame.
            for i in range(max(0, len(received)-1)):
                size = received[i]
                end = i + size
                if size >= 3 and end <= len(received) and received[i+1] == command_code:
                    frame = bytes(received[i:end])
                    if sum(frame) & 0xff == 0 and frame != request and i >= pre_count:
                        payload = frame[2:-1]
                        ascii_ok = all(32 <= b <= 126 or b in (0, 9, 10, 13) for b in payload)
                        valid = {'frame_length':size,'checksum_valid':True,'payload_bytes':len(payload),
                                 'payload_sha256':hashlib.sha256(payload).hexdigest(),
                                 'payload_ascii':payload.decode('ascii','replace').rstrip('\0').strip() if ascii_ok else None}
                        break
            if valid:
                break
finally:
    try:
        termios.tcsetattr(fd, termios.TCSANOW, old)
    finally:
        os.close(fd)

private_rx = record_dir/('gprobe-if02-'+record_name+'-once.rx')
with private_rx.open('xb') as f:
    os.fchmod(f.fileno(), 0o600)
    f.write(received)
result = {'transport':'FTDI interface 02 (CDBUS0/1 via U65) / STDP4320 UART per B03 design reference',
                  'baud':'115200 8N1','command':'GProbe '+command_name,
                  'request_frames_sent':1 if sent else 0,'request_bytes_sent':len(request) if sent else 0,
                  'preexisting_rx_bytes_read_into_memory':pre_count,'total_rx_bytes':len(received),
                  'reply':valid,'retries':0,'reset_commands':0,'register_reads_or_writes':0,
                  'spi_flash_reads_or_writes':0,'i2c_transactions':0,'gpio_writes':0}
result_path = record_dir/('gprobe-if02-'+record_name+'-once-result.json')
result_path.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result, ensure_ascii=True),flush=True)
