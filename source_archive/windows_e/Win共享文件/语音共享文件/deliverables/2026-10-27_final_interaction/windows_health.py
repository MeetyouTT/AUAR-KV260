"""Read-only checks using each existing service's actual health protocol."""
import datetime
import json
import socket
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'aura'))
from common import frontend_wire, portrait_wire


def main():
    results = {}
    for name, port in (('asr', 8791), ('dialogue', 8792)):
        try:
            with urllib.request.urlopen('http://192.168.50.1:%d/health' % port, timeout=5) as response:
                value = json.load(response)
            results[name] = {'reachable': True, 'health': value}
        except (OSError, ValueError) as exc:
            results[name] = {'reachable': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    for name, port, wire in (('frontend', 8795, frontend_wire), ('portrait', 8796, portrait_wire)):
        try:
            with socket.create_connection(('192.168.50.1', port), timeout=3) as connection:
                wire.send(connection, {'protocol': wire.PROTOCOL, 'kind': 'health'})
                # Portrait receive takes a maximum payload size, frontend a total deadline.
                value, data = wire.receive(connection, 0 if name == 'portrait' else 3)
            assert not data
            results[name] = {'reachable': True, 'health': value}
        except (OSError, ValueError, AssertionError) as exc:
            results[name] = {'reachable': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    results['checked_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (HERE / 'windows_health_final.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    # Health dictionaries are retained in the evidence, without printing model configuration.
    print(json.dumps({name: result['reachable'] for name, result in results.items() if isinstance(result, dict)}))


if __name__ == '__main__':
    main()
