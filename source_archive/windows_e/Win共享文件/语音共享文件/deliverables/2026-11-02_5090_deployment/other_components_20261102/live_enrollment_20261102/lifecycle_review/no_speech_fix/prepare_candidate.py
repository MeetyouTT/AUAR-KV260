"""Create review-only two-file candidate from current pinned public source."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]/'start_sync_fix/candidate_runtime'
SOURCES=json.loads((HERE.parent/'PUBLIC_SOURCE_READBACK.json').read_text(encoding='utf-8'))['sources']
names=('board/runtime/audio/board_asr.py','board/runtime/audio/board_dialogue_jobs.py')
manifest={};diff=[]
for name in names:
 raw=(BASE/name).read_bytes();before=hashlib.sha256(raw).hexdigest()
 assert before==SOURCES[name]['sha256']==SOURCES[name]['pin']
 text=raw.decode('utf-8')
 if name.endswith('board_asr.py'):
  old='class BoardAsrUnavailable(RuntimeError):\n    pass\n'
  new=old+'\n\nclass BoardNoSpeech(ValueError):\n    """The original recognizer completed without any recognized speech text."""\n    pass\n'
  assert text.count(old)==1;text=text.replace(old,new)
  old="raise ValueError('Board ASR returned no speech')";new="raise BoardNoSpeech('Board ASR returned no speech')"
  assert text.count(old)==1;text=text.replace(old,new)
 else:
  old='from board.runtime.audio.transcription import configuration\n'
  new=old+'from board.runtime.audio.board_asr import BoardNoSpeech\n'
  assert text.count(old)==1;text=text.replace(old,new)
  old="        if not isinstance(raw_text, str) or not raw_text.strip() or len(raw_text) > 4096:\n            raise ValueError('No bounded board ASR text')\n        if any(ord(c) < 32 for c in raw_text):\n            raise ValueError('ASR text cannot enter the stream protocol')\n"
  new="        if not isinstance(raw_text, str) or len(raw_text) > 4096:\n            raise ValueError('No bounded board ASR text')\n        if any(ord(c) < 32 for c in raw_text):\n            raise ValueError('ASR text cannot enter the stream protocol')\n        if not raw_text.strip():\n            raise self._entry_error()\n"
  assert text.count(old)==1;text=text.replace(old,new)
  old="            raw = self.asr.transcribe(job.pcm, sample_rate=16000, deadline=job.deadline,\n                                      cancelled=job.cancelled.is_set)\n"
  new="            try:\n                raw = self.asr.transcribe(job.pcm, sample_rate=16000, deadline=job.deadline,\n                                          cancelled=job.cancelled.is_set)\n            except BoardNoSpeech as exc:\n                self._check(job)\n                raise self._entry_error() from exc\n"
  assert text.count(old)==1;text=text.replace(old,new)
 candidate=text.encode('utf-8');target=HERE/'candidate'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(candidate)
 beforepath=HERE/'baseline'/name;beforepath.parent.mkdir(parents=True,exist_ok=True);beforepath.write_bytes(raw)
 manifest[name]={'before_sha256':before,'candidate_sha256':hashlib.sha256(candidate).hexdigest(),'before_bytes':len(raw),'after_bytes':len(candidate)}
 diff.extend(difflib.unified_diff(raw.decode('utf-8').splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(HERE/'CANDIDATE.diff').write_text(''.join(diff),encoding='utf-8',newline='\n')
(HERE/'MANIFEST.json').write_text(json.dumps({'base_startup_sha256':'9a9a709a7b2e898879bac595758f9b7ece6f2ff2e75a4c9f42ed9c38e043072a','files':manifest,'deployment_performed':False},indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest))
