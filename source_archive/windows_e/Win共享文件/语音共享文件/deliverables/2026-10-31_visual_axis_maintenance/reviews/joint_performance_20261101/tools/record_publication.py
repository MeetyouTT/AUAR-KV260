"""Record actual release and same-method comparison locally without device access."""
from pathlib import Path
import hashlib,json
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parents[1];TASK=HERE.parents[1];PROJECT=TASK.parents[1]
OWNER=PROJECT/'deliverables/2026-10-30_board_owner';CANON=OWNER/'integration/production_business_acceptance'
def read(p):return json.loads(p.read_bytes())
def raw(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def ref(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def put(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(data)
def replace(p,data):
 tmp=p.with_name(p.name+'.publication-tmp');put(tmp,data);tmp.replace(p)

def main():
 base_path=HERE/'evidence/baseline_1793532356967963000.json'
 post_path=HERE/'evidence/single_projection_post_baseline_1793533717316425200.json'
 ready_path=HERE/'evidence/single_projection_forward_ready_1793533601945768100.json'
 before=read(base_path)['result'];post=read(post_path)['result'];ready=read(ready_path)['result']
 assert post['status']=='COMPLETE' and ready['status']=='PRODUCTION_BOARD_BUSINESS_READY'
 a=before['summary'];b=post['summary']
 def measure(label,x,y):
  return dict(label=label,before=x,after=y,absolute_change=y-x,relative_change_percent=(y/x-1)*100 if x else None)
 comparisons=[measure('board_cpu_percent_median',a['board_cpu_busy_percent']['median'],b['board_cpu_busy_percent']['median']),
  measure('gtk_one_core_cpu_percent_median',a['processes']['496789']['cpu_one_core_percent']['median'],b['processes']['648047']['cpu_one_core_percent']['median']),
  measure('gtk_main_one_core_cpu_percent_median',a['threads_one_core_percent']['gtk_main']['median'],b['threads_one_core_percent']['gtk_main']['median']),
  measure('callback_cpu_ms_median',a['ui']['ui_callback_previous']['thread_cpu_ms']['median'],b['ui']['ui_callback_previous']['thread_cpu_ms']['median']),
  measure('publish_ms_median',a['ui']['ui_callback_previous']['publish_ms']['median'],b['ui']['ui_callback_previous']['publish_ms']['median']),
  measure('callback_wall_ms_p95',a['ui']['ui_callback_previous']['wall_ms']['p95'],b['ui']['ui_callback_previous']['wall_ms']['p95']),
  measure('native_presentations_per_second',a['counters']['avatar']['frames']['per_second'],b['counters']['avatar']['frames']['per_second'])]
 report=dict(schema='aura-single-projection-actual-publication-1',status='PUBLISHED_PASSIVE_POSTCHECK_COMPLETE_LIVE_PENDING',
  recorded_utc=datetime.now(timezone.utc).isoformat(),actual_ready=ref(ready_path),before=ref(base_path),after=ref(post_path),
  source_and_owner_after=post['after'],comparison=comparisons,
  sampler_body_sha256=read(post_path)['original_sampler_body_sha256'],same_sampling_body_and_method=True,
  camera_firmware_and_current_four_configurations_retained=True,only_one_source_changed=True,
  native_callback_max_ms_before_after=[a['avatar']['gtk_callback_ms']['maximum'],b['avatar']['gtk_callback_ms']['maximum']],
  native_egl_bind_max_ms_before_after=[a['avatar']['egl_bind_ms']['maximum'],b['avatar']['egl_bind_ms']['maximum']],
  visual_source_age_p95_ms_before_after=[a['camera']['observation_age_ms']['p95'],b['camera']['observation_age_ms']['p95']],
  limitations=['Uncontrolled before/after with GUI restart and possible scene changes; not a strict causal board CPU gain.',
               'Native drawing had a 101.20ms maximum including 80.03ms EGL bind; not every tail improved.',
               'Source-age P95 increased from 176ms to 194ms and maximum from 178ms to 237ms.',
               'Original observer cost retained; medians 191.4ms to 195.6ms CPU per sample.',
               'Memory and visual timeline counters are process-local and reset after GUI restart.',
               'No real speech latency has yet been measured for this new source.'])
 put(HERE/'CURRENT_PUBLICATION.json',raw(report))
 spec=(HERE/'package/single_projection/candidate_spec.json').read_bytes()
 assert (CANON/'spec.json').read_bytes()==(HERE/'package/single_projection/base_spec.json').read_bytes()
 targets=[CANON/'spec.json',CANON/'actual_ready.json',OWNER/'coordination/runtime_windows.json',HERE/'LATEST.json',PROJECT/'AGENTS.md',PROJECT/'README.md']
 archives=[]
 for p in targets:
  dest=HERE/'docs_state_publication/before'/p.relative_to(PROJECT);put(dest,p.read_bytes());archives.append(dict(original=ref(p),archive=ref(dest)))
 replace(CANON/'spec.json',spec);replace(CANON/'actual_ready.json',raw(ready))
 coord=read(targets[2]);coord['continuation_history'].append(dict(original_bytes_archive=archives[2]['archive'],previous_current_observation=coord['current_observation'],reason='Single metadata projection one-source release'))
 current=ref(HERE/'CURRENT_PUBLICATION.json');coord.update(startup_sha256=ready['startup_sha256'],source_manifest_sha256=ready['source_manifest_sha256'],
  supervisor_pid=648043,gtk_pid=648047,current_observation=current,status=report['status'],updated_utc=report['recorded_utc'],
  last_device_state=post['after']['state'],latest_joint_performance_publication=current)
 coord['operator_instruction']=dict(spec=ref(CANON/'spec.json'),publisher=str(HERE/'tools/publish_single_projection.py'),
  sole_publisher_thread='01a195e4-58a7-72d3-b141-d5d373579f7f',publication_complete=True,
  publication_expected_listening_enabled=False,usage='Current one-source release is committed; later user-authorized listening changes are runtime choices, not a source replacement.')
 coord['verified_listening']=dict(enabled=False,state='PAUSED',microphone_open=False,startup_sha256=ready['startup_sha256'],source=ref(post_path))
 coord['device_operation_owner']['state']='PASSIVE_POSTCHECK_COMPLETE_PREPARING_AUTHORIZED_LIVE'
 replace(targets[2],raw(coord))
 latest=read(HERE/'LATEST.json');latest.update(status=report['status'],current_publication=current,postcheck=ref(post_path));replace(HERE/'LATEST.json',raw(latest))
 note=f'''<!-- single-projection-current-20261101 -->
现役已完成一源状态投影优化及同方法60秒后测；真人对话测量尚未开始。startup `{ready['startup_sha256']}`、manifest `{ready['source_manifest_sha256']}`、380组件；唯一替换production_memory_presentation，当前四项相机/转轴配置、原相机430894、wide固件与v24记忆/人格/动画保留。GUI新owner为supervisor648043、GTK648047，完整birth/命令指纹见[实际发布与后测]({str(HERE/'CURRENT_PUBLICATION.json').replace(chr(92),'/')})。

后测保持main/角色可见/16fps、PAUSED/mic=false、follow=false及输出关闭。发布耗时和GTK CPU中位下降；原生绘制一次101.20ms长尾及视觉源龄波动完整保留，不宣称所有性能均改善。此前段落的startup/PID仅适用于各自保存时点；之后真人恢复聆听已获用户授权，须以新鲜状态回执为准。
<!-- /single-projection-current-20261101 -->

'''
 for p in targets[-2:]:replace(p,note.encode()+p.read_bytes())
 put(HERE/'docs_state_publication/SEAL.json',raw(dict(before=archives,after=[ref(p) for p in targets],device_access=False,current_publication=current)))
 print(json.dumps(dict(status=report['status'],current_publication=current,comparisons=comparisons),ensure_ascii=False))

if __name__=='__main__':main()
