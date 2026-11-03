"""Only local test helpers; product/candidate files stay read-only."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OLD=ROOT.parent/'voice_self_match_lifecycle_review_20261102'
RUNTIME=ROOT/'candidate_runtime'
EXPECTED={
 'board/runtime/board_speaker_business.py':'e229b6c3c64e75373e74d5fa136b633174ddf9897f6e95bc368899de9dc2c3d7',
 'tools/provisional_voice.py':'1ac360902f2b5790cb0b047110ef0d267940031caaaf20b91ec75c7fef1ab47c',
 'tools/yuki_business_gui.py':'6f04e9f8d7a87a8741f41f321f1c51478236be0b1cec7db7983c7b23f63764fd'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(RUNTIME/n)==pin for n,pin in EXPECTED.items())
text=(OLD/'base_composition.py').read_text(encoding='utf-8')
text=text.replace("RELEASE=HERE/'integration_runtime'","RELEASE=HERE.parent/'candidate_runtime'")
start=text.index('PINS=');end=text.index('class Mono:')
pins=dict(EXPECTED)
for name in ('common/feature_intents.py','board/runtime/board_business.py','tools/yuki_jobs_candidate.py',
 'tools/board_recording.py','tools/production_memory_presentation.py','board/runtime/history_delete.py',
 'common/anonymous_voice.py','tools/speaker_device.py','board/identity/store.py'):
 pins[name]=sha(RUNTIME/name)
text=text[:start]+'PINS='+repr(pins)+"\nassert all(hashlib.sha256((RELEASE/name).read_bytes()).hexdigest()==pin for name,pin in PINS.items())\n\n"+text[end:]
start=text.index('        self.business=BoardSpeakerBusiness.create')
end=text.index('        # Use actual current formal pair policy',start)
text=text[:start]+'''        # Only model construction and physical readback are synthetic IO.
        # The SELECTED production subclass _attach_speaker and real worker run.
        from tools import yuki_business_gui
        from board.runtime.audio import board_speaker_onnx
        self.model_constructions=[];self.readback_verifications=[]
        def encoder(directory,**kwargs):
            self.model_constructions.append(dict(kwargs))
            return self.encoder
        readback=SimpleNamespace(config={'synthetic':True},
            verify=lambda config:self.readback_verifications.append(dict(config)),read=lambda *args:None)
        monkeypatch.setattr(board_speaker_onnx,'BoardEcapaOnnxEncoder',encoder)
        monkeypatch.setattr(yuki_business_gui,'load_private_face_readback',lambda spec:readback)
        self.gui=object.__new__(yuki_business_gui.CandidateGuiBoardBusiness)
        self.gui.runtime=self.runtime;self.gui.face_readback_spec={'synthetic':True}
        self.gui._attach_speaker(dict(enabled=True,model_directory=str(path/'synthetic-unused-model'),
            manifest_sha256='0'*64,expected_model_id=self.encoder.model_id,anonymous_config={'enabled':True}),
            self.runtime.boot_id)
        self.business=self.runtime.speaker_business
        assert type(self.gui).__name__=='CandidateGuiBoardBusiness'
'''+text[end:]
(HERE/'base_composition.py').write_bytes(text.encode('utf-8'))
(HERE/'composition.py').write_text('from base_composition import *\n',encoding='utf-8')
(HERE/'recording_helpers.py').write_bytes((OLD/'test_recording_integration.py').read_bytes())
(HERE/'yuki_pair.formal.public.json').write_bytes((OLD/'yuki_pair.formal.public.json').read_bytes())
(HERE/'LOADED_SOURCE_PINS.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8')
print('Real selected CandidateGuiBoardBusiness._attach_speaker harness prepared')
