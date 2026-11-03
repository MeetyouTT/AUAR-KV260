# 父侧板端合入接点

使用本目录 `candidate/`，不要把父目录冻结的旧两份 transport 覆盖回来。与 anonymous_identity_binding 的 extras 组合，并把本目录 SOURCE_MANIFEST 的 9 组件加入实际 UI runtime 和严格配置 pin；现役所有音频/动画/机械保护及并行 startup-speed 原字节/参数保留。

组件：

```
board/runtime/audio/channel_jobs.py          # 更新，保持原55版内容
board/runtime/audio/voice_channel.py         # 更新，保持原55版内容
board/runtime/audio/face_binding_bridge.py   # 新增
board/runtime/audio/face_gallery_readback.py # 新增
common/face_binding_wire.py                  # 新增，Windows同份依赖
common/binding_intent.py                     # 新增，匿名方案冻结版本逐字节复制
common/speaker_visual.py                     # 原55版逐字节复制
tools/enrollment_receipts.py                 # 匿名方案冻结版本逐字节复制，无签署密钥
config/face_gallery_readback.local.json      # 新增，严格实际来源pin
```

无新摄像头/模型/原生 runner import。直接非标准库依赖仅为现役 `common.asr_wire`、`common.voice_enrollment`、`board.identity.store.normalize`、`board.interaction.ui_contract`、`board.identity.voice_enrollment`、原 `TranscriptionJobs`/`VoiceChannel`。新增 `tools.enrollment_receipts` 模块顶层只有 stdlib、ASR context 和 ui_contract；其声纹桥类不会在板端实例化。ARM 已验证以上依赖可加载。

## 每轮图库传输

UI 网络 worker 上从已验证的当前 in-memory snapshot 调 `FaceGalleryReadback.read(meta,snapshot)`。仅按配置打开真实模型库，mode=ro、query_only、30ms busy timeout、独立事务；要求专用 `identity_model_binding` 精确匹配、无混合模型、真实 revision 与 snapshot 一致。未知/可见模板缺失仍保留可信 revision 和完整库存，`current=null`。所有模板只在拥有节点 RAM 验证并计算原 JSON SHA256。

POST `/v1/voice/identity/gallery`：

```json
{
  "context": "完整原ASR context对象",
  "packet": {
    "version": 1,
    "context": "同一ASR context对象",
    "gallery": {"store_id":"gallery-摘要","model_id":"实际模型","revision":1,"source_kind":"actual"},
    "current": null,
    "inventory": [["原外键ID","原模板JSON的64hex-SHA256"]]
  }
}
```

库存按 ID 唯一排序，最多原32项；没有姓名/图片/向量。规范 JSON 为 UTF8/ensure_ascii=False/sort_keys=True/separators=(',',':')/allow_nan=False。共享 `validate_packet(value,meta=None)`、`packet_sha256(value)`、`decode_gallery_header(header,meta)` 已冻结。

整包实际序列化字节不超过24576；ACK 必须恰为 `{accepted:true,packet_sha256:同摘要}`，当前请求仍有效，随后才附 `X-Aura-Face-Gallery`：`v1:` + urlsafe-base64 JSON（保留padding，最多4096字符），内部 exact 为 `{version:1,context:meta,packet_sha256,current}`。Windows 必须命中同 context+digest 的已验 packet。请求失败或缺视觉/配置仍正常对话，不能把未收到库存当空库删除。

## 统一登记分支

原 `identity_request` 48hex token 的 transcript 可附 exact `binding_request`：

```
{version:1, attempt_id, origin_context, face_guard, name,
 board_text, confirmed_existing:boolean}
```

真实 attempt 是32hex；只有询问姓名的 `name-wait-<32hex>` 可用空/null name，且 confirmed_existing=false，不能生成提交回执。face_guard exact 为 service_epoch/camera_epoch/target/gallery_revision/face_identity_id；target 为原 camera_epoch/track_id/track_generation。origin 与 commit 必须同 boot/session，世代不倒退。

板端仅在原身份分支对单独 board_text 调冻结 `face_enrollment_text`；原 ASR transcript 保持。没有 binding_request 的旧人脸查询/登记仍使用原 FSM。

`FaceBindingBridge` 用 thread-local scope 包装原 FSM 的 snapshot/command，guide 线程显式进入原 exchange scope。它不会替换原登记策略。提交回执要求同一实际命令的 full ACK、identity_completion/last_operation=COMMITTED、图库revision+1、唯一新增或原明确替换外键，以及本轮真实 ASR 明确确认；话术 registered 本身无效。已有KNOWN须同脸实际新鲜匹配、同库版本、原姓名一致、且本轮真实ASR明确确认与 confirmed_existing=true，状态为 EXISTING_CONFIRMED。没有ASD，不声明单一发声者已验证。

最终 `identity_result` 原 body/context/token/sequence/final 不变，可多一个 unsigned `binding_receipt`，schema 与冻结 `tools.enrollment_receipts.face_commit_payload/existing_face_payload` 一致。仅 final registered/already_known 可附，整包按真实 json.dumps(...).encode() 严格<=4096；超限整体省去 receipt，交由统一 transform 告知尚未完成。不能截断回执或因 registered 绕过验证。父侧4096读取门槛无需扩大。

只有 Windows 原token适配器经 owner/token/sequence/final/attempt/origin/commit/name/gallery/guard 校验后才能受限签署；板端不持签署密钥，不暴露通用签署接口。原两个模板库分别提交，最终关联激活由匿名方案 registry 决定，个人档案和个人记忆权限保持原规则。

## 部署与回退

本轮只准备候选。父侧需再次读实际 `/proc/MainPID/cmdline`、pending unit、全部 pins 和双确认空闲，保护相机及并行更新。配置source guard在部署前应再次纯只读 verify；相机/boot变化则停止身份部分，普通语音仍可用，不复制旧boot绑定到新进程。UI恢复方式沿现役监督器/启动器，不运行历史重启脚本；相机保持不重启。

diffs 同时保留针对实际279版与冻结55版的两份薄传输差异。没有回滚真实身份库、导出模板或更改原模型/阈值。模块级回退需按父侧整个UI pin配置原子回退到本次完整基线，不能只删一份必需import。
