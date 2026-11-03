"""Finish the local handoff and indexes from immutable actual receipts; no device or model access."""
from pathlib import Path
import hashlib,json,time
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parents[1];TASK=HERE.parents[1];PROJECT=TASK.parents[1]
OWNER=PROJECT/'deliverables/2026-10-30_board_owner';CANON=OWNER/'integration/production_business_acceptance'
def read(p):return json.loads(p.read_bytes())
def encoded(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def ref(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def put(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(data)
def replace(p,data):
 tmp=p.with_name(p.name+'.final-seal-tmp');put(tmp,data);tmp.replace(p)

def main():
 assert not (HERE/'FINAL_HANDOFF.json').exists()
 release_path=HERE/'CURRENT_SUBTITLE_RELEASE.json';release=read(release_path);current=release['current'];caption=release['caption_trial']
 assert ref(release_path)['sha256']=='5bea114599d4f6995e222f20c587d34656f7356b98500b0e2defee728e17d4e6'
 assert caption['matching_complete_ack'] and caption['user_feedback']=='both_visible'
 assert caption['api_reply_empty_all_observed'] and caption['api_transcript_empty_all_observed']
 assert caption['showing_true_observed'] and not caption['unknown_fields_present']
 state=current['state'];assert state['listening_state']=='PAUSED' and state['microphone_open'] is False and state['playing'] is False
 assert state['following'] is False and state['readback']['flags']==0 and state['readback']['lease_left_ms']==0
 assert current['all_component_bytes_match'] and current['component_pins']==380
 assert ref(CANON/'spec.json')['sha256']=='62b99e24560229c78a3be000fed5752b6a50c4fb16ab6bc2c88e987561831177'
 spec=read(CANON/'spec.json');assert spec['startup_sha256']==current['startup_sha256']=='22317f7933447b28a2ca535a47246de8b3869989cc0d964a13cd169cd2289311'
 assert spec['source_manifest_sha256']==current['manifest_sha256']=='5b741bff8039a4f71110b06cce88ff40bea32a27ace718a263f6879f79deaa2b'
 old_live=read(HERE/'LIVE_STATUS.json');now=datetime.now(timezone.utc).isoformat()
 report=dict(schema='aura-joint-final-handoff-1',status='BOUNDED_TEST_AND_REPAIRS_COMPLETE_FINAL_PAUSED',sealed_utc=now,
  final_actual=current,final_actual_reference=caption['final_paused'],current_spec=ref(CANON/'spec.json'),current_ready=ref(CANON/'actual_ready.json'),
  subtitle_release=ref(release_path),actual_ui_comparison=ref(HERE/'CURRENT_PUBLICATION.json'),
  original_follow_handoff=ref(HERE.parent/'live_follow_test_20261101/HANDOFF.json'),
  original_follow_controller='ORIGINAL_UNCHANGED_25_FILES',follow_polarity=1,follow_candidate_r2_in_production=False,
  user_feedback=dict(original_follow='APPROXIMATE_ACCEPTANCE',intro_audio_continuous=True,intro_wait_acceptable=True,
                     visual_people_count_correct=True,visual_audio_complete=True,multi_turn_memory_ok=True,
                     subtitle_recognition_and_response_visible=True,final_audio_complete=True),
  final_request_token=caption['request_token'],final_matching_complete_ack=True,final_audio_underrun_packets=caption['audio_output']['turn_underrun_packets'],
  gui_runtime_fault_count=caption['runtime_faults']['count'],renderer_worker_fault_count=0,
  api_subtitle_bodies_empty=True,caption_text_images_audio_or_identity_exported=False,
  model_weights_downloaded_copied_or_moved=False,
  bounded_acceptance_limits=dict(mechanical_zero_calibrated=False,physical_shaft_angle_measured=False,
                                 over_five_minute_summary_retrieval_verified=False,acoustic_first_sound_measured=False,
                                 long_duration_stability_verified=False,subtitle_version_performance_resampled=False),
  historical_evidence_preserved=True,device_commands_inflight=False,
  device_operator_thread='01a195e4-58a7-72d3-b141-d5d373579f7f',main_chat_device_ownership_automatically_restored=False)
 put(HERE/'FINAL_HANDOFF.json',encoded(report))
 text=f'''# 本轮实测与修复收尾（2026-11-01）

已完成原板端人脸随动恢复与方向修正、UI状态投影优化、字幕单文件修复和真人复验。最后一轮已收到匹配的完整播放回执，用户确认“两栏字幕都显示，声音完整”。设备最终保持主页面、语音PAUSED/enabled=false/mic=false、无播放、跟随关闭、转轴输出关闭；当前没有在途设备命令。

用户本轮还确认：原版跟随效果大致合适；自我介绍声音连续、等待可接受；视觉人数正确且声音完整；主动多轮测试后仍记得温水偏好。记忆结论属于用户当前会话体验，不扩展为超过五分钟的摘要检索验收。

| 同方法约60秒UI对照 | 改前 | 投影优化后 |
|---|---:|---:|
| publish耗时中位 ms | 9.59 | 4.57 |
| 完整UI回调CPU中位 ms | 25.55 | 20.68 |
| GTK CPU中位，100%=单核 | 51.98% | 47.93% |
| 整板4核CPU忙碌中位 | 56.63% | 54.85% |
| 原生呈现计数/秒 | 15.75 | 15.86 |

该对照属于startup71c28版本，采样脚本正文、2秒间隔、PSS与/proc遍历保持，观察器有可见CPU开销；场景与GUI重启的影响未完全排除。一次绘制101.20ms长尾、视觉源龄P95从176→194ms等限制完整保留。字幕de04版本保留投影热路径，本轮按安排没有再做性能采样。

字幕修复只增加本次有效提交owner/epoch的一次性显示许可，原请求TTL、后续失效、锁顺序和控制API正文清理保持。公开ARM R2在板端Python3.9.9上实际通过19项行为、10项投影与500个嵌套等价案例。最终真人68点记录中，caption.showing的true/false均出现，API两处正文空标志全为true，无缺字段；用户在播放中确认两栏显示。GUI与渲染worker故障均0，本轮音频欠载0。暂停后字幕可按设计清空。

当前生产根仍为`/home/root/aura-board-business-20261030/production-5259eab11e42af13`；startup `{current['startup_sha256']}`，manifest `{current['manifest_sha256']}`，spec `62b99e24560229c78a3be000fed5752b6a50c4fb16ab6bc2c88e987561831177`，配置SHA `{current['configuration_sha256']}`。380项闭包全部实读匹配。最后仅更新production_memory_presentation源码，另外379项、原25文件跟随控制器、当前相机/转轴配置、原相机430894、wide固件与VART保持；跟随极性+1。

最终owner为supervisor689460/birth5191021、GTK689464/birth5191136、camera430894/birth4011213，同boot `{current['boot_id']}`；完整命令指纹见[结构化最终交接](FINAL_HANDOFF.json)。脉宽读回1400µs只是控制读回，不是机械角度或中点标定。最后配对request hash `{caption['request_token']}`；[原始脱敏窗口]({caption['metadata']['path'].replace(chr(92),'/')})、[完整播放结果]({caption['result']['path'].replace(chr(92),'/')})、[最终暂停读回]({caption['final_paused']['path'].replace(chr(92),'/')})均保留。软件首音频入队约9.185秒，不当作声学首声。

首次公开包的Python注解兼容失败、第三轮中断、用户说明问题未说好的无效追问、旧观察器漏关联ACK，以及字幕首窗到时错误取消在途生成的记录均按历史保留。临时观察器随后增加首个已接纳请求门槛，超时只停采样，生成/播放期间不再发送cancel；空闲、生成、播放及一直忙的公开门槛检查通过。先前被取消窗不覆盖为本轮成功，字幕与完整声音的成功只对应最后一轮。

项目spec/ready、AGENTS/README、视觉任务最新指针和协调文件已接入本回执，改前原字节归档保留。后续操作从[最新指针](LATEST.json)读取并新鲜核对设备状态；设备串行分工仍沿用用户安排，本窗口当前空闲。机械零点/角度、声学首声与长期稳定性不属于本轮完成声明。
'''
 put(HERE/'FINAL_HANDOFF.md',text.encode())
 targets=[HERE/'LIVE_STATUS.json',HERE/'LATEST.json',TASK/'LATEST_REVIEW.json',OWNER/'coordination/runtime_windows.json',HERE/'EXECUTION_NOTES.json']
 archive=HERE/'docs_state_joint_final';assert not archive.exists();before=[]
 for p in targets:
  dest=archive/'before'/p.relative_to(PROJECT);put(dest,p.read_bytes());before.append(dict(original=ref(p),archive=ref(dest)))
 live=old_live;live.update(status=report['status'],latest_actual_state=current,latest_state_reference=caption['final_paused'],
                         subtitle_display_acceptance='USER_CONFIRMED_BOTH_COLUMNS_DURING_REPLY',subtitle_control_metadata_available=True,
                         caption_final_trial=caption,pending='No further work in this bounded test; device commands finished and user pause restored.',
                         recorded_utc=now)
 replace(HERE/'LIVE_STATUS.json',encoded(live))
 latest=read(HERE/'LATEST.json');latest['original_baseline_handoff']=latest.get('handoff');latest['ui_projection_publication']=latest.get('current_publication')
 latest.update(status=report['status'],handoff=ref(HERE/'FINAL_HANDOFF.json'),summary=ref(HERE/'FINAL_HANDOFF.md'),
               live_status=ref(HERE/'LIVE_STATUS.json'),current_publication=ref(release_path),latest_actual_state=caption['final_paused'],
               device_commands_inflight=False)
 replace(HERE/'LATEST.json',encoded(latest))
 visual=read(TASK/'LATEST_REVIEW.json');visual['original_follow_review']=dict(review=visual.get('review'),summary=visual.get('summary'))
 visual.update(schema='aura-visual-axis-latest-local-review-3',review='reviews/joint_performance_20261101/FINAL_HANDOFF.json',
               summary='reviews/joint_performance_20261101/FINAL_HANDOFF.md',
               actual_platform_receipt='reviews/joint_performance_20261101/evidence/live_trial_1793536566480481000/FINAL_PAUSED.json',
               production_startup_sha256=current['startup_sha256'],current_live_state_claimed=False,device_commands_inflight=False)
 replace(TASK/'LATEST_REVIEW.json',encoded(visual))
 coord=read(OWNER/'coordination/runtime_windows.json');coord.update(status=report['status'],final_joint_handoff=ref(HERE/'FINAL_HANDOFF.json'),
                        latest_joint_live_status=ref(HERE/'LIVE_STATUS.json'),finalization_stage='REQUESTED_TESTS_COMPLETE_FINAL_PAUSED',updated_utc=now)
 coord['device_operation_owner']['state']='IDLE_COMPLETED_NO_INFLIGHT_COMMANDS';replace(OWNER/'coordination/runtime_windows.json',encoded(coord))
 notes=read(HERE/'EXECUTION_NOTES.json');notes['items'].extend([
  dict(stage='subtitle public R1 ARM',observed='Real AST extraction lost deferred annotations on board Python3.9.9; candidate semantics not reached.',correction='Independent R2 harness explicitly set future annotations and isolated module lifetime; 19+10/500 actual ARM cases passed; candidate de04 unchanged.'),
  dict(stage='first caption live window',observed='Rejected first token and late ordinary request; old timeout cleanup cancelled in-flight generation. User saw recognition caption but received no response audio.',correction='Old window preserved; temporary cleanup removed cancellation, first-accepted-token selection added. Later distinct caption trial had full ACK, user confirmed both captions and complete audio.'),
  dict(stage='extra live requests attribution',observed='Individual additional request sources were not reconstructed.',correction='User later reported active extra-turn testing. Do not classify all extra requests as system-triggered or ambient.')])
 replace(HERE/'EXECUTION_NOTES.json',encoded(notes))
 after=[ref(p) for p in targets]
 put(archive/'SEAL.json',encoded(dict(schema='aura-joint-final-local-index-seal-1',before=before,after=after,
                                     final_handoff=ref(HERE/'FINAL_HANDOFF.json'),summary=ref(HERE/'FINAL_HANDOFF.md'),
                                     canonical_spec=ref(CANON/'spec.json'),canonical_ready=ref(CANON/'actual_ready.json'),device_access=False)))
 for item in before:assert ref(Path(item['archive']['path']))['sha256']==item['original']['sha256']
 assert read(CANON/'spec.json')['startup_sha256']==read(OWNER/'coordination/runtime_windows.json')['startup_sha256']==current['startup_sha256']
 assert read(HERE/'LATEST.json')['summary']['sha256']==ref(HERE/'FINAL_HANDOFF.md')['sha256']
 print(json.dumps(dict(status=report['status'],handoff=ref(HERE/'FINAL_HANDOFF.json'),summary=ref(HERE/'FINAL_HANDOFF.md'),
                      latest=ref(HERE/'LATEST.json'),canonical_spec=ref(CANON/'spec.json'),device_access=False),ensure_ascii=False))

if __name__=='__main__':main()
