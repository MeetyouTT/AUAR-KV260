"""Opt-in loopback control wrapper. Never serves images, features or names."""
import ipaddress
import json
import secrets

PATH = '/v1/ui/sface-calibration'


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


def _invalid_constant(_):
    raise ValueError('Non-finite JSON value')


def wrap_handler(original, state):
    class CalibrationHandler(original):
        def do_POST(self):
            if self.path != PATH:
                return super().do_POST()
            try:
                if not ipaddress.ip_address(self.client_address[0]).is_loopback:
                    self.respond(403, {'error': 'Calibration control is loopback only'})
                    return
            except ValueError:
                self.respond(403, {'error': 'Calibration control is loopback only'})
                return
            with state.lock:
                service = state.identity
                extractor = getattr(service, 'extractor', None)
                controller = getattr(extractor, 'calibration', None)
                config = (getattr(extractor, 'config', {}) or {}).get('dpu_sface_calibration') or {}
                capability = config.get('control_token', '')
                if not controller or config.get('enabled') is not True:
                    self.respond(404, {'error': 'Calibration control disabled'})
                    return
            supplied = self.headers.get_all('Authorization') or []
            if (len(supplied) != 1 or not isinstance(capability, str) or len(capability) != 64
                    or not secrets.compare_digest(supplied[0], 'Bearer '+capability)):
                self.respond(403, {'error': 'Calibration capability required'})
                return
            try:
                lengths = self.headers.get_all('Content-Length') or []
                if (len(lengths) != 1 or self.headers.get('Transfer-Encoding')
                        or self.headers.get('Content-Type', '').split(';')[0] != 'application/json'):
                    raise ValueError('Bounded JSON request required')
                size = int(lengths[0])
                if not 0 < size <= 4096: raise ValueError('Request too large or empty')
                previous_timeout = self.connection.gettimeout()
                try:
                    self.connection.settimeout(2.)
                    raw = self.rfile.read(size)
                finally:
                    self.connection.settimeout(previous_timeout)
                if len(raw) != size: raise ValueError('Incomplete request')
                command = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
                if (not isinstance(command, dict) or set(command) != {'action', 'params'}
                        or not isinstance(command['action'], str)):
                    raise ValueError('Exact action and params required')
                if command['action'] == 'start':
                    # Target and start are atomic relative to camera state. No
                    # stats calculation or DPU work happens under this lock.
                    with state.lock:
                        if (state.identity is not service or getattr(service, 'extractor', None) is not extractor
                                or not getattr(getattr(extractor, 'shadow', None), 'ready', False)):
                            raise ValueError('Calibration DPU worker not ready')
                        result = controller.dispatch('start', command['params'], current_target=state.identity_target())
                else:
                    with state.lock:
                        controller.observe_target(state.identity_target())
                    # Reports take their own bounded RAM snapshot. Camera state
                    # stays unlocked during score aggregation/search.
                    result = controller.dispatch(command['action'], command['params'])
                self.respond(200, result)
            except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
                self.respond(400, {'error': 'Invalid calibration control or insufficient coverage'})
            except (OSError, TimeoutError):
                self.respond(400, {'error': 'Incomplete bounded calibration request'})
    return CalibrationHandler
