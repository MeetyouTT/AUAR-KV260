"""Probe Ubuntu SSH through one IPv4 WLAN socket; leave OS routing unchanged."""
import argparse
import datetime as dt
import ipaddress
import json
import os
from pathlib import Path
import socket
import struct
import time


ROOT = Path(__file__).resolve().parent
IP_UNICAST_IF = 31


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', help='Current Ubuntu IPv4; defaults to ubuntu-registration.json')
    parser.add_argument('--interface-index', type=int, required=True)
    parser.add_argument('--source-ip', required=True)
    args = parser.parse_args()
    if os.name != 'nt' or args.interface_index <= 0:
        parser.error('A verified Windows IPv4 interface is required')
    socket.inet_pton(socket.AF_INET, args.source_ip)
    host = args.host
    if not host:
        registration = json.loads((ROOT / 'ubuntu-registration.json').read_text(encoding='utf-8-sig'))
        host = registration['host']
    address = ipaddress.IPv4Address(host)
    if address.is_loopback or address.is_unspecified or address.is_multicast:
        parser.error('Provide the current unicast Ubuntu IPv4 address')
    target_endpoint = (str(address), 22)
    report = dict(
        schema_version=1, status='CHECKING', started_utc=utc(),
        ubuntu_host=target_endpoint[0], port=target_endpoint[1],
        host_source='argument' if args.host else 'ubuntu-registration.json',
        method='IPv4 IP_UNICAST_IF plus explicit local address bind',
        interface_index=args.interface_index, source_ip=args.source_ip,
        routes_modified=False, vpn_modified=False, ssh_config_modified=False,
        authentication_attempted=False, attempts=[],
        socket_option_documentation='https://learn.microsoft.com/en-us/windows/win32/winsock/ipproto-ip-socket-options',
    )
    for index in range(3):
        attempt = dict(index=index, started_utc=utc(), connected=False, banner=None)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            try:
                attempt['stage'] = 'select_interface'
                connection.setsockopt(socket.IPPROTO_IP, IP_UNICAST_IF,
                                      struct.pack('!I', args.interface_index))
                selected = connection.getsockopt(socket.IPPROTO_IP, IP_UNICAST_IF)
                attempt['selected_interface_readback'] = selected
                if selected != args.interface_index:
                    raise RuntimeError('Outgoing interface readback mismatch')
                connection.bind((args.source_ip, 0))
                attempt['local_endpoint'] = list(connection.getsockname())
                connection.settimeout(6)
                attempt['stage'] = 'connect'
                connection.connect(target_endpoint)
                attempt['connected'] = True
                attempt['local_endpoint'] = list(connection.getsockname())
                attempt['peer_endpoint'] = list(connection.getpeername())
                attempt['stage'] = 'read_banner'
                connection.settimeout(5)
                attempt['banner'] = connection.recv(256).decode('ascii', errors='replace').strip()
                attempt['stage'] = 'complete'
            except Exception as error:
                attempt['error_type'] = type(error).__name__
                attempt['error'] = str(error)
                if getattr(error, 'winerror', None) is not None:
                    attempt['winerror'] = error.winerror
            finally:
                attempt['finished_utc'] = utc()
        report['attempts'].append(attempt)
        if index < 2:
            time.sleep(1)
    banners = sum((item.get('banner') or '').startswith('SSH-') for item in report['attempts'])
    connected = sum(item['connected'] for item in report['attempts'])
    configured = all(item.get('selected_interface_readback') == args.interface_index
                     and 'local_endpoint' in item for item in report['attempts'])
    report['status'] = ('DIRECT_SSH_BANNER_RECEIVED' if banners else
                        'DIRECT_SSH_BANNER_NOT_RECEIVED' if connected else
                        'DIRECT_TCP_CONNECT_FAILED' if configured else
                        'DIRECT_PROBE_SETUP_FAILED')
    report.update(finished_utc=utc(), connected_count=connected, ssh_banner_count=banners,
                  socket_interface_verified=configured)
    target = ROOT / 'windows-direct-tcp22-probe.json'
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, target)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
