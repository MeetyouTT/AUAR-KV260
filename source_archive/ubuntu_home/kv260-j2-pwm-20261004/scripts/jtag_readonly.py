#!/usr/bin/env python3
"""Read JTAG target inventory using a private, temporary hardware server."""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import signal
from pathlib import Path
import socket
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--uart-registers', action='store_true',
                    help='also read UART1 configuration/status, never FIFO or writes')
args = parser.parse_args()
mode = 'uart-registers' if args.uart_registers else 'inventory'
root = Path(__file__).resolve().parents[1]
tcl = root / 'scripts/jtag_readonly.tcl'
tag = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out = root / 'evidence' / (tag + '-jtag-readonly')
out.mkdir(exist_ok=False)
status = {'evidence': str(out), 'complete': False, 'target_control_sent': False,
          'memory_accessed': False, 'pl_programmed': False,
          'requested_query': mode,
          'tcl_sha256': hashlib.sha256(tcl.read_bytes()).hexdigest()}
server = None
try:
    status['host_kernel'] = os.uname().release
    status['host_euid'] = os.geteuid()
    status['ftdi_shared_files'] = [
        {'path':str(p),'uid':p.stat().st_uid,'mode':oct(p.stat().st_mode & 0o777)}
        for p in Path('/dev/shm').glob('*') if 'digilent' in p.name.lower() or 'ftdi' in p.name.lower()]
    print(json.dumps({'host_kernel':status['host_kernel'],
                      'ftdi_shared_file_count':len(status['ftdi_shared_files'])}),flush=True)
    usb=[]
    for device in Path('/sys/bus/usb/devices').iterdir():
        try:
            if (device/'serial').read_text().strip() != 'XFL1EMEBC1R5':
                continue
            bus=int((device/'busnum').read_text());number=int((device/'devnum').read_text())
            node=Path('/dev/bus/usb') / f'{bus:03d}' / f'{number:03d}'
            st=node.stat()
            usb.append({'node':str(node),'mode':oct(st.st_mode & 0o777),
                        'uid':st.st_uid,'gid':st.st_gid,
                        'read_write_access':os.access(node,os.R_OK|os.W_OK)})
        except OSError:
            continue
    status['host_usb']=usb
    print(json.dumps({'host_usb':usb}),flush=True)
    with socket.socket() as check:
        check.bind(('127.0.0.1', 0))
        port = check.getsockname()[1]
        status['localhost_port'] = port
    with (out / 'hw-server.output').open('wb') as server_log:
        command = [
            '/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin/hw_server',
            f'-sTCP:127.0.0.1:{port}', '-p0', '-L-', '-l', 'discovery,jtag']
        if shutil.which('strace'):
            command = ['strace','-f','-o',str(out/'hw-server.strace'),'-e',
                       'trace=openat,mmap,ftruncate,close'] + command
        server = subprocess.Popen(command, stdout=server_log,
                                  stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + 10
        while True:
            if server.poll() is not None:
                raise RuntimeError('Temporary hardware server exited')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=.2):
                    break
            except OSError:
                if time.monotonic() > deadline:
                    raise RuntimeError('Temporary hardware server not ready')
                time.sleep(.2)
        completed = subprocess.run([
            '/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin/xsct', '-nodisp', str(tcl), str(port), mode],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
        (out / 'xsct.output').write_bytes(completed.stdout)
        status['returncode'] = completed.returncode
        status['output_sha256'] = hashlib.sha256(completed.stdout).hexdigest()
        text = completed.stdout.decode(errors='replace')
        print(text, flush=True)
        if completed.returncode != 0 or 'AURA_JTAG_TARGETS_END' not in text:
            raise RuntimeError('XSCT target query failed; see xsct.output and hw-server.output')
        status['processor_targets_text'] = text.split('AURA_PROCESSOR_TARGETS_BEGIN', 1)[1].split('AURA_PROCESSOR_TARGETS_END', 1)[0].strip()
        status['jtag_targets_text'] = text.split('AURA_JTAG_TARGETS_BEGIN', 1)[1].split('AURA_JTAG_TARGETS_END', 1)[0].strip()
        if args.uart_registers:
            status['uart_registers_text'] = text.split('AURA_UART1_REGISTERS_BEGIN',1)[1].split('AURA_UART1_REGISTERS_END',1)[0].strip()
            status['memory_accessed'] = True
        status['complete'] = True
except Exception as exc:
    status['error'] = str(exc)
    raise
finally:
    if server is not None and server.poll() is None:
        os.killpg(server.pid,signal.SIGTERM)
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(server.pid,signal.SIGKILL)
            server.wait(timeout=5)
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    (root / 'CURRENT_JTAG.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps({k:v for k,v in status.items() if k!='ftdi_shared_files'}, indent=2), flush=True)
