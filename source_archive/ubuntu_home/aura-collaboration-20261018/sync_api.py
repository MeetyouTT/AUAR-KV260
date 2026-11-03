"""Local Verysync API helper. Configuration secrets remain in memory."""
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import subprocess
import urllib.parse
import urllib.request


def rows(value):
    return value if isinstance(value, list) else list(value.values()) if isinstance(value, dict) else []


def alias(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:10]


def utc():
    return datetime.now(timezone.utc).isoformat()


class API:
    def __init__(self):
        process = subprocess.run(['/home/ghmd/.local/opt/verysync/verysync', 'cli', 'config', 'dump-json'],
                                 capture_output=True, text=True, timeout=15)
        if process.returncode:
            raise RuntimeError('Local sync management unavailable')
        self.config = json.loads(process.stdout)
        gui = self.config.get('gui', {})
        address = gui.get('address', '127.0.0.1:8886')
        if address.startswith(':'):
            address = '127.0.0.1' + address
        host, port = address.rsplit(':', 1)
        if host in ('0.0.0.0', '::', '[::]'):
            host = '127.0.0.1'
        if not ipaddress.ip_address(host.strip('[]')).is_loopback:
            raise RuntimeError('Only the loopback management API is allowed')
        self.base = ('https' if gui.get('useTLS') else 'http') + '://' + host + ':' + port
        self.secret = gui.get('apiKey', gui.get('apikey', ''))
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def call(self, path, query=None, method='GET', data=None, timeout=12):
        if query:
            path += '?' + urllib.parse.urlencode(query, doseq=True)
        headers = {'X-API-Key': self.secret} if self.secret else {}
        payload = None
        if data is not None:
            headers['Content-Type'] = 'application/json'
            payload = json.dumps(data).encode()
        elif method != 'GET':
            payload = b''
        request = urllib.request.Request(self.base+path, data=payload, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw else {'ok': True}
        except Exception as error:
            raise RuntimeError('Local API ' + path.split('?')[0] + ' failed: ' + type(error).__name__) from None

    def folders(self):
        return [row for row in rows(self.config.get('folders', []))
                if row.get('path') == '/home/ghmd/Win共享文件']

    def identity(self, row):
        return row.get('id', row.get('ID'))

    def names(self):
        return {row.get('deviceID', row.get('deviceId')): row.get('name', '')
                for row in rows(self.config.get('devices', []))}
