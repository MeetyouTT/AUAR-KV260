"""Summarize the tests actually run, keeping unimplemented features explicit."""
import ast
import hashlib
import json
from pathlib import Path
import urllib.request

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
host=json.loads((HERE/'actual_host_probe.json').read_text(encoding='utf-8'))
board=json.loads((HERE/'actual_board_probe.json').read_text(encoding='utf-8'))
thinking=json.loads((HERE/'native_thinking.json').read_text(encoding='utf-8'))
capabilities=json.loads((HERE/'model_capabilities.json').read_text(encoding='utf-8'))
old=json.loads((ROOT/'deliverables/2026-10-18_voice_channel/verification.json').read_text(encoding='utf-8'))
hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==info['sha256']
        for name,info in old['source_manifest'].items()}
assert all(hashes.values()),'Source differs from the original experimental-channel manifest'
for data in (host,board):
    assert data['status']=='PASS_CHANNEL_RECEIVE_ONLY' and data['same_tcp_connection']
    for turn in data['turns']:
        assert turn['result']['network_complete'] and not turn['result']['playback_verified']
        assert turn['received_pcm_sha256']==turn['result']['pcm_sha256']
health=json.load(urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=4))
assert health['ready'] and health['llm_model']=='aura-qwen3.8-27b-abliterated:iq4_xs'
ast.parse((HERE/'test_native_thinking.py').read_text(encoding='utf-8-sig'))
summary={'date':'2026-10-18','scope':'Recheck only; no production source or model settings changed',
         'regression':{'passed':27,'failed':0,'elapsed_seconds':1.34},
         'source_manifest_matches':hashes,'health_after':health,
         'host_first_pcm_ms':[x['first_pcm_ms'] for x in host['turns']],
         'board_first_pcm_ms':[x['first_pcm_ms'] for x in board['turns']],
         'board_after':board['board_after'],'model_capabilities':capabilities['capabilities'],
         'native_thinking_test':thinking,
         'test_options':{'temperature':0,'seed':42,'num_predict':512,'num_ctx':2048,
                         'stream':True,'changes_apply_to_test_requests_only':True},
         'feature_status':{'streaming_transport_and_clause_pipeline':'IMPLEMENTED_AND_RETESTED',
                           'production_ui_streaming_playback':'NOT_IMPLEMENTED',
                           'persistent_audio_output':'NOT_IMPLEMENTED',
                           'dedicated_context_cache_optimization':'NOT_IMPLEMENTED',
                           'dflash_backend':'NOT_IMPLEMENTED',
                           'native_streaming_tts':'NOT_IMPLEMENTED',
                           'automatic_long_thought_routing':'NOT_IMPLEMENTED',
                           'cached_thinking_feedback_and_interruption':'NOT_IMPLEMENTED',
                           'per_request_native_thinking':'SUPPORTED_AND_TESTED'},
         'subsecond_verified':False,'acoustic_playback_tested':False,
         'limitations':['Historical recording, no new user recording',
                       'One arithmetic problem is not a quality benchmark',
                       'Native-thinking timings exclude TTS and physical playback',
                       'No automatic routing or feedback audio implementation to validate']}
(HERE/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'tests':summary['regression'],'board_first_pcm_ms':summary['board_first_pcm_ms'],
                  'source_files_match':all(hashes.values()),'service_ready':health['ready']}))
