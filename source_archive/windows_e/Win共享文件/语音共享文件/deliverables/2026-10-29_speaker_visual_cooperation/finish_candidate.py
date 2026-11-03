import ast,datetime,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
b=json.loads((H/'board_baseline.json').read_text(encoding='utf-8'));files={}
prior=json.loads((H/'SOURCE_MANIFEST.json').read_text(encoding='utf-8')) if (H/'SOURCE_MANIFEST.json').exists() else None
for path in sorted((H/'candidate').rglob('*.py')):
    raw=path.read_bytes();ast.parse(raw.decode('utf-8'));name=path.relative_to(H/'candidate').as_posix()
    if prior and name in prior['files']:base=prior['files'][name]['base_sha256']
    elif name in b['pins']:base=b['pins'][name]
    else:base=hashlib.sha256((A/name).read_bytes()).hexdigest() if (A/name).exists() else None
    files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'base_sha256':base}
def tests(name):
    root=ET.parse(H/name).getroot();suite=root if root.tag=='testsuite' else root.find('testsuite')
    value={k:int(suite.attrib.get(k,0)) for k in ('tests','failures','errors','skipped')}
    assert value['failures']==value['errors']==0;return value
manifest=dict(version=1,status='CANDIDATE_VERIFIED_NOT_DEPLOYED',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  files=files,windows_files=[n for n in files if not n.startswith('board/')],
  board_components=['common/speaker_visual.py','board/runtime/audio/channel_jobs.py','board/runtime/audio/voice_channel.py'],
  board_baseline=b,tests=tests('tests.xml'),compatibility=tests('compat_tests.xml'),
  original_voice_fingerprint_preserved_by_agent=True,real_identity_databases_modified=False,
  services_restarted=False,microphone_opened=False,raw_audio_or_images_persisted=False)
