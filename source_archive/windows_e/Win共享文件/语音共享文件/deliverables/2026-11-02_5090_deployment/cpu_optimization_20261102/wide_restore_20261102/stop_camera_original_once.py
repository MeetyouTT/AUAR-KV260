"""Call the unchanged reviewed original helper once, with its real --stop."""
import hashlib
import sys
assert hashlib.sha256(STOP_SOURCE.encode()).hexdigest() == '4a5e374eacc825e16a22664dc6ef1137f5e0950be3dc8b3e477f791faf5e2e91'
space = {'__name__': 'original_current_owner_normal_stop', 'EXPECTED': FRESH['normal_stop_expected']}
exec(compile(STOP_SOURCE, '<unchanged-original-stop-4a5>', 'exec'), space)
sys.argv = ['original_current_owner_normal_stop', '--stop']
space['main']()
