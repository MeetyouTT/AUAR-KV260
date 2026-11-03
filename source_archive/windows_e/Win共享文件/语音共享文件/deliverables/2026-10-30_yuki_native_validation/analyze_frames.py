from pathlib import Path
import hashlib
import json
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parent
CAPTURES = ROOT / 'evidence/candidate-captures'


def compare(first, second):
    x = np.asarray(Image.open(str(first)).convert('RGB')).astype(np.int16)
    y = np.asarray(Image.open(str(second)).convert('RGB')).astype(np.int16)
    assert x.shape == y.shape
    difference = np.abs(x-y)
    background = np.array([252,252,243])
    foreground = np.logical_or(np.max(np.abs(x-background),axis=2)>12,
                               np.max(np.abs(y-background),axis=2)>12)
    return {'mean_absolute_rgb':float(difference.mean()),
            'foreground_mean_absolute_rgb':float(difference[foreground].mean()),
            'changed_pixels_over_5':int((difference.max(axis=2)>5).sum()),
            'foreground_pixels':int(foreground.sum()),
            'rgb_sha_equal':hashlib.sha256(x.tobytes()).digest()==hashlib.sha256(y.tobytes()).digest()}


pairs = {
    'candidate_idle_0_to_60':(CAPTURES/'idle_0-0000.png',CAPTURES/'idle_0-0060.png'),
    'reference_idle_0_to_60':(ROOT/'reference-normal-t0.png',ROOT/'reference-normal-t60.png'),
    'candidate_idle_0_to_156':(CAPTURES/'idle_0-0000.png',CAPTURES/'idle_0-0156.png'),
    'candidate_idle_0_to_360':(CAPTURES/'idle_0-0000.png',CAPTURES/'idle_0-0360.png'),
    'normal_reference_vs_candidate':(ROOT/'reference-normal-t0.png',CAPTURES/'idle_0-0000.png'),
    'shy_reference_vs_candidate':(ROOT/'reference-shy-t0.png',CAPTURES/'face_controls-0281.png')}
pairs.update({
    'matched_normal_reference_vs_candidate':(ROOT/'reference-normal-matched.png',ROOT/'evidence/static-reference-captures/matched_normal-0000.png'),
    'matched_shy_reference_vs_candidate':(ROOT/'reference-shy-matched.png',ROOT/'evidence/static-reference-captures/matched_shy-0000.png'),
    'native_parameter_zero_vs_authored_start':(CAPTURES/'idle_0-0000.png',ROOT/'evidence/static-reference-captures/matched_normal-0000.png')})
report = {'pixel_equivalence_certified':False,
          'reference_and_native_physics_advance_not_identical':True,
          'pairs':{name:compare(*paths) for name,paths in pairs.items()}}
(ROOT/'image-comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
frames = json.loads((ROOT/'evidence/candidate-frames.json').read_text(encoding='utf-8'))
summary = []
for scenario in frames['scenarios']:
    snapshots = scenario['snapshots']
    base = np.array(snapshots[0]['frame']['vertices'],dtype=float)
    entry = {'name':scenario['name'],'snapshots':len(snapshots),
             'tick_count':scenario['config']['ticks'],'first_vertices':len(base),
             'vertex_max_delta':[]}
    for shot in snapshots:
        vertices = np.array(shot['frame']['vertices'],dtype=float)
        delta = float(np.abs(vertices[:,:2]-base[:,:2]).max()) if base.shape==vertices.shape else None
        entry['vertex_max_delta'].append({'tick':shot['tick'],'max_xy_delta_from_first':delta,
                                          'body_UD':shot['parameters'].get('body_UD'),
                                          'head_slant':shot['parameters'].get('head_slant')})
    summary.append(entry)
(ROOT/'frame-motion-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
static = json.loads((ROOT/'evidence/static-reference-frames.json').read_text(encoding='utf-8'))
matching = []
for case in static['scenarios']:
    expression = case['name'].removeprefix('matched_')
    requested = json.loads(json.loads((ROOT/f'reference-{expression}-state.json').read_text(encoding='utf-8'))['state']['parameters'])
    actual = case['snapshots'][0]['parameters']
    mismatch = {k:{'requested':v,'actual':actual.get(k)} for k,v in requested.items()
                if k not in actual or abs(actual[k]-v)>1e-5}
    matching.append({'expression':expression,'parameters_checked':len(requested),'mismatches':mismatch})
first = frames['scenarios'][0]['snapshots'][0]
matched = static['scenarios'][0]['snapshots'][0]
changed = {k:[first['parameters'].get(k),v] for k,v in matched['parameters'].items()
           if abs(first['parameters'].get(k,0)-v)>1e-5}
native_v0 = np.array(first['frame']['vertices'],dtype=float)
native_v1 = np.array(matched['frame']['vertices'],dtype=float)
responsiveness = {'changed_parameters':changed,'vertex_counts':[len(native_v0),len(native_v1)],
                  'maximum_vertex_xy_change':float(np.abs(native_v0[:,:2]-native_v1[:,:2]).max()) if native_v0.shape==native_v1.shape else None,
                  'same_parameter_snapshots':matching,
                  'original_physics_internal_state_equivalence_certified':False}
(ROOT/'static-parameter-comparison.json').write_text(json.dumps(responsiveness,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
print(json.dumps(responsiveness,indent=2))
