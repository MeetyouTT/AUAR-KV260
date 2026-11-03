"""Assemble an evidence-led review and proposed fixes, without runtime changes."""
import datetime,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
read=lambda name:json.loads((HERE/name).read_text(encoding='utf-8'))
runtime=read('active_runtime.json');offline=read('offline_dataset_audit.json')
equivalence=read('reference_equivalence.json');pipeline=read('passive_pipeline.json')
front=json.loads((HERE.parent/'2026-10-19_identity_capture_snapshot/controlled_front_check.json').read_text(encoding='utf-8'))
assert offline['selection_matches_production']
assert all(row['pixel_max_difference']==0 for row in equivalence['public_material_alignment_comparisons'])
assert all(row['opencv_vs_windows_cosine']>.999999 for row in equivalence['saved_real_photo_feature_comparisons'])
findings=[
 {'id':'F1','priority':'P1','title':'0.80为未标定试用门槛，直接拒绝已确认本人的有效输入',
  'file':'aura/board/identity/store.py','needle':"if not scored or scored[0][0] < self.threshold:",
  'confirmed':True,'evidence':['controlled_front_check.json','offline_dataset_audit.json']},
 {'id':'F2','priority':'P1','title':'自然多帧登记最终仅存一个模板，未覆盖多种外观',
  'file':'aura/board/identity/store.py','needle':'PRIMARY KEY(identity_id, model_id)',
  'confirmed':True,'evidence':['active_runtime.json','offline_dataset_audit.json']},
 {'id':'F3','priority':'P2','title':'独立帧验证限于同一短视频，没有跨场景或负样本验收',
  'file':'aura/board/identity/sampling.py','needle':"self.stage = 'ready'; self.until",
  'confirmed':True,'evidence':['offline_dataset_audit.json','controlled_front_check.json']},
 {'id':'F4','priority':'P2','title':'人脸检测额外后等待降低吞吐，丢检即撤销目标和结果',
  'file':'aura/board/identity/face_targets.py','needle':'self.process(packet,detector);next_at=time.monotonic()+self.interval/1000',
  'confirmed':True,'evidence':['passive_pipeline.json','controlled_front_check.json']},
 {'id':'F5','priority':'P2','title':'低相似度被显示为未登记，且关键故障证据未保留',
  'file':'aura/board/identity/live.py','needle':"else '未登记 / UNKNOWN'",
  'confirmed':True,'evidence':['active_runtime.json','controlled_front_check.json']},
]
for finding in findings:
 path=ROOT/finding['file'];lines=path.read_text(encoding='utf-8').splitlines()
 finding['line']=next(i+1 for i,line in enumerate(lines) if finding['needle'] in line)
 finding['absolute_path']=path.as_posix()
 finding['link']='['+Path(finding['file']).name+']('+path.as_posix()+':'+str(finding['line'])+')'
def link(index):return findings[index]['link']
summary={'date':'2026-10-19','status':'REVIEW_COMPLETED_REMEDIATIONS_PROPOSED_NOT_DEPLOYED',
 'scope':'active face enrollment and identification pipeline, voice identity query and actual retained evidence',
 'database':runtime['database'],'threshold':.8,'ambiguity_margin':.1,'findings':findings,
 'direct_rejection_cause_confirmed':'fresh known-positive scores 0.620695–0.643428 are below 0.80',
 'exact_image_cause_of_cross_session_score_drop_confirmed':False,
 'official_alignment_math_bug_reproduced':False,'rgb_channel_or_cpu_backend_mismatch_reproduced':False,
 'one_template_per_identity_confirmed':True,'negative_person_test_count':0,
 'controlled_frontal_test_passed':False,'photo_and_template_consistency_passed':True,
 'native_opencv_vs_windows_features_equivalent_on_three_actual_pngs':True,
 'official_formula_vs_custom_alignment_pixel_identical_on_five_public_cases':True,
 'model_replacement_or_threshold_reduction_authorized_by_this_review':False,
 'production_sources_models_config_or_db_modified':False,'new_current_photos_saved':False}
