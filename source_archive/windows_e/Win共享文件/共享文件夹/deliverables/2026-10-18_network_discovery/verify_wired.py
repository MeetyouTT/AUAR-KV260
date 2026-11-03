"""Verify the configured wired peer without authenticating or controlling it."""
import concurrent.futures
import json
from pathlib import Path
import socket

HERE = Path(__file__).resolve().parent
HOST = '192.168.50.1'
BOARD = '192.168.50.2'

def probe(port):
    try:
        with socket.socket() as stream:
            stream.settimeout(2)
            stream.bind((HOST, 0))
            stream.connect((BOARD, port))
            if port != 22:
                stream.sendall(b'GET /health HTTP/1.0\r\nHost: 192.168.50.2\r\n\r\n')
            reply = stream.recv(1024).decode('utf-8', 'replace')
            if port == 22:
                reply = reply.split('\r\n', 1)[0]
        return {'port': port, 'connected': True, 'reply': reply}
    except OSError as exc:
        return {'port': port, 'connected': False, 'error': str(exc)}

def main():
    configured = json.loads((HERE / 'wired_setup_result.json').read_text(encoding='utf-8-sig'))
    if configured.get('status') != 'CONFIGURED' or configured['host_ip'] != HOST:
        raise SystemExit('Expected wired address has not been configured yet')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(probe, (22, 8783, 8790)))
    report = {'host_ip': HOST, 'board_ip': BOARD, 'source_bound_to_wired_ip': True,
              'board_ping': configured.get('board_ping'), 'services': results,
              'ssh_authenticated': False, 'board_configuration_modified': False}
    (HERE / 'wired_verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))

if __name__ == '__main__':
    main()
