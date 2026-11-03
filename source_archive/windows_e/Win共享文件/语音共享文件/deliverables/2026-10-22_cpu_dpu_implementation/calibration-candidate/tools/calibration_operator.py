"""Local scalar-only control client. Run on board; never upload biometrics.

Capability is read from an explicit private config, never an argv/env value.
Action params arrive on stdin; caller does not put session tokens in argv.
"""
import argparse
import json
from pathlib import Path
import re
import secrets
import sys
from urllib.error import HTTPError
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler, Request

READ = {'health', 'report', 'suggest', 'validation_report'}
ACTIONS = READ | {'start', 'end', 'discard', 'freeze', 'reset'}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_):
        raise ValueError('Calibration redirects refused')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Explicit CALIBRATION_ONLY local control')
    parser.add_argument('--private-config', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--action', choices=sorted(ACTIONS), required=True)
    args = parser.parse_args(argv)
    try:
        if not args.private_config.is_absolute() or not 1024 <= args.port <= 65535:
            raise ValueError('Explicit absolute config and local port required')
        value = json.loads(args.private_config.read_text(encoding='utf-8')).get('dpu_sface_calibration') or {}
        capability = value.get('control_token', '')
        if (value.get('enabled') is not True or value.get('mode') != 'CALIBRATION_ONLY'
                or not isinstance(capability, str) or not re.fullmatch(r'[0-9a-f]{64}', capability)):
            raise ValueError('Explicit enabled calibration capability required')
        raw_params = '' if args.action in READ or args.action == 'reset' else sys.stdin.read(4097)
        if len(raw_params) > 4096: raise ValueError('Input params too large')
        params = {} if not raw_params else json.loads(raw_params)
        if not isinstance(params, dict): raise ValueError('Object params required')
        if args.action not in READ:
            if 'request_id' in params: raise ValueError('Client generates a fresh request_id')
            params['request_id'] = secrets.token_hex(16)
        body = json.dumps({'action': args.action, 'params': params}, allow_nan=False).encode()
        if len(body) > 4096: raise ValueError('Bounded scalar request required')
        request = Request('http://127.0.0.1:'+str(args.port)+'/v1/ui/sface-calibration',
                          data=body, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+capability},
                          method='POST')
        with build_opener(ProxyHandler({}), NoRedirect).open(request, timeout=3) as response:
            raw = response.read(65537)
            if len(raw) > 65536: raise ValueError('Response too large')
            result = json.loads(raw)
            if not isinstance(result, dict): raise ValueError('Object response required')
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, HTTPError):
        # Do not echo config/body, request headers, URL credentials or tokens.
        print('Calibration request failed; inspect local scalar health and config.', file=sys.stderr)
        return 1


if __name__ == '__main__': raise SystemExit(main())
