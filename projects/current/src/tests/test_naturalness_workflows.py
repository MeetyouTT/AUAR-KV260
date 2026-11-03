import json
import pytest
from tools import build_naturalness_workflows as wf


def test_all_graphs_keep_reference_geometry_and_separate_transition_anchors(tmp_path):
    assert wf.main(['--outdir',str(tmp_path/'graphs')]) == 0
    paths=list((tmp_path/'graphs').glob('*_api.json'))
    assert len(paths)==21
    for path in paths:
        g=json.loads(path.read_text(encoding='utf-8'))
        assert g['7']['inputs']['length']==39
        assert (g['7']['inputs']['width'],g['7']['inputs']['height'])==(864,1536)
        assert g['8']['inputs']['steps']==8
        assert g['14']['inputs']['filename_prefix'].startswith('AURA_NATURAL_V3_')
        if 'enter_v3' in path.name or 'exit_v3' in path.name:
            assert g['7']['inputs']['last_frame']==['6',0]
            assert g['5']['inputs']['image']!=g['6']['inputs']['image']
        else:
            assert g['7']['inputs']['first_frame']==g['7']['inputs']['last_frame']
    m=json.loads((tmp_path/'graphs/workflow_manifest.json').read_text(encoding='utf-8'))
    assert m['status']=='BUILT_NOT_SUBMITTED_NOT_GENERATED'


def test_workflow_builder_refuses_existing_outputs_without_overwrite(tmp_path):
    args=['--outdir',str(tmp_path),'--only','talking_calm_rest_v3','--seeds','123']
    wf.main(args)
    before=(tmp_path/'talking_calm_rest_v3_s123_api.json').read_bytes()
    with pytest.raises(SystemExit): wf.main(args)
    assert (tmp_path/'talking_calm_rest_v3_s123_api.json').read_bytes()==before


def test_unknown_asset_cannot_create_empty_success(tmp_path):
    with pytest.raises(SystemExit): wf.main(['--outdir',str(tmp_path),'--only','does_not_exist'])
    assert not list(tmp_path.iterdir())
