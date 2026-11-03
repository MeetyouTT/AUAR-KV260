#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Probe one Unix socket connection with an explicit protocol; never start services."""
import argparse
import datetime
import json
import socket
import time


def probe(path, kind, timeout):
    start = time.monotonic()
    result = {'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'path': path, 'socket_type': kind, 'ipc_reachable': False,
              'functional_validation': False, 'attempts': 1}
    types = {'seqpacket': socket.SOCK_SEQPACKET, 'stream': socket.SOCK_STREAM}
    try:
        with socket.socket(socket.AF_UNIX, types[kind]) as connection:
            connection.settimeout(timeout)
            connection.connect(path)
        result['ipc_reachable'] = True
    except OSError as error:
        result.update(errno=error.errno, error=str(error))
    result['elapsed_seconds'] = round(time.monotonic()-start, 6)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', required=True)
    parser.add_argument('--type', choices=['seqpacket','stream'], default='seqpacket')
    parser.add_argument('--timeout', type=float, default=2.0)
    args = parser.parse_args()
    if not 0 < args.timeout <= 30:
        parser.error('timeout must be in (0, 30]')
    result = probe(args.path, args.type, args.timeout)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['ipc_reachable'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
