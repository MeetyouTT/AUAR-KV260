"""Match a preserved Windows probe with a completed Ubuntu header capture."""
import datetime
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def instant(text):
    text = re.sub(r'(\.\d{6})\d+(?=Z|[+-]\d\d:\d\d|$)',r'\1',text)
    value = datetime.datetime.fromisoformat(text.replace('Z','+00:00'))
    assert value.tzinfo is not None
    return value


def endpoint(text):
    address,port = text.rsplit(':',1)
    value = ipaddress.ip_address(address.strip('[]'))
    if isinstance(value,ipaddress.IPv6Address) and value.ipv4_mapped:
        value = value.ipv4_mapped
    return str(value),int(port)


def atomic_json(path,value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    os.replace(str(temporary),str(path))


def main():
    capture = json.loads((ROOT/'ubuntu-tcp22-observation-latest.json').read_text())
    assert capture['status'] == 'OBSERVED', 'Capture must finish before the final comparison'
    directory = Path(capture['output_directory'])
    snapshot = directory/'windows-probe-correlated.json'
    raw = snapshot.read_bytes()
    windows = json.loads(raw.decode('utf-8-sig'))
    assert windows['ubuntu_host'] == capture['host'] == '172.23.242.132'
    assert windows['port'] == 22
    start,end = instant(capture['capture_started_utc']),instant(capture['finished_utc'])
    rows = []
    for attempt in windows['attempts']:
        first,last = instant(attempt['started_utc']),instant(attempt['finished_utc'])
        address,port = endpoint(attempt['local_endpoint'])
        in_window = start <= first and last <= end
        packets = [p for p in capture['packets']
                   if p['source_port'] == port or p['target_port'] == port]
        rows.append(dict(index=attempt['index'],started_utc=attempt['started_utc'],
                         finished_utc=attempt['finished_utc'],windows_source_address=address,
                         windows_source_port=port,windows_tcp_connected=attempt['connected'],
                         windows_banner=attempt.get('banner'),fully_inside_capture=in_window,
                         ubuntu_exact_port_tcp_packets=len(packets),
                         ubuntu_inbound_syn=sum(p['direction']=='IN' and 'S' in p['flags'] and '.' not in p['flags'] for p in packets),
                         ubuntu_outbound_syn_ack=sum(p['direction']=='OUT' and 'S' in p['flags'] and '.' in p['flags'] for p in packets),
                         ubuntu_exact_port_headers=[p['header'] for p in packets]))
    assert rows and all(row['fully_inside_capture'] for row in rows), 'Probe was not fully covered'
    total_tcp = len(capture['packets'])
    diagnostic = (directory/'tcp-headers.log').read_text()
    count = re.search(r'(?m)^(\d+) packets captured$',diagnostic)
    total_captured = int(count[1]) if count else None
    received = re.search(r'(?m)^(\d+) packets received by filter$',diagnostic)
    dropped = re.search(r'(?m)^(\d+) packets dropped by kernel$',diagnostic)
    icmp = [line for line in diagnostic.splitlines() if ': ICMP ' in line]
    udp_unreachable_ports = sorted(set(int(port) for line in icmp
                                      for port in re.findall(r'udp port (\d+) unreachable',line)))
    if total_tcp == 0:
        conclusion = dict(code='NO_WINDOWS_SSH_TRAFFIC_AT_UBUNTU_CAPTURE_POINT',
                          requests_reached_ubuntu_capture_point=False,
                          ubuntu_ssh_reply_observed=False,
                          ubuntu_ssh_return_path_failure_demonstrated=False,
                          scope='Three timestamp-correlated Windows attempts; all Ubuntu interfaces for the stated IPv4 SSH endpoint',
                          next_location='Windows TUN forwarding and physical-interface egress, then upstream path before Ubuntu',
                          exact_loss_hop_known=False,
                          note='Windows TCP Connected=true on 172.18.0.1 does not prove a connection to the real Ubuntu sshd; no SYN reached this capture point')
    else:
        conclusion = dict(code='TCP_TRAFFIC_OBSERVED_REVIEW_TUPLES_AND_TIMES',
                          exact_loss_hop_known=False,
                          note='Do not infer failure from missing exact source-port matches alone; TUN/NAT may rewrite source ports')
    report = dict(schema_version=1,status='CORRELATED',host=capture['host'],port=22,
                  capture_started_utc=capture['capture_started_utc'],capture_finished_utc=capture['finished_utc'],
                  capture_directory=str(directory),windows_probe_snapshot=str(snapshot),
                  windows_probe_sha256=hashlib.sha256(raw).hexdigest(),windows_route=windows['route'],
                  windows_attempt_overlap_confirmed=True,attempts=rows,
                  total_captured_packets=total_captured,total_tcp22_packets=total_tcp,
                  capture_statistics=dict(packets_received_by_filter=int(received[1]) if received else None,
                                          packets_dropped_by_kernel=int(dropped[1]) if dropped else None),
                  non_ssh_traffic=dict(icmp_records=len(icmp),udp_port_unreachable_ports=udp_unreachable_ports,
                                       note='These ICMP records are not TCP/22 requests or SSH replies'),
                  conclusion=conclusion,clock_basis='Each host reported UTC; clock settings were not changed',
                  payload_recorded=False,routes_modified=False,board_contacted=False,
                  gpu_admission_modified=False)
    atomic_json(directory/'paired-analysis.json',report)
    atomic_json(ROOT/'ubuntu-tcp22-paired-analysis.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
