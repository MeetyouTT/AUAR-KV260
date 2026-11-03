"""Read-only source and parameter-coverage audit for freeze=0 comparisons."""
from pathlib import Path
import hashlib
import json

BASE=Path(__file__).resolve().parent.parent
CORE=BASE/'native_integration/candidate_core'
WEB=Path('D:/share、/项目开发/美冬本地女友项目/web')
model=json.loads((BASE/'inputs/ems/yuk_0.ems.json').read_text(encoding='utf8'))
parameters=json.loads((BASE/'native_integration/controlled-normal-parameters.json').read_text(encoding='utf8'))
combo=set()
motion_parameters=set()
def walk(x):
    if isinstance(x,dict):
        if 'meshCombinator' in x:
            combo.update(c['variable']['key'] for c in x['meshCombinator']['combinatorList'])
        for v in x.values():walk(v)
    elif isinstance(x,list):
        for v in x:walk(v)
walk(model)
selector={o['label'] for c in model['metadata']['selectorControl'] for o in c['optionList']}
for g in model['object'].values():
    for m in g['motion'].values():
        motion_parameters.update(p['id'] for p in m['parameter'])
extra=sorted((combo|selector|motion_parameters)-parameters.keys())
key_report={'scope':'additional direct getVariable queries; do not assume zero defaults',
    'existing_parameter_count':len(parameters),'combinator_variables':sorted(combo),
    'selector_output_variables':sorted(selector),'motion_parameter_variables':sorted(motion_parameters),
    'additional_query_keys':extra,'union_query_keys':sorted(parameters.keys()|combo|selector|motion_parameters),
    'minimum_missing_for_combinator_and_selector':sorted((combo|selector)-parameters.keys()),
    'observation_phase':'after core Step/Update, before or immediately after the corresponding Draw; not cached showState before Update'}
(BASE/'agent_audit/hidden-geometry-parameter-keys.json').write_text(
    json.dumps(key_report,ensure_ascii=False,indent=2),encoding='utf8')

def source(path,needle):
    text=path.read_text(encoding='utf8')
    line=text[:text.index(needle)].count('\n')+1
    return dict(path=str(path),line=line,symbol=needle,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())
