"""Classify retained local text in board RAM. Export shape flags only."""
import hashlib
import http.client
import json
from pathlib import Path
import re
import sys

root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
raw=(root/'startup/config.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='735bf3867e748129319ef191c2069dfc2951640e2da64825fc02b28ee013ec13'
startup=json.loads(raw);aura=Path(startup['runtime'])/'aura'
for p in ('common/binding_intent.py','common/feature_intents.py','common/spoken_input.py','common/character_profile.py'):
    assert hashlib.sha256((aura/p).read_bytes()).hexdigest()==startup['component_sha256'][p]
sys.path.insert(0,str(aura))
from common.binding_intent import binding_intent
from common.feature_intents import speaker_text
from common.spoken_input import prepare_spoken_input
from common.character_profile import strip_character_address
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
try:
    c.request('GET','/api/state');r=c.getresponse();data=r.read(2097153)
    assert r.status==200 and len(data)<=2097152
    v=json.loads(data)
finally:c.close()
t=v.get('local_transcription') or {}
candidates={'local_transcription.text':t.get('text'),'local_transcription.transcript':t.get('transcript')}
result=[]
for path,value in candidates.items():
    row={'static_path':path,'nonempty_text_available':type(value) is str and bool(value)}
    if type(value) is str and value:
        norm=strip_character_address(prepare_spoken_input(value)['text'].strip(' \t\r\n。！!？?')).strip(' \t\r\n，,。！!？?')
        intent=binding_intent(value); kind=intent.get('kind')
        row.update(characters=min(4097,len(value)),kind=kind if kind in ('ordinary','remember_self','name_hint','invalid_name','face_only','voice_only') else 'other',
            speaker_canonical=bool(speaker_text(value)),normalized_changed=value!=norm,
            starts_register_voice=bool(re.match(r'^(?:请)?(?:帮我)?(?:登记|注册)(?:我的)?声纹',norm)),
            starts_my_name=norm.startswith('我叫'),has_register='登记' in norm,has_voiceprint='声纹' in norm,has_my_name='我叫' in norm,
            contains_whitespace=bool(re.search(r'\s',norm)),contains_colon=bool(re.search(r'[:：]',norm)),
            contains_quotes=bool(re.search(r'[“”‘’\x22\x27]',norm)),contains_internal_period='。' in norm,
            leading_punctuation=bool(norm and norm[0] in '，,:：。'),trailing_comma=norm.endswith(('，',',')),
            explicit_i_want_prefix=norm.startswith(('我要','我想')),entry_name_valid=intent.get('name') is not None)
    result.append(row)
print(json.dumps({'source':'original_retained_API_text_only','shape':result,'raw_text_or_name_exported':False,'board_mutations':False}))