manifest['pcm_lifecycle_revision']='queued-reference-release-v2'
manifest['pcm_lifecycle_changed_files']=['tools/speaker_turn_host.py','tools/speaker_turns.py','tools/device_hub.py']
manifest['validation_scope']={'specialized_current':55,'original_specialized_retained':49,'compatibility_retained':115,'compatibility_repeated_after_lifecycle':False}
(H/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
text='''# 声纹与视觉协作：候选实现及集成接口

本目录为子代理交付。PCM生命周期修订后的55项专项通过，原49项专项与115项既有声纹/个人记忆/持久对话/本地HTTP通道回归证据保留；本次小修仅重跑专项。仅准备候选，未部署、未覆盖正式aura、未重启任何服务，没有加载模型或接触真实模板/现场音频/相机画面。新匿名身份绑定方案由另一子代理负责，不在本次核心小修中变更。

## 实现与限制

此前普通对话只询问声纹登记是否进行中，只有显式声纹命令才送PCM，离线speaker_attribution门并未接通。新增链路让普通持久会话每轮都能先记录匿名/待分析状态，再将描述性声纹证据补回同一个原始回合，失败、短句、未知声纹或无镜头时仍继续普通对话。

- 声纹分析复用Hub现有ECAPA单CPU worker和gallery，不登记、不改模板。未现场标定时记录NOT_CALIBRATED并跳过embedding，避免无意义负载。已标定匹配仍只是CANDIDATE；同model/gallery revision、30秒内三份不同capture和不同PCM才标CANDIDATE_STABLE。重复PCM/取消/过期/未知不增强连续证据。
- 视觉仅记录采集边界两份独立新帧的脸部观察：同boot、服务epoch、相机epoch、轨迹代次、身份库修订、同一可见目标，新鲜source帧与裁脸来源一致。多人、掉线、换代、过期、fixture源等记UNAVAILABLE。包中没有姓名、图像或模板；相机provider异常降级，不阻断语音。
- 没有活跃说话人ASD或重叠说话检测，因此始终single_speaker_verified=false，声纹和人脸是INDEPENDENT_EVIDENCE。不会把“看见的人”当说话者，不按同名合并跨模态身份，也不自动打开个人记忆。匿名会话ID只代表对话范围，不伪称稳定物理说话者ID。
- 原turns/事实/ACK/回忆来源不变，新建turn_speaker_attribution独立表，通过完整原ASR context和CID精确绑定。慢结果在原turn已经generated/played、下一轮正常开始后仍可回填原turn；显式取消、到期、记忆版本变化及个人授权撤销使记录匿名终结，结果不能流入下一轮。
- 一条模型端poll线程、队列上限2、最多3个tracker任务槽；此处是任务槽/所属引用的范围，不是整条链路最多3份PCM拷贝。Tracker取消或关闭时立即清排队job PCM；现有poll循环也清理已到期的排队任务。Hub把future的PCM参数改为可清空工作描述，取消/观测到期清引用并取消尚未启动的future。没有另建原始PCM/图片持久库。
- Hub最多256份10分钟元数据结果，12秒逻辑分析截止；模型端默认14秒轮询期限，与TTS完成无关。已经进入HTTP或原生CPU函数的局部PCM不能强杀，待函数正常返回后释放；TTL阻止过期结果回写，不代表12/14秒硬删除、系统内所有拷贝消失或操作系统内存清零。提交ACK丢失时后台仍按完整原meta尽力取消Hub，不将不确定提交状态遗留为新一轮的结果。
- 新归属DB操作Python锁最多等待30ms、SQLite busy最多30ms，拥塞时匿名降级。原数据库交易等待/ACK语义不变。新元数据默认不注入LLM上下文，不作为姓名或授权凭据。

## 父代理接入

1. ModelHost构造：

```python
from tools.speaker_conversation import SpeakerConversation
self.speaker_conversation = SpeakerConversation(
    self.conversations, scope_for=lambda meta: turn_profile(self, meta))
```

scope_for每次后台写入均重新进入原个人grant，匿名默认None；不能从候选声纹生成profile。

2. Handler在ASR/唤醒通过且存在普通CID后暂存请求PCM/视觉元数据，仅在begin_conversation已经成功写入原turn之后调用：

```python
self.speaker_conversation.begin(meta, cid, pcm, visual, deadline=request_deadline)
```

该调用不等待embedding或HTTP结果；pending先落独立表，再由单worker提交和持续查询。中断调用cancel(meta)，关闭服务调用close()，health()只返回计数和资源上限，没有名字/ID/PCM。不要在生成/播放完成时关闭tracker，否则慢结果无法补回原turn。普通下一轮开始不等同取消上一轮。

3. 可选header为X-Aura-Speaker-Visual（最多4096字符），使用common.speaker_visual.decode_visual_header(header, meta)。缺失时visual=None，语音照常。两份板端候选已从board_baseline.json的实际runtime按绑定SHA逐字节读取；channel_jobs只读原有in-memory identity_snapshot，voice_channel仅附加有界metadata header，不导出相机图像。

4. Hub在初始化现有speaker_pool时增设SpeakerTurns，不新建模型。仅模型本机/本有线地址可调用：

| 路由 | 字段 |
| --- | --- |
| /v1/speaker/analysis/submit | context, conversation_id, pcm(base64), visual |
| /v1/speaker/analysis/result | context, conversation_id |
| /v1/speaker/analysis/cancel | context, conversation_id |

底层adapter为device_client.submit_speaker_turn、speaker_turn_result、cancel_speaker_turn，由后台线程调用。登记/删除/原记忆API保持。

5. ConversationStore新增attribution_pending/attribution_merge/attribution_cancel/attribution_for_turn/attribution_records。Profile/Timeline继承保留原scope检查；取消只清除原request候选，不能读取私人内容。attribution_records排除已遗忘/抑制的历史。权限令牌仍完全沿用ProfileAccess。

## 文件与部署

SOURCE_MANIFEST.json列出11份候选的完整SHA和原始基线SHA。Windows需其中9份；板端仅需新增common/speaker_visual.py、修改board/runtime/audio/channel_jobs.py和voice_channel.py（预计原279组件新增1项为280，最终由父代理重新核对）。不要把本候选的所有Windows模块一并复制上板，也不要从A的旧channel_jobs覆盖现役音频/动画更新。

由父代理统一合并GPU/本项/共享入口，重算voice SOURCE_FILES指纹并安全重载。任何板端部署前重新发现/proc实际入口和pins，并再次双确认空闲、监听/麦克风/跟随/运动关闭。保留原机械FAULT/boot/FDT/固件/VART保护、并行优化、其他模型和D盘LLM存储。所有真实私有库备份/验证继续使用独立隐藏WMI文件视图；只添加新表，不回滚旧库。

## 证据与未验项目

- tests.xml/tests_pcm_lifecycle.log：55项真实SQLite、纯函数、合成向量、模拟CPU、假HTTP handler和薄传输专项通过。新增验证第一任务阻塞、第二任务排队后取消/到期立即清所属PCM引用且encoder零调用，Hub未启动future取消/到期同样不编码；活动原生函数自然返回且取消结果不回写。原49项在tests_pre_pcm_lifecycle.xml/.log保留。
- compat_tests.xml/compat_tests_verified.log：115项原兼容回归通过。最初test_voice_identity需要Linux fcntl，Windows收集错误保留于compat_initial_collection.*，没有给fcntl造替身；该Linux测试未在本子任务执行。
- compat_mock_mismatch.*保留114通过/1旧mock不识别social关键字失败。fixture_adaptation.json确认仅mock补现役API，8条原assert AST不变，原生产prepare_feedback语义不变；新增专项还确认social分支确实保留。
- 两份板端源码已只读核对，但未在ARM加载新候选。未做真人声纹标定、陌生人/多人/跨天误认率、现场声画关联或有声对话验收。已标定标志必须来自可信、模型绑定的现场证据；当前未标定不能承诺识别出真人身份。

本轮完成工程链路候选，真实连续识别质量和最终部署由父代理后续验收；研究代理提供的Light-ASD可作为未来独立评估方向，本轮没有添加该模型或GPU开销。
'''
(H/'README.md').write_text(text,encoding='utf-8')
(H/'PROGRESS.json').write_text(json.dumps(dict(status=manifest['status'],complete=False,implementation_complete=True,
 candidate_only=True,tests=manifest['tests'],compatibility=manifest['compatibility'],
 pending=['parent integration/deployment','ARM smoke','field speaker calibration','human audiovisual acceptance'],
 automatic_profile_access=False,raw_pcm_persisted=False,other_models_stopped=False),indent=2),encoding='utf-8')
print(json.dumps({'status':manifest['status'],'files':len(files),'tests':manifest['tests'],'compatibility':manifest['compatibility'],
 'board_components':manifest['board_components'],'manifest':str(H/'SOURCE_MANIFEST.json')}))