(HERE/'review_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
threshold_table='\n'.join('| '+str(row['threshold'])+' | '+str(row['saved_collection_13_pass'])+'/13 | '+str(row['final_validation_5_pass'])+'/5 | '+str(row['controlled_new_frontal_6_pass'])+'/6 | 未测 |'
 for row in offline['threshold_counterfactual_numeric_replay'] if row['threshold'] in (.8,.75,.65,.6,.5,.363))
report=f'''# 身份登记与实时识别失败审查

日期：2026-10-19，按用户所在时区记录。状态：已完成源码、活动部署、照片与真实模型复核；提出措施，尚未应用参数、模型或身份库更改。

## 结论先行

当前已完成纯人脸登记与照片留档，正式库1身份/1份128维SFace模板/修订15。登记选中照片与库中模板一致，三方特征重算一致，语音问句已走身份查询。**本人的新正脸有效输入0.621～0.643低于当前0.80，因此匹配器直接拒认。** 这个直接拒绝原因已确认。

更深层的设计问题是：未经本机校准的高门槛、最终只保留一份模板、同会话短时验证和单帧即时判定共同限制可用性；检测吞吐及目标连续性进一步放大失败。当前证据仍不足以把“新正脸为什么降到0.63”唯一归因于眼镜反光、光照、头姿或关键点定位。将这些猜测写成已修复的源码缺陷是不成立的。

本轮没有发现“只写了本地代码未运行”“身份数据没有保存”“仍拿人体特征做认证”或“Windows与板卡SFace颜色通道不一致”的证据。

## 1. 本次审查做了什么

1. 从实际camera PID和systemd参数动态定位活动目录、配置，核对15个相关模块指纹及两个模型SHA；不是根据本地README推断活动版本。
2. 只读核对正式SQLite数量、修订和权限，不导出姓名或生物特征。
3. 用原SFace权重在独立电脑CPU进程重算25张已保存人脸，复现选图规则，得到全体相似度、样本姿态与亮度统计；未访问或修改正式模型服务内存。
4. 用OpenCV 4.6.0官方公式的独立逐项实现对照项目五点对齐，5组公开素材/几何变换裁剪逐像素相同。
5. 将3张真实登记PNG分别送入板卡OpenCV DNN及原Windows CPU ORT，归一化特征余弦均为1.000000，最大单分量差小于0.0000005；输入RGB张量无差别。
6. 复核用户明确配合的10秒正脸检查；另做10秒被动性能测量。后者没有用户声明人员/姿态，只用于吞吐和服务状态，不能当真人通过率。

本轮未重新运行全部222项回归，因为没有修改生产代码；新增的是独立诊断实验。没有停服务、改阈值、写身份库、下载或复制模型权重，也没有保存新的现场照片。

## 2. 当前方案真实结构

```mermaid
flowchart LR
    A[640×480 RGB摄像头] --> B[板端YuNet 2022mar找脸与五点]
    B --> C[单张已确认人脸轨迹]
    C --> D[五点对齐得到112×112人脸]
    D --> E[Windows CPU SFace 2021dec提128维特征]
    E --> F[板端归一化余弦比对]
    G[SQLite 每身份仅一份模板] --> F
    F --> H[门槛0.80及多身份分差0.1]
    H --> I[当前身份状态]
    I --> J[我是谁的受约束语音查询]
```

注册时：语音给称呼→复述并明确确认更新→至少15秒自动选样→正脸候选中选一张实际代表图→后续5份新正脸逐份验证→保存这一张对应的特征→播报真实提交结果。

- **25张照片不是25份库模板，也没有训练或微调SFace。** 13张采集+7张质量拒绝+5张验证已存；库最终仍仅1份模板。
- YOLOX-Nano+ByteTrack是人体检测/跟踪，使用原DPU；当前人脸目标不依赖先选人体。它的帧率不能当作YuNet人脸识别帧率。
- Paraformer提供文字，27B负责普通对话，OmniVoice16负责发声；三者没有生成人脸匹配结果。
- 当前功能是普通RGB人脸身份识别加语音查询；活体检查、说话者与画面人物绑定不是现有实现，个人长期记忆也不能由一次识别自动授权。

## 3. 已确认的问题，按影响排序

### F1 / P1：0.80是直接拒认门槛，但没有做本机阈值标定

位置：{link(0)}；有效配置`threshold_origin`本身写明`user_authorized_experimental_cosine_0.80_not_field_calibrated`，即用户同意的试用值，不是校准结果。

| 检查 | 结果 | 含义 |
| --- | --- | --- |
| 选中图对正式库模板 | 余弦1.0 | 保存一致 |
| 本轮13张采集图对最终模板 | 10/13达到0.80 | 采集内已有外观变化被门槛拒绝 |
| 后5张独立验证 | 5/5，0.813952～0.897079 | 该短时段能配上 |
| 后续本人正脸检查 | 0/6，0.620695～0.643428 | 有效本人输入被当前门槛拒绝 |

这里的0.80是余弦相似度，不是“有80%概率是本人”。OpenCV为SFace给出的LFW示例余弦门槛是0.363，不同基准还使用不同数值；不能把0.80当作人脸识别的通用标准。[OpenCV官方模型与示例](https://docs.opencv.org/4.13.0/d0/dd4/tutorial_dnn_face.html)。

仅对现有分数做离线门槛回放，结果如下。**没有运行完整新策略、没有测其他人的误认，不能据此选一个正式值。**

| 候选门槛 | 已存采集图 | 同会话验证图 | 后续本人正脸有效图 | 其他人误认 |
| --- | --- | --- | --- | --- |
{threshold_table}

因此0.75或0.65仍不能放行这6份有效正脸；0.60在这6份分数上能放行，但不是“已证明0.60合适”。当前没有可靠不同人的负样本，无法估计误认率，也无法证明0.363可直接用于本项目的一对多场景。0.1图库分差在仅1份身份时根本不会触发，不能替代负样本校准。

### F2 / P1：多帧采样最终压缩成单张模板，外观覆盖不足

位置：{link(1)}，数据库主键是`(identity_id, model_id)`，再次登记走替换，不会增加同人多模板；`sampling.py`只把一个实际候选特征交给写库。

本轮13张合格采集均满足现有正脸几何范围；算法按最小yaw/roll排序取5张，再从中选medoid。审查重算的选择与生产完全一致，所选7828确实是正脸，不能继续称“选中了身体”或“这次保存了侧脸”。

问题是只存一份特征时，其余距离、明暗、眼镜反光和轻微姿态变化并未作为其他参考留下。图像文件存下来有助于查错，却不会自动进入模型记忆。13张合格采集已有3张对该模板低于0.80，说明规则内的“正脸”也不等于0.80以上相似度。

不能仅凭同会话5验证图选最高分的替代模板来宣布修复；那会利用验证集反向选模型。本轮另一个候选8016对5验证的最低分0.842811高于已选模板0.813952，也只能作为同会话诊断，不能证明它在后续真人检查更好，因为那6张图没有保留。

### F3 / P2：独立帧验证没有等价于跨会话识别验收

位置：{link(2)}。

采集图跨度15.055秒，训练结束到第一张验证相隔0.708秒，5张验证总跨度仅4.415秒。它们是后来的不同帧，没有自比作弊，但人员、相机曝光、背景、距离和姿态高度相关。

此流程能验证“当前选中的图与随后几秒能配上”，没有验证“离开回来、换距离、重新开对话或改变明暗仍能配上”。同会话登记成功和之后本人正脸失败可以同时发生，二者并不矛盾。

已有222项回归主要验证状态、授权、源帧、防过期、事务等软件行为；公开Lena预检循环重复同一张原图。它们有价值，但不测真实场景分布的正负样本分离，也不等于222次真人准确度测试。对应预检见`../2026-10-19_enrollment_photo_archive/preflight.py`。

### F4 / P2：实际人脸吞吐较低，且一次丢检直接影响身份状态

位置：{link(3)}、`live.py`的`offer_face`与`work`。

本次被动10.18秒测量：YuNet完成23次，约2.260Hz；身份特征完成18次，约1.768Hz。YuNet推理中位247.26ms，源龄中位498ms；特征往返中位31.8ms。Windows模型计算约11ms的健康快照与此一致。因此主要人脸检测节奏不在GPU大语言模型上。

代码在检测结束后再等待200ms，实际周期约“推理耗时+200ms”，不是200ms开始一次。特征端同样在完成后再等500ms。这是可量化的调度开销，不需要靠换LLM处理。

正脸受控检查52次轮询中，33次未满足单人脸条件、9次目标未确认。注意这52次是轮询，可能重复读到同一帧，不能直接算成检测器漏检率；旧日志也未区分33次是0张还是多张。一次无脸检测会清空公开目标和`IdentityService.result`，状态无帧间共识，视觉上容易闪烁。

但检测不是全部原因：本次另一段被动性能测量39次轮询均有1张已确认脸及新鲜输入，仍全部UNKNOWN。它不是用户确认的本人测试，不能用于准确度；却说明当前系统也会在“目标持续有效”时拒认。仅延长跟踪或缓存姓名不能修复有效输入低分。

### F5 / P2：失败分类与证据不足，让排查不断回到重登记

位置：{link(4)}、`photo_archive.py`。

- 相似度不足被显示成“未登记 / UNKNOWN”，但本人实际已登记。低分、无脸、多人、目标未确认、质量不足、过期、网络忙和图库歧义没有形成统一可读的原因码。
- 平时health没有保留带帧归属的匹配分数/原始五点/对齐残差，失败6帧也只留数值；照片存档有姿态概览，没有原五点和仿射矩阵。现在不能离线重现那6帧的定位过程。
- 五点yaw比例不是标定头姿模型；质量规则没有充分评估抬头低头、曝光、眼部遮挡/反光或关键点可信度。本轮照片均不是因为Laplacian清晰度低而被筛除，7张质量拒绝都超过yaw比例0.38，所以不能把它们笼统称为“模糊图”。
- 登记图能看到反光，亮度也随转头变化，但它只是候选影响因素。失败正脸当时的图片/五点不在，不能说已经证明“都是眼镜造成”。

## 4. 已做排除和仍待证实的假设

| 项目 | 审查结果 | 范围限制 |
| --- | --- | --- |
| 身份未写入或模板串错 | 不支持；正式库1/1/修订15，选中图对模板1.0 | 未导出姓名或向量 |
| 人体特征混进当前登记 | 不支持；本轮25图是112×112实际人脸，独立人脸目标 | 旧全幅诊断不是当前路径 |
| 当前保存侧脸 | 不支持；模板7828，yaw比例0.0071、roll约1.11° | yaw是几何提示，非精确角度 |
| RGB/BGR或Windows后端出错 | 3份真实PNG与OpenCV输入及特征一致 | 不代表所有硬件输入质量已验证 |
| 五点对齐公式写错 | 5组公开素材/几何变换输出逐像素一致 | 不能排除上游五点定位漂移 |
| 库中两人过于相似、分差不足 | 当前只有1身份，0.1分差条件不触发 | 未来多人需另测 |
| 结果TTL导致这6份低分 | 该6份源龄429～774ms，未过3秒TTL，无取图/特征错误 | 其他丢脸时刻仍可不可用 |
| 反光、曝光、距离或关键点漂移 | 待证实；登记图明暗/反光存在变化 | 缺失败6帧图片与原五点 |
| 27B没有记住名字导致此次失败 | 不支持；新问句走受约束身份查询，当前脸UNKNOWN便拒报 | 不是说话者认证或长期记忆 |

参考预处理与对齐实现来自[OpenCV官方识别源码](https://github.com/opencv/opencv/blob/4.6.0/modules/objdetect/src/face_recognize.cpp)；YuNet旧版宽高方差0.1/0.2的非对称写法与[官方旧版检测源码](https://github.com/opencv/opencv/blob/4.6.0/modules/objdetect/src/face_detect.cpp)一致，没有把它误判成项目解码bug。

## 5. 解决措施及实施顺序

### 第一阶段：补齐定位信息，建立独立回放集（最高优先）

不让用户反复覆盖现有身份。先用现有25张图建立固定基线；在一次明确启用的失败诊断中，按帧记录检测分数、原五点、脸框尺寸、亮度/眼部遮挡指标、对齐残差、112×112脸图哈希、SFace分数、源龄、模型版本和原因码。仅保留人脸小图，不保存全幅/上半身，不把姓名/向量写入公开报告；普通对话不持续存图。

原因码至少分为NO_FACE、MULTIPLE_FACES、TARGET_UNCONFIRMED、QUALITY_REJECTED、FEATURE_UNAVAILABLE、STALE、LOW_SIMILARITY、AMBIGUOUS。UI将“未登记”改成“当前未能确认身份”，给出与实际原因相符的一条提示。这样可以回答“脸没找到”还是“找到了但分数不够”，避免建议用户重复登记。

需要真正独立于登记的本人短视频/采样会话，覆盖接近和稍远距离、正脸和轻微左右转头、两个实际明暗条件；另收经同意、身份标注可靠的其他人样本。没有负样本时只报告漏认，明确不报告误认率。

### 第二阶段：对SFace门槛做本机标定，保留当前正式值直到结果可评审

固定模型、输入预处理和模板策略，扫描候选余弦门槛，分别统计本人漏认和其他人误认，按独立会话/识别事件划分训练、校准、测试，避免将邻近视频帧随机拆成“独立”样本。对1人图库和预期多人图库分别评估，连0.1分差一起核对。

0.363是官方对照点；0.50～0.65可列入当前数据附近的离线候选扫描，不预先指定胜出值。根据受控6份得出0.60能放行只是数值回放，不能直接上线。结果应有误认/漏认曲线、每组样本数、人与会话划分、可回退配置；参数变更再交给用户确认。

### 第三阶段：让自然多帧采样真正形成少量、多样的身份模板

在独立候选库里把现有单模板结构扩展为每身份最多3～5份真实观察模板，按正面/轻左/轻右及质量分组，保留同一明确身份和来源会话，不自动从普通聊天补模板、不滚动自学习。先利用已存13份合格采集做结构实验，不覆盖正式模板。

匹配策略需限制模板数，结合质量和姿态选择，以及跨帧同一身份一致性；多模板的最高分会增加比较次数，必须重新标定身份层面的误认门槛。不能把“候选多了最高分更高”直接当改进完成，也不能未经验证平均所有角度向量。

若固定输入及校准后，同人/异人分数仍重叠严重，再对新的人脸检测或特征模型做同一回放集A/B；更换权重会产生新model_id和新模板版本，不能把旧SFace向量直接复用。现阶段没有证据要求先更换27B、ASR、TTS或人体DPU。

### 第四阶段：提高有效检测节奏，引入可解释的时间判定

- 将检测和特征的间隔按一次循环的总时间预算调度，去掉“推理完固定再睡200ms”的额外节奏；CPU饱和时丢旧帧保最新，测量板卡温度、相机、DPU与语音共存后决定实际目标帧率。当前247ms中位推理说明单纯减睡眠不能保证5Hz，先测能否达到稳定3～4Hz。
- 对比保持宽高比的输入方式与现有640×480→320×320拉伸，独立测试不同检测分数门槛。当前0.9是常见示例值，不能未经数据就断言过高，也不能盲降把假脸带进来。只有对照数据有收益才换检测方案或迁移计算位置。
- 在“同一有效可见人脸、同模型/服务/库修订”内，用一小段新鲜合格帧做身份共识；例如连续若干帧同一身份才确认，低质量帧显示CHECKING。具体窗口根据实际帧率及误认标定；禁止靠无限延长TTL或继承上一人的名字提高表面通过率。
- 完全失脸、多人、换目标、重启换代或库更新仍立即撤销身份授权；展示防抖与身份授权状态分开，不用几何跟踪代替生物特征确认。

### 第五阶段：按完整体验验收

先约定验收目标，例如独立会话正脸识别事件通过率≥95%、轻微转头≥90%，完全离场后1秒内撤下身份，重返在有效可见条件下2秒内恢复；这些是建议的体验目标，尚未达到。其他人测试应报告人数、会话与误认次数，即使观察0次也不能称真实误认率为0。

验收要覆盖开始/结束对话后再次发问、离场与重返、取消、多人和服务重启。语音“我是谁”只有实时识别通过才报姓名；本次无需通过普通聊天写一个固定名字来伪装识别。登记成功、文件保存、实时识别、语音播报四项应分别报告。

## 6. 对项目推进方式的调整

现有系统的事务、授权和来源保护有实际价值，应保留；问题在于此前多轮修复主要补流程，未形成可重复、跨会话、有负样本的识别评估。后续先固定小型回放数据、复现失败，再单独改一个变量，完成离线对照后才让用户做短时现场验收。避免再靠“版本加载→用户重登→再问是否成功”的循环寻找参数。

优先路线：**原因与证据可见 → 独立数据上的阈值标定 → 少量多样模板 → 检测节奏与时序判定 → 完整语音验收。** 不以反复登记、单纯加照片数量、直接降到官方示例值或立即换大模型作为本轮结论。

## 7. 证据及状态

- `active_runtime.json`：实际版本、源指纹、模型SHA、有效配置和库数量。UI28f2/相机6f1分属两个服务是当前安排；相机目录中的旧UI模块没有被作为正式GUI运行，不能把这两处不同哈希当作修复未生效。
- `offline_dataset_audit.json`：25张图的特征重算、选图复现、相似度矩阵、门槛数值回放和时间跨度。
- `reference_equivalence.json`：5组官方对齐公式对照、3张实际PNG的原板卡/电脑特征对照。
- `passive_pipeline.json`：被动10秒吞吐；不是另一次本人受控测试。
- `../2026-10-19_identity_capture_snapshot/controlled_front_check.json`：用户确认本人正脸的10秒检查。
- `review_summary.json`：问题优先级、源码定位及本轮状态。

原照片在`身份登记照片/c6c3fa6ebd4449ae93bd9ec316344d51/`，未复制到审查源码包。LLM权重、下载及Ollama数据继续在D盘。本报告给出分析和可评审措施，不代表这些措施已部署或真人识别已修复。
'''
(HERE/'REPORT.md').write_text(report,encoding='utf-8')
analysis=ROOT.parent/'语言模型分析';name='身份认证失败详细审查与解决措施_20261019.md'
(analysis/name).write_text(report,encoding='utf-8')
marker='identity-failure-audit-20261019'
def note(path,body):
 raw=path.read_text(encoding='utf-8')
 raw=re.sub(r'<!-- '+marker+r' -->.*?<!-- /'+marker+r' -->\s*','',raw,flags=re.S)
 path.write_text('<!-- '+marker+' -->\n'+body+'\n<!-- /'+marker+' -->\n\n'+raw,encoding='utf-8')
note(ROOT/'AGENTS.md','- 2026-10-19用户要求详细审查身份失败，已完成只读审查与措施提案，生产代码/模型/0.80/0.1/身份库均未改。当前库1身份/1模板/修订15；25图原CPU重算复现选图，selected对库1.0；5组对齐与官方公式逐像素一致，3实际PNG板端OpenCV对电脑ORT余弦1.0，不能再把颜色/后端/对齐公式错误当已确认主因。直接拒认因本人新正脸0.620695～0.643428低于未标定0.80；25图实际只存单模板，同会话验证跨度4.415秒，不等于跨会话通过。0.60仅离线6份分数可放行，负样本0，不能直接部署或称误认已校准。人脸实测2.26Hz/特征1.768Hz（人体DPU帧率无关），推理后200ms额外等待；后续被动稳定1脸仍UNKNOWN，检测不是唯一原因。具体光照/反光/关键点导致低分尚无失败图证据。措施顺序：原因码及失败人脸证据→独立正负会话标定→少量多样模板并重标定→调度与同目标短窗共识→完整验收。审查入口deliverables/2026-10-19_identity_failure_audit/REPORT.md、review_summary.json；不自动重登记/改阈值/换模型。LLM数据D盘。')
note(ROOT/'README.md','> **2026-10-19 身份失败详细审查完成：** 已确认未标定0.80门槛拒绝有效本人输入；单模板与同会话验证覆盖不足，检测吞吐及状态策略放大失败。已排查模板写入、颜色通道和对齐公式，未部署参数或模型变更。[详细分析与解决措施](deliverables/2026-10-19_identity_failure_audit/REPORT.md)。')
note(analysis/'README.md',f'[身份认证失败详细审查与解决措施]({name})：含活动版本核对、25图重算、官方公式/后端对照和优先实施路线；尚未部署变更。')
print(json.dumps({'status':summary['status'],'report':str(HERE/'REPORT.md'),'findings':len(findings),
 'database':runtime['database'],'production_changed':False},ensure_ascii=False))
