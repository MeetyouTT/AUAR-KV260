"""Read-only board preflight; no capture, names, transcripts or identity vectors."""
import json
import shutil
import urllib.request

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8783/api/state',timeout=3) as response:
    state = json.load(response)
recording = state.get('local_recording',{})
result = {'scope':'READ_ONLY_NO_MICROPHONE_OPENED',
          'phase':state.get('phase'),'playing':state.get('playing'), 'paused':state.get('paused'),
          'local_recording_state':recording.get('state'), 'arecord_available':bool(shutil.which('arecord'))}
result['handsfree']={key:state.get('handsfree_dialogue',{}).get(key)
                     for key in ('enabled','state','microphone_open','conversation_entered')}
print(json.dumps(result))
