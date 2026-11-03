"""Prepare one local voice-first candidate; never deploy or access a device."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[6]
SOURCE=PROJECT/'deliverables/2026-10-31_visual_axis_maintenance/reviews/summary_retention_acceptance_20261101/local_audit/sources/tools/voice_first_recording.py'
PIN='57375530fddbcf7a8f431201bf86ba904d289828e69a82cdee81ab0324987427'
RELATIVE='tools/voice_first_recording.py'

METHODS='''    def _conversation_resume_binding(self):
        jobs = self.transcriber
        condition = getattr(jobs, 'condition', None)
        if condition is None:
            return None
        with condition:
            selection = getattr(jobs, 'conversation_selection', None)
            cid = getattr(selection, 'active', None)
            session = getattr(jobs, 'session_id', None)
            if (getattr(jobs, 'closed', True) or getattr(jobs, 'profile_selection', None) is not None
                    or getattr(jobs, 'scope_provider', None) is not None
                    or getattr(jobs, 'boot_id', None) != self.attention_gate.boot_id
                    or not isinstance(session, str) or not session
                    or not isinstance(cid, str) or len(cid) != 32
                    or any(char not in '0123456789abcdef' for char in cid)
                    or getattr(selection, 'saved', None) != cid):
                return None
            return jobs, selection, cid, session, jobs.boot_id

    @staticmethod
    def _same_resume_binding(left, right):
        return bool(left is not None and right is not None and left[0] is right[0]
                    and left[1] is right[1] and left[2:] == right[2:])

    def _select_listening_conversation(self):
        # Only an explicit continue can create this one-use RAM credential.
        # Keep the original selector, generation invalidation and grant guards.
        marker, self._pause_resume = self._pause_resume, None
        jobs = self.transcriber
        condition = getattr(jobs, 'condition', None)
        if marker is not None and condition is not None:
            with condition:
                resume = self._same_resume_binding(marker, self._conversation_resume_binding())
                jobs.select_conversation(resume=resume)
        else:
            jobs.select_conversation(resume=False)

'''

OLD_TOGGLE='''    def handsfree_toggle(self):
        result = super().handsfree_toggle()
        if self.monitor_enabled:
            self.monitor_state = self._waiting_state()
            self.monitor_reason = 'AUDIO_WAKE_WORD' if self.wake_word_required else 'DIRECT_SPEECH'
        return result
'''
NEW_TOGGLE='''    def handsfree_toggle(self):
        binding = self._conversation_resume_binding() if not self.monitor_enabled else None
        self._pause_resume = None
        result = super().handsfree_toggle()
        if self.monitor_enabled:
            self.monitor_state = self._waiting_state()
            self.monitor_reason = 'AUDIO_WAKE_WORD' if self.wake_word_required else 'DIRECT_SPEECH'
        if self.monitor_enabled and self._same_resume_binding(binding, self._conversation_resume_binding()):
            self._pause_resume = binding
        return result
'''


def main():
    before=SOURCE.read_bytes()
    assert hashlib.sha256(before).hexdigest()==PIN
    after=before.decode('utf-8')
    replacements=[
        ('        self.wake_rearm = False\n', '        self.wake_rearm = False\n        self._pause_resume = None\n'),
        ('    def _waiting_state(self):\n',METHODS+'    def _waiting_state(self):\n'),
        ('    def _finish_session(self, *args, **kwargs):\n',
         '    def _finish_session(self, *args, **kwargs):\n        self._pause_resume = None\n'),
        ('    def cancel(self):\n', '    def cancel(self):\n        self._pause_resume = None\n'),
        (OLD_TOGGLE,NEW_TOGGLE),
        ('            self.transcriber.select_conversation(resume=False)\n',
         '            self._select_listening_conversation()\n'),
    ]
    for old,new in replacements:
        if old.startswith('        self.wake_rearm'):
            assert after.count(old)>=1
        else:assert after.count(old)==1,old
        after=after.replace(old,new,1)
    after=after.encode('utf-8')
    ast.parse(after,feature_version=(3,9))
    for folder,body in [('before',before),('after',after)]:
        path=HERE/folder/RELATIVE
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():assert path.read_bytes()==body
        else:
            with path.open('xb') as stream:stream.write(body)
    patch=''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),
        fromfile='before/'+RELATIVE,tofile='after/'+RELATIVE))
    (HERE/'CHANGE.diff').write_text(patch,encoding='utf-8')
    result=dict(schema='aura.explicit-pause-resume-candidate.v1',status='LOCAL_ONLY_NOT_DEPLOYED',
        baseline_startup_sha256='22317f7933447b28a2ca535a47246de8b3869989cc0d964a13cd169cd2289311',
        relative=RELATIVE,before_sha256=PIN,after_sha256=hashlib.sha256(after).hexdigest(),
        before_bytes=len(before),after_bytes=len(after),python39_syntax_checked=True,
        production_changed=False,device_model_HTTP_or_private_database_access=False)
    (HERE/'CANDIDATE.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
