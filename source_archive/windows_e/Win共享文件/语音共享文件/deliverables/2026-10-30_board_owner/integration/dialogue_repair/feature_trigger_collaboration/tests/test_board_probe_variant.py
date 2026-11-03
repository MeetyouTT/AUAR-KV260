"""Focused BOARD worker protocol checks; all transports/native state are fake."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

HERE=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('fail_fourth',[False,True])
def test_board_probe_uses_real_compact_contract_and_preserves_safe_partial_evidence(tmp_path,monkeypatch,fail_fourth):
    import board.runtime.board_dialogue_client as transport
    from common.model_inference_wire import Owner,make_response,validate_request,WireError
    specification=importlib.util.spec_from_file_location('board_public_probe_v2',HERE/'public_board_probe_v2/worker.py')
    worker=importlib.util.module_from_spec(specification);specification.loader.exec_module(worker)
    class Client:
        def __init__(self,*args):self.calls=0;self.cancels=0
        def health_date_source_id(self):return 'public-test-source'
        def validate_sample(self,*args):return True
        def sample_health_date(self,clock,**kwargs):
            assert clock.boot_id=='public-test-boot'
        def output_format_capabilities(self):
            return {'format_contract_version':1,'output_formats':['json','dialogue_abc_v1']}
        def request(self,kind,payload,**kwargs):
            checked=validate_request(kind,payload)
            assert checked['options']['output_format']=='dialogue_abc_v1'
            self.calls+=1
            if fail_fourth and self.calls==4:raise WireError('owner_mismatch')
            return make_response(Owner.from_dict(checked),result={'text':json.dumps(
                {'a':'目前没有可核验的结果，不能确认。','b':'neutral','c':''})})
        def cancel(self,owner):
            self.cancels+=1
            if fail_fourth and self.cancels==4:return make_response(owner,error='backend_failed')
            return make_response(owner,result={'cancelled':False,'state':'completed'})
    client=Client()
    monkeypatch.setattr(transport,'InferenceHttpClient',lambda *args:client)
    monkeypatch.setattr(worker,'verify_sources',lambda *args:dict(runtime_sources=339,
        utc_bounds=[1793300000.,1793600000.]))
    class Boot:
        def is_file(self):return True
        def read_text(self):return 'public-test-boot\n'
    monkeypatch.setattr(worker,'Path',lambda p:Boot() if str(p)=='/proc/sys/kernel/random/boot_id' else Path(p))
    monkeypatch.setattr(worker,'HERE',tmp_path)
    monkeypatch.setattr(sys,'platform','linux')
    destination=tmp_path/'public-board.json'
    monkeypatch.setattr(sys,'argv',['worker','--coordinated-slot','public-fake-slot',
        '--runtime-root',str(HERE/'runtime_v16'),'--startup-config',str(tmp_path/'metadata-only-config'),
        '--output',str(destination)])
    if fail_fourth:
        with pytest.raises(SystemExit) as error:worker.main()
        assert error.value.code==1
    else:
        worker.main()
    result=json.loads(destination.read_text(encoding='utf-8'))
    assert len(result['cases'])==4
    assert result['execution_host']=='board' and not result['private_data_accessed']
    assert [r['status'] for r in result['cases'][:3]]==['completed']*3
    if fail_fourth:
        assert result['cases'][3]['failure_stage']=='inference_rpc'
        assert result['cases'][3]['failure_code']=='owner_mismatch'
        assert result['cases'][3]['cleanup_error_code']=='backend_failed'
        assert result['cases'][3]['cleanup_failure_stage']=='validate_cancel_response'
    else:
        assert result['status']=='PUBLIC_REPLIES_REQUIRE_ROOT_REVIEW'
        assert all(r['owner_cleanup_state']=='completed' for r in result['cases'])
