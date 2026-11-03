"""Observe SSH TCP headers and routes; never capture payloads or change routing."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import time

ROOT = Path(__file__).resolve().parent
HOST = '172.23.242.132'


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write_json(path,value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    os.replace(str(temporary),str(path))


def run(args):
    result = subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
    return dict(exit_code=result.returncode,output=result.stdout.strip())


def route_snapshot():
    return dict(rules=run(['ip','-4','rule','show']),
                windows_return_route=run(['ip','-4','route','get','10.148.20.87','from',HOST]),
                ssh_connections=run(['ss','-tn','sport = :22']),
                reverse_path_filter={name:Path('/proc/sys/net/ipv4/conf',name,'rp_filter').read_text().strip()
                                     for name in ('all','wlp0s20f3')})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds',type=int,default=180)
    args = parser.parse_args()
    assert 30 <= args.seconds <= 300
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    directory = ROOT/'network-runs'/stamp
    directory.mkdir(parents=True,exist_ok=False)
    state = dict(schema_version=1,status='STARTING',host=HOST,ssh_port=22,
                 requested_duration_seconds=args.seconds,requested_utc=utc(),
                 output_directory=str(directory),packets=[],payload_recorded=False,
                 routes_modified=False,board_contacted=False,window_attempt_overlap_confirmed=False,
                 before=route_snapshot())
    write_json(directory/'state.json',state)
    write_json(ROOT/'ubuntu-tcp22-observation-latest.json',state)
    expression = '((tcp port 22) and host '+HOST+') or (icmp and host '+HOST+')'
    command = ['pkexec','--disable-internal-agent','/usr/bin/timeout',str(args.seconds),
               '/usr/sbin/tcpdump','-nn','-tttt','-l','-i','any','-s','96',expression]
    state['capture_filter'] = expression
    process = subprocess.Popen(command,stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,bufsize=0)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout,selectors.EVENT_READ)
    last_write = time.monotonic()
    lines = []
    pending = b''
    packet = re.compile(r'IP (\d+\.\d+\.\d+\.\d+)\.(\d+) > (\d+\.\d+\.\d+\.\d+)\.(\d+): Flags \[([^]]+)\]')
    with (directory/'tcp-headers.log').open('w') as log:
        while True:
            events = selector.select(timeout=1)
            for key,_ in events:
                chunk = os.read(key.fileobj.fileno(),65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                pending += chunk
                while b'\n' in pending:
                    raw,pending = pending.split(b'\n',1)
                    line = raw.decode(errors='replace')+'\n'
                    log.write(line)
                    log.flush()
                    lines.append(line.rstrip())
                    if 'listening on ' in line:
                        state.update(status='CAPTURING',capture_started_utc=utc())
                        print(json.dumps(dict(status='CAPTURING',started_utc=state['capture_started_utc'],
                                              seconds=args.seconds,output_directory=str(directory))),flush=True)
                    match = packet.search(line)
                    if match:
                        source,source_port,target,target_port,flags = match.groups()
                        direction = ('IN' if target==HOST and target_port=='22'
                                     else 'OUT' if source==HOST and source_port=='22' else 'OTHER')
                        # tcpdump prints the host's local wall clock. Preserve it
                        # and map it explicitly to UTC for Windows correlation.
                        try:
                            packet_utc = datetime.datetime.strptime(line[:26],'%Y-%m-%d %H:%M:%S.%f').astimezone(datetime.timezone.utc).isoformat()
                        except ValueError:
                            packet_utc = None
                        state['packets'].append(dict(observed_utc=utc(),packet_utc=packet_utc,
                            direction=direction,source=source,source_port=int(source_port),
                            target=target,target_port=int(target_port),flags=flags,header=line.rstrip()))
            if time.monotonic()-last_write >= 2:
                write_json(directory/'state.json',state)
                write_json(ROOT/'ubuntu-tcp22-observation-latest.json',state)
                last_write = time.monotonic()
            if process.poll() is not None and not selector.get_map():
                break
    code = process.wait()
    state.update(status='OBSERVED' if code in (0,124) and 'capture_started_utc' in state else 'CAPTURE_FAILED',
                 capture_exit_code=code,finished_utc=utc(),after=route_snapshot(),
                 packet_count=len(state['packets']),diagnostics=lines[-5:])
    state['inbound_syn_count'] = sum(p['direction']=='IN' and p['flags']=='S' for p in state['packets'])
    state['outbound_syn_ack_count'] = sum(p['direction']=='OUT' and p['flags']=='S.' for p in state['packets'])
    state['inbound_ack_count'] = sum(p['direction']=='IN' and p['flags']=='.' for p in state['packets'])
    state['outbound_rst_count'] = sum(p['direction']=='OUT' and 'R' in p['flags'] for p in state['packets'])
    if not state['inbound_syn_count']:
        state['interpretation'] = 'No inbound SSH SYN observed. Correlate with a timestamped Windows attempt before attributing the loss to a path segment.'
    elif state['outbound_syn_ack_count'] and not state['inbound_ack_count']:
        state['interpretation'] = 'Ubuntu received SYN and emitted SYN-ACK; client ACK was not observed. Compare Windows capture and return path.'
    elif state['inbound_ack_count']:
        state['interpretation'] = 'ACK traffic observed; correlate per client source port to distinguish completed handshakes from unrelated traffic.'
    else:
        state['interpretation'] = 'Inbound SSH packets observed; inspect response flags and kernel path for the same tuple.'
    write_json(directory/'state.json',state)
    write_json(ROOT/'ubuntu-tcp22-observation-latest.json',state)
    print(json.dumps({key:state[key] for key in ('status','finished_utc','packet_count',
                     'inbound_syn_count','outbound_syn_ack_count','inbound_ack_count',
                     'interpretation','output_directory')},ensure_ascii=False),flush=True)


if __name__ == '__main__':
    main()
