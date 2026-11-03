"""Read-only bounded discovery of the wired project peer and known control host."""
import concurrent.futures
import json
from pathlib import Path
import socket
import struct
import time

HERE = Path(__file__).resolve().parent
ETHERNET = '169.254.167.87'

def resolve(name):
    try:
        return {'name': name, 'addresses': socket.gethostbyname_ex(name)[2]}
    except OSError as exc:
        return {'name': name, 'error': str(exc)}

def probe(port):
    host = '192.168.137.1'
    try:
        with socket.create_connection((host, port), 2) as stream:
            stream.settimeout(2)
            if port != 22:
                stream.sendall(('GET /health HTTP/1.0\r\nHost: ' + host + '\r\n\r\n').encode())
            data = stream.recv(512)
        return {'host': host, 'port': port, 'connected': True, 'reply': data.decode('utf-8', 'replace')}
    except OSError as exc:
        return {'host': host, 'port': port, 'connected': False, 'error': str(exc)}

def dns_name(packet, pos, visited=None):
    labels = []
    visited = set() if visited is None else visited
    end = None
    while pos < len(packet):
        size = packet[pos]
        pos += 1
        if size == 0:
            return '.'.join(labels), end or pos
        if size & 0xc0 == 0xc0:
            if pos >= len(packet):
                break
            pointer = ((size & 0x3f) << 8) | packet[pos]
            if pointer in visited:
                raise ValueError('Repeated DNS pointer')
            visited.add(pointer)
            name, _ = dns_name(packet, pointer, visited)
            labels.append(name)
            return '.'.join(labels), end or pos + 1
        if size > 63 or pos + size > len(packet):
            raise ValueError('Invalid DNS name')
        labels.append(packet[pos:pos + size].decode('utf-8', 'replace'))
        pos += size
    raise ValueError('Truncated DNS name')

def mdns():
    questions = [('ghmd-MRA-XXX.local', 1), ('kv260.local', 1),
                 ('_ssh._tcp.local', 12), ('_workstation._tcp.local', 12)]
    payload = struct.pack('!6H', 0, 0, len(questions), 0, 0, 0)
    for name, kind in questions:
        payload += b''.join(bytes([len(label)]) + label.encode() for label in name.split('.')) + b'\0'
        payload += struct.pack('!HH', kind, 1)
    rows = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as stream:
            stream.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            stream.bind(('', 5353))
            stream.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(ETHERNET))
            stream.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                              socket.inet_aton('224.0.0.251') + socket.inet_aton(ETHERNET))
            stream.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
            stream.settimeout(.5)
            stream.sendto(payload, ('224.0.0.251', 5353))
            until = time.monotonic() + 7
            while time.monotonic() < until:
                try:
                    packet, peer = stream.recvfrom(8192)
                except socket.timeout:
                    continue
                if len(packet) < 12 or not packet[2] & 0x80:
                    continue
                _, _, qd, an, ns, ar = struct.unpack_from('!6H', packet)
                pos = 12
                for _ in range(qd):
                    _, pos = dns_name(packet, pos)
                    pos += 4
                records = []
                for _ in range(min(an + ns + ar, 100)):
                    name, pos = dns_name(packet, pos)
                    kind, cls, ttl, size = struct.unpack_from('!HHIH', packet, pos)
                    pos += 10
                    value = None
                    if kind == 1 and size == 4:
                        value = socket.inet_ntoa(packet[pos:pos + 4])
                    elif kind in (5, 12):
                        value, _ = dns_name(packet, pos)
                    elif kind == 28 and size == 16:
                        value = socket.inet_ntop(socket.AF_INET6, packet[pos:pos + 16])
                    if value is not None:
                        records.append({'name': name, 'type': kind, 'value': value})
                    pos += size
                rows.append({'sender': peer[0], 'records': records})
        return {'interface_address': ETHERNET, 'responses': rows}
    except (OSError, ValueError, struct.error) as exc:
        return {'interface_address': ETHERNET, 'responses': rows, 'error': str(exc)}

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        names = [pool.submit(resolve, n) for n in ('ghmd-MRA-XXX', 'ghmd-MRA-XXX.local', 'kv260.local')]
        ports = [pool.submit(probe, p) for p in (22, 8791, 8790, 8783)]
        wire = pool.submit(mdns)
        report = {'scope': 'Read-only name/health/mDNS discovery; no login or network configuration changes',
                  'names': [f.result() for f in names], 'gateway_services': [f.result() for f in ports],
                  'wired_mdns': wire.result()}
    (HERE / 'discovery.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))

if __name__ == '__main__':
    main()
