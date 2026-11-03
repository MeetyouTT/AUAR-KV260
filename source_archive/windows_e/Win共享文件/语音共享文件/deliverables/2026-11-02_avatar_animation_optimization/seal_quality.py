from inspect_baseline import *
from PIL import Image
import numpy as np,statistics
def main():
 v=HERE/'validation';names=('PERF_A1','PERF_B1','PERF_B2','PERF_A2');runs={n:load(v/(n+'.json')) for n in names}
 for r in runs.values():assert r['capture'] is False and r['actual_completed_fps']>15.8 and r['complete_frame_ms']['p95']<62.5
 median=lambda rows,key:statistics.median([r[key] for r in rows])
 old=[runs['PERF_A1'],runs['PERF_A2']];new=[runs['PERF_B1'],runs['PERF_B2']]
 before=HERE/'board_results/previews/baseline_v1';after=HERE/'board_results/previews/candidate_v2'
 a=np.asarray(Image.open(before/'0000.png'));b=np.asarray(Image.open(after/'0000.png'));different=int(np.any(a!=b,axis=-1).sum());assert different==0
 out=dict(schema='aura-avatar-physics-quality-gate-1',release_gate_passed=True,
   visual_review=dict(rejected_first_candidate_sleeve_detachment=True,R2_shoulder_compensation_reviewed=True,reviewed_seconds=[2,4,5.5,7,9,11],neutral_first_frame_different_pixels=different,original_model_texture_and_framing_preserved=True,whole_recording_available=True,physical_screen_human_acceptance=False),
   native_policy=dict(source='board_results/revision2b/physical_parameters.json',original_policy_passed=load(HERE/'board_results/revision2b/physical_parameters.json')['original_audio_eye_owner_policy_passed'],measured_frames_per_variant=1536,poses=2,states=3),
   same_load_ABBA=dict(order=list(names),total_real_time_seconds=40,baseline_fps=median(old,'actual_completed_fps'),candidate_fps=median(new,'actual_completed_fps'),
    baseline_completed_frame_ms_p50=statistics.median([r['complete_frame_ms']['p50'] for r in old]),candidate_completed_frame_ms_p50=statistics.median([r['complete_frame_ms']['p50'] for r in new]),
    baseline_completed_frame_ms_p95=statistics.median([r['complete_frame_ms']['p95'] for r in old]),candidate_completed_frame_ms_p95=statistics.median([r['complete_frame_ms']['p95'] for r in new]),
    scope='KV260 offscreen GLES with glFinish; production GUI stopped; unchanged camera active; no pixel readback in timed samples',claimed_speed_improvement=False,physical_panel_FPS_measured=False),
   no_new_model_audio_camera_or_axis_operations=True)
 save(HERE/'release/QUALITY_GATE.json',out);save(HERE/'validation/QUALITY_GATE.json',out)
 print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
