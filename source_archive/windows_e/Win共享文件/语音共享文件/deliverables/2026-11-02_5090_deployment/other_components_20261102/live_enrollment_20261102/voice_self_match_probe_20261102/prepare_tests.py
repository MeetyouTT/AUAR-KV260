"""Reuse actual formal/Yuki/worker synthetic composition and old 66/24 contracts."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'voice_entry_name_fix_20261102'
text=(OLD/'composition.py').read_text(encoding='utf-8')
needle="PINS['tools/formal_yuki.py']='c74b5f00d52208d992e8ee82c998250001c781c900d31b1f72a18bdda6f492e9'"
assert text.count(needle)==1
text=text.replace(needle,needle+"\nPINS['board/runtime/board_speaker_business.py']=('f82bc71d00c355c164d43ca0b6a853ea6a32e67c84ffd228791d7070209b907e' if MODE=='candidate' else '6904267bd016a10a1508b26f372f0db54a71d78eed2eb15b043026218b1b7816')")
# The old grammar is the baseline of this single-worker patch in both variants.
text=text.replace("PINS=dict(BASE_PINS,**(CANDIDATE_PINS if MODE=='candidate' else {}))","PINS=dict(BASE_PINS,**CANDIDATE_PINS)")
text=text.replace("    def event_time(self):return 1000.","    def event_time(self):return 1000.+self.mono()")
text=text.replace("        monkeypatch.setitem(sys.modules,'webrtcvad',SimpleNamespace(Vad=Vad))",
 "        self.timeline.mono=self.mono\n        self.last_meta=None;self.last_raw=None;self.last_events=[]\n        monkeypatch.setitem(sys.modules,'webrtcvad',SimpleNamespace(Vad=Vad))")
text=text.replace('        meta=self.runtime.jobs.submit(clip)','        meta=self.runtime.jobs.submit(clip)\n        self.last_meta=meta;self.last_raw=raw;self.last_events=[]')
text=text.replace("            if 'error' in event:errors.append(event['error'])","            self.last_events.append(event)\n            if 'error' in event:errors.append(event['error'])")
(HERE/'composition.py').write_text(text,encoding='utf-8')
(HERE/'BASE_PINS.json').write_bytes((OLD/'BASE_PINS.json').read_bytes())
for name in ('test_yuki_voice_entry.py','test_original_voice_contract.py'):
 (HERE/name).write_bytes((OLD/name).read_bytes())
print('Actual Yuki composition and unchanged66/24 tests prepared')
