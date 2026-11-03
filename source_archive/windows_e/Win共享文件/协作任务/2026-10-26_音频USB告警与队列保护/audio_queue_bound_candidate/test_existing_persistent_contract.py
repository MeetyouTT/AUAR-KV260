"""Re-run the seven existing content contracts with an available queue API."""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

TREE=Path('/home/ghmd/Win共享文件/语音共享文件/aura')
sys.path.insert(0,str(TREE))
from tests.framework import test_persistent_audio as legacy

spec=importlib.util.spec_from_file_location('candidate_engine_contract',Path(__file__).with_name('gstreamer_persistent_engine.py'))
candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)


class DrainingCandidate(candidate.PersistentGstAudioEngine):
    def __init__(self,*args,pipeline_factory,**kwargs):
        def draining_factory(*a,**kw):
            pipeline,source,sink=pipeline_factory(*a,**kw)
            # The old fixture already models immediate downstream consume;
            # supply the documented property instead of bypassing validation.
            source.get_property=lambda name:0
            return pipeline,source,sink
        super().__init__(*args,pipeline_factory=draining_factory,**kwargs)


class ExistingPersistentContract(legacy.PersistentTests):
    def setUp(self):
        with patch.object(legacy,'PersistentGstAudioEngine',DrainingCandidate):
            super().setUp()
