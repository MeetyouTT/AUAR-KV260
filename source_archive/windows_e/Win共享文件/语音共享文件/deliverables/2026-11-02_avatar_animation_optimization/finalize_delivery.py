from inspect_baseline import *
import statistics,zipfile
def main():
 manifest=load(HERE/'release/MANIFEST.json');gate=load(HERE/'release/QUALITY_GATE.json')
 before=load(HERE/'validation/LIVE_BEFORE_VALID.json');after=load(HERE/'validation/LIVE_AFTER_R2.json');ready=load(HERE/'validation/R2_READY_RECOVERED_WAIT2.json')
 assert ready['status']=='READY_WITH_NEW_NATIVE_LIBRARY' and ready['all_380_pins_match']
 params=load(HERE/'board_results/revision2b/physical_parameters.json')['states_and_poses'][0]['parameters']
 export=Path('E:/AUAR_工程交付_20261102');checks=[]
 for line in (export/'SHA256SUMS.txt').read_text(encoding='utf-8-sig').splitlines():
  if not line.strip():continue
  h,name=line.split(None,1);name=name.strip().lstrip('*');p=export/name
  actual=sha(p);assert actual==h.lower(),name;checks.append(dict(file=name,sha256=actual))
 save(HERE/'validation/ENGINEERING_BASELINE_PRESERVED.json',dict(status='ALL_EXISTING_RELEASE_CHECKSUMS_MATCH',files=checks,archive_or_manifest_rewritten=False))
 m=load(HERE/'validation/MODEL_RECOVERY_RESULT.json')
 same=gate['same_load_ABBA']
 status=dict(schema='aura-avatar-animation-final-1',updated_host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  release='R2_shoulder_pivot',implemented=True,files_published=True,loaded_into_original_GUI=True,software_readiness_verified=True,
  render_capture_reviewed=True,physical_screen_human_confirmed=False,physical_screen_feedback='PENDING_USER_OPTIONAL_RESPONSE',
  current_startup_sha256=manifest['startup_after'],native_library_sha256=manifest['components']['tools/libaura_yuki.so']['after_sha256'],
  boot_id=ready['boot_id'],gui_owner=ready['gui_owner'],gtk_owner=ready['gtk_owner'],camera_owner=ready['camera_owner'],
  changed_components=list(manifest['components']),component_count=380,other_components_preserved=376,
  source_directory='candidate_physics_v2/native',release_package='release/animation_overlay_R2.zip',native_package='release/native_physics_arm_R2.zip',
  before_after_GIF='previews/final_R2/before_after.gif',before_after_16fps_video='previews/final_R2/before_after_16fps.mp4',
  controlled_real_KV260_ABBA=same,original_GUI_before=before['native_swap_fps'],loaded_GUI_after=after['native_swap_fps'],
  live_before_after_not_causal_speed_comparison='Windows original model endpoint was recovered and GUI restarted between samples; use ABBA for controlled renderer cost.',
  audio_eye_policies_tested=True,synthetic_audio_envelope_only=True,new_human_audio_or_screen_acceptance_claimed=False,
  preserved_engineering_release_checksums=True,models_and_voice_configuration_changed=False,
  missing_original_model_service_recovered=dict(session=m['session_id'],status=m['status'],configuration_sha256=m['state']['configuration_sha256'],model=m['health']['backend']['model'],tts=m['health']['backend']['tts'],steps=m['health']['backend']['num_step']),
  listening_preference_restored=True,listening_enabled=False,microphone_open=False,axis_following=False,axis_motion_commands=0,camera_restarts=0,DFX_or_boot_changes=0,
  unused_exploration='candidate/ eye work and baseline/native e2 minimal motion were not selected or published',rejected_candidate='candidate_physics/ (V1 sleeve detachment)',
  review_receipts=['validation/QUALITY_GATE.json','validation/LIVE_BEFORE_VALID.json','validation/LIVE_AFTER_R2.json','validation/R2_READY_RECOVERED_WAIT2.json','validation/PUBLICATION_R2.json'])
 save(HERE/'STATUS.json',status)
 readme=f'''# 雪妃物理与手臂动画 R2

本轮按用户补充要求，重点增强部件物理反馈和手臂摆动幅度。R2 已发布并由原 GTK/EGL 界面实际加载；380 项绑定一致、角色可见、运行故障 0。已检查板端原生录制，用户现场观感反馈尚未回传，故实屏人类验收仍标为待确认。

可以直接查看 [前后 GIF（左原版、右新版）](previews/final_R2/before_after.gif)、[16fps MP4](previews/final_R2/before_after_16fps.mp4) 和 [抽帧总览](previews/final_R2/contact_sheet.png)。GIF 为 8fps 便于预览，MP4 保留 16fps 时间轴；两者均由 KV260 原生 GLES2 离屏画面生成，不是物理面板录像，也没有现场音频、人物或摄像头画面。

## 已实现的变化

- 原 A/B 两套姿态、四条手臂分支加入连续转动。以原图袖口顶部的肩部附着点为支点，做位置补偿；中立首帧与原版逐像素相同。
- 左右臂使用各自的阻尼弹簧状态，保留角速度；开始、回摆和状态切换不重置相位或动量。强弱随待机、思考、回答平滑变化。
- 增加小幅头部/躯干驱动，在现有 60Hz author tick 内让原锚点带动原物理链；头发输出倍率 1.35，附属部件 1.40。原物理求解器、角色图、纹理、构图和原身体呼吸保留。
- 原口型、PCM 所属、150ms 过期保护、取消/暂停闭口、原眼部策略通过实际 ARM 回归。眼部平滑探索未纳入本次发布。

16 秒待机参数检查（除去前 3 秒预热）中，新增左臂关节角 {params['aura_arm_left']['min']:.2f}°～{params['aura_arm_left']['max']:.2f}°，右臂 {params['aura_arm_right']['min']:.2f}°～{params['aura_arm_right']['max']:.2f}°。这是局部关节驱动角，不是实体转轴角，也不是整条手臂在屏幕上的总轨迹。

## 验证与性能

| 同负载真实 KV260 离屏 A/B/B/A，合计 40 秒 | 原版 | R2 |
|---|---:|---:|
| 完成帧率，各两轮中位 | {same['baseline_fps']:.3f} fps | {same['candidate_fps']:.3f} fps |
| 完成一帧 P50，各两轮中位 | {same['baseline_completed_frame_ms_p50']:.2f} ms | {same['candidate_completed_frame_ms_p50']:.2f} ms |
| 完成一帧 P95，各两轮中位 | {same['baseline_completed_frame_ms_p95']:.2f} ms | {same['candidate_completed_frame_ms_p95']:.2f} ms |

该对照使用同一相机实例、同一模型/纹理、423×516 尺寸、同种子及时间轴。计时包含 glFinish，计时环无截图读回；GUI 停止，不等同物理面板呈现帧率。没有宣称提速。

原主界面 20 秒样本约 {before['native_swap_fps']:.2f} fps，新版加载后 20 秒约 {after['native_swap_fps']:.2f} fps，均来自真实 swap 计数。两窗口之间恢复了退出的 Windows 模型接口并重启 GUI，环境不同，只作各自运行观测，不作为因果提速 A/B。

ARM 两版各 1536 帧、2 姿态×3 状态参数回归通过，并运行原口型/眼部/owner/过期测试。192 帧×原版/R2 的主姿态对照、96 帧×原版/R2 的 B 姿态对照已留存。原素材中立首帧在两套姿态均为 0 个差异像素。已抽查两套姿态的肩部、袖口和手臂连接；这不扩展为多小时稳定或新真人声画验收。

## 发布、依赖恢复与范围

当前 startup `{manifest['startup_after']}`，原生库 `{status['native_library_sha256']}`。只替换原生库及其三份绑定文件，另 376 项组件保留。[发布清单](release/MANIFEST.json) 给出逐项前后 SHA；[运行就绪](validation/R2_READY_RECOVERED_WAIT2.json) 与 [后测](validation/LIVE_AFTER_R2.json) 给出实际进程指纹。

首次正常 GUI 启动在原模型接口 Date 校验的 socket connect 阶段失败，未进入动画初始化。新鲜检查确认 8797 无监听、原模型 owner 已退出，维护方确认没有停用安排。沿原 start_inference.ps1 -Action Start 恢复同配置 {m['health']['backend']['model']} / OmniVoice {m['health']['backend']['num_step']} 步；恢复健康后另留一次明确的新 GUI 启动事务并通过 READY。没有循环重启或降低原时钟校验。[依赖恢复回执](validation/MODEL_RECOVERY_RESULT.json)。

当前监听偏好保持本轮接手实读的 false，麦克风关闭；相机原 owner 不变，未运行转轴、DFX、R7 或相机重启。业务、身份、声纹门槛、音色及记忆机制保留；没有读取或导出私库、登记模板、现场录音。

E:/AUAR_工程交付_20261102 的原包和 SHA 清单保持，现逐项核对仍匹配。[原交付校验](validation/ENGINEERING_BASELINE_PRESERVED.json)。本轮新版本单独归档：[动画覆盖包](release/animation_overlay_R2.zip)、[原生源码及二进制](release/native_physics_arm_R2.zip)、[回退说明](ROLLBACK.md)。

## 留存的失败与未采用材料

第一版围绕图片中心转动，出现袖口脱离，已拒绝；证据保留于 previews/contact_sheet.png、board_results/previews/candidate_v1。R2 改为原始图集中测得的肩部顶部支点并重新编译/录制。首次 R2 暂存脚本生成错误及缺少暂存源导致的编译拒绝，保留于 board_results/revision2/steps.json；最终实际工件为 revision2b，来源逐项与 candidate_physics_v2/native 匹配。

早期 baseline/native 的 e2 连续微动并非现役 b243 库，已用原编译回执校正，正确基线在 baseline/actual_native 与 baseline/ACTUAL_LIBRARY_SOURCE_LINEAGE.json。candidate/ 的眼部探索未加载。首次缺 Origin 的页面请求未通过校验；确认页面未变后按原接口补齐 Origin/Host，再取得有效主页面基线。以上失败未套用为通过记录。
'''
 (HERE/'README.md').write_text(readme,encoding='utf8')
 rollback='''# R2 回退到本轮原版

回退单位是四个组件与原 startup 配置，原字节已在正常停止 GUI 后留存。本说明不自动提交任何设备操作。

| 文件 | 原件 |
|---|---|
| tools/libaura_yuki.so | board_results/backup/tools/libaura_yuki.so |
| config/yuki_pair.formal.json | board_results/backup/config/yuki_pair.formal.json |
| tools/formal_yuki.py | board_results/backup/tools/formal_yuki.py |
| config/board_avatar_gtk.json | board_results/backup/config/board_avatar_gtk.json |
| startup/config.json | board_results/backup/startup.json |

1. 由当前维护者先取得明确设备交接，现读 boot、startup、GUI/GTK 和相机的 PID/birth/命令哈希，以及播放/录音/跟随状态。核对 R2 完整 380 项来源与 release/MANIFEST.json，留存当前监听偏好。原接手或本次 PID 都不能当作未来固定值。
2. 在实际空闲、暂停监听且无自动跟随时，沿原正常 GUI 停止流程，使用 KillMode=process、SendSIGKILL=no、TimeoutStopSec=infinity 的本次唯一临时保护；只提交一次正常 stop，等待 supervisor 与 GTK 原寿命结束。结束后移除本次保护并恢复原 unit 属性。相机保持运行。
3. 确认 GUI 为 inactive/dead/MainPID0、无 Job，原相机 owner 未变，原监听偏好已保存。任务板端目录的 publish_animation.py --rollback 可在这些严格条件下以 CAS 恢复原四项及 startup 原字节；它还会检查当前 R2 哈希和其余376项。完整恢复后必须再次核对380项。
4. 核对原 Windows8797健康及原启动依赖，按新鲜来源创建新的单次正常 GUI 启动事务。实读 READY、角色可见、swap计数增长及故障0，恢复步骤1实际读取的监听偏好。
5. 本轮 gui_maintenance.py/start_after_model_recovery.py 是封存的单次事务，绑定本轮 owner/intent，保留作流程证据；未来回退由维护者用新事实构造事务，不能重放历史 one-shot 或只替换旧PID来绕过检查。模型、库、摄像头、平台和转轴都不属于动画回退内容。

板端备份亦保留在 STATUS.json 对应发布 stage 的 backup/。当前原版 startup SHA 为 c3861fa3d2cbb10fee424804f7b3932eadd576819a2a6290c7ca406d900b9602，原库 SHA 为 b2432e75a75e4dbdebee8e89a141a68ba00671c33b2b258b81ce16794b2c73d2。若在本轮后已有其他发布，先合并这些后续增量并重新核验，不覆盖别人的新版本。
'''
 (HERE/'ROLLBACK.md').write_text(rollback,encoding='utf8')
 print(json.dumps(dict(status='R2_IMPLEMENTED_PUBLISHED_LOADED_VERIFIED_PREVIEW_DELIVERED',startup=status['current_startup_sha256'],native=status['native_library_sha256'],loaded_GUI_fps=status['loaded_GUI_after'],old_engineering_checksums=len(checks),physical_confirmation=False)))
if __name__=='__main__':main()