playback=CORE/'src/runtime/playback.cpp'
animation=CORE/'src/runtime/animation.cpp'
geometry=CORE/'src/runtime/geometry_scene.cpp'
stage=WEB/'tachie/emote-stage.js'
wrapper=WEB/'vendor/freemote/emoteplayer.js'
report={
    'scope':'offline source inspection only; no production mutation, browser or board operation',
    'conclusion':'freeze=0 equality does not prove meshCombinator is unused, and its mismatch with immediate direct GeometryInstance is not yet a mesh formula failure. Native and original may be at different evaluation phases; 37 public variables also omit internal geometry drivers.',
    'received_evidence':{
        'original_controlled_vs_rebuilt_combo_freeze0':'pixel-exact equal, parent lossless export',
        'rebuilt_combo_vs_rebuilt_no_combo_freeze0':'pixel-exact equal, parent lossless export',
        'native_direct_geometry_vs_freeze0':{'reported_mae':6.245,'reported_different_pixels':47747},
        'claim_boundary':'These image comparison values were supplied by parent; not rerun here.'},
    'native_phases':[
        {'operation':'GeometryInstance::set_parameter + evaluate + build_frame',
         'behavior':'set_parameter stores and invalidates. evaluate copies inputs, clamps, samples every active frame and meshCombinator immediately. No author tick or elapsed time is required.',
         'evidence':[source(geometry,'GeometryStatus GeometryInstance::set_parameter'),source(geometry,'GeometryStatus GeometryInstance::evaluate()'),source(geometry,'!sample_combinators(n.combinators')]},
        {'operation':'PlaybackInstance::play',
         'behavior':'Animation play dispatches timeline events at time0 immediately and composes numeric output; the clip starts sampled=false. Playback then composes and dirties its final output.',
         'evidence':[source(animation,'AnimationStatus AnimationInstance::play'),source(playback,'PlaybackStatus PlaybackInstance::play')]},
        {'operation':'PlaybackInstance::transition(frames=0)',
         'behavior':'Ordinary zero-duration and Immediate requests assign immediately. Mouth and Selector controller requests can defer until an author step; selector output weights initialize/update only in update_selectors. Additive clips are excluded from composition until sampled by step.',
         'evidence':[source(animation,'bool request(const Controller&'),source(animation,'state.deferred ='),source(animation,'void update_selectors()'),source(animation,'!state.playing || !state.additive || !state.sampled')]},
        {'operation':'PlaybackInstance::prepare_frame',
         'behavior':'Uses composed output to set geometry parameters, evaluate and build; performs no animation step or physics step. A prepare at tick0 is a distinct phase from step()+prepare.',
         'evidence':[source(playback,'PlaybackStatus PlaybackInstance::prepare_frame()')]},
        {'operation':'PlaybackInstance::step',
         'behavior':'Animation step increments timeline time, dispatches events and updates controllers/selectors/blink. Playback binds animated parameters, evaluates anchors, advances physics once if enabled, composes output, increments tick. prepare_frame evaluates final output separately.',
         'evidence':[source(animation,'AnimationStatus AnimationInstance::step()'),source(playback,'PlaybackStatus PlaybackInstance::step_tick')]},
        {'operation':'PlaybackInstance::advance(1.0)',
         'behavior':'Catch-up is clamped to .25 seconds/15 author ticks per call. For exactly1 second use60 step calls or60 advance(1/60) calls, not a single advance(1).',
         'evidence':[source(playback,'constexpr std::uint32_t kMaximumCatchUpTicks = 15'),source(playback,'PlaybackStatus PlaybackInstance::advance')]}],
    'source_wrapper_phases':[
        {'operation':'freeze setup',
         'behavior':'applyPose/main timeline and expressions run; explicit EmotePlayer_Update(playerId, freezeSeconds*60) runs once, then stepUpdate=true marks modified. freeze0 therefore initially passes Update(0), freeze1/60 passes Update(1).',
         'evidence':[source(stage,'applyPose();\n    applyExpression();'),source(stage,'if (state.freeze) EmotePlayer_Update(player.playerId, state.time * 60);')]},
        {'operation':'first frozen render',
         'behavior':'onUpdate precedes core evaluation. With stepUpdate && modified, wrapper calls EmotePlayer_Step then Update(0), clears modified, then DrawToTexture2. Thus freeze0 is not literally an absence of core calls; Step/Update0 is nevertheless not evidence of a positive-time Update.',
         'evidence':[source(wrapper,'player.onUpdate();'),source(wrapper,'if (player.stepUpdate) {'),source(wrapper,'EmotePlayer_DrawToTexture2(player.playerId')]},
        {'operation':'current DOM parameters instrumentation',
         'behavior':'reference_server injects parameter queries into showState. showState is called by onUpdate before wrapper Step/Update/Draw. Cached DOM values can therefore describe the preceding update phase; capture queries should be after the matching core update.',
         'evidence':[source(stage,'function showState()'),source(stage,'function update()')]}],
    'parameter_coverage':key_report,
    'recommended_discriminating_observations':[
        'Keep separate fresh instances for combo/no_combo at freeze0, positive1 author frame, and60 frames. Export lossless pixels and post-update full variable union for each image.',
        'Compare combo/no_combo first, then compare native direct Geometry using the complete same post-update values. Preserve projection, dimensions, texture and the existing diagnostic disable flags.',
        'Record bulk Update(60) separately from60 successive Update(1) calls; they need not be equivalent when internal update phases/controllers are involved.',
        'Do not derive physics correctness from controlled models whose physical controllers are disabled; production native playback physics remains enabled.',
        'If positive-time combo/no_combo still equal, further isolated original-engine evidence is needed before declaring fields unused; do not silently remove the candidate combinators.'
    ],
    'no_runtime_claim':True,'production_changed':False,'browser_used':False,'board_connected':False}
(BASE/'agent_audit/initial_pose_update_audit.json').write_text(
    json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'extra_query_keys':extra,'union_count':len(key_report['union_query_keys']),
                  'reports':['hidden-geometry-parameter-keys.json','initial_pose_update_audit.json']},ensure_ascii=True))
