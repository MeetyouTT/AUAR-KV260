import json
from PIL import Image
from tools.check_naturalness_candidate import inspect


def test_candidate_cannot_pass_without_metadata(tmp_path):
    assert inspect(tmp_path)['status']=='FAIL'


def test_candidate_gate_detects_body_jumps_and_never_claims_visual_approval(tmp_path):
    (tmp_path/'meta.json').write_text(json.dumps({'fps':24,'frames':39}),encoding='utf-8')
    for i in range(39):
        im=Image.new('RGBA',(464,480),(0,0,0,0))
        im.paste((100 if i%2 else 180,100,80,255),(100,100,300,450))
        im.save(tmp_path/('%06d.png'%i))
    assert inspect(tmp_path)['status']=='STRUCTURE_VALID_REQUIRES_VISUAL_REVIEW'
    report=inspect(tmp_path,max_body_mad=1)
    assert report['status']=='FAIL' and report['max_body_pixel_mad']>1
