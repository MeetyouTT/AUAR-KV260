# 板端真实人脸回执桥（候选已冻结，未部署）

本增量以父目录 55 项版的两份薄传输为基线，保持现役音频、动作和原 VoiceEnrollment 状态机。原 11 文件及历史 SOURCE_MANIFEST.json 逐 SHA 校验未变。正式源文件、板卡入口和服务均未修改。

新 manifest 为本目录 SOURCE_MANIFEST.json。9 个组件中，2 个更新现有薄传输，7 个新增严格 pin，单独合入时为 279→286 项；父侧其他新增组件应在同一份实际配置中取并集，不能减掉旧 pin。

## 实际来源

- 现役 UI runtime：`/home/root/aura-audio-animation-20261029/2a62bf25b0994029a1ff0f23f0b9720e/runtime`，279 项源检查一致。
- `/proc/1333/cmdline` 的实际相机入口为 `.../pan-face-edge-v5/face-source-v17/entry.py`，SHA `f26be22cb640bf44a1bd81b66bb3fa014f5b847b13320781836bf3f173387623`。
- 沿原源码核对 `native_entry_operator.py`→`native_entry_pan_face_v5.py`→`native_entry.py`，最终生成配置为 `.../native-run-605eaf50-c66a-4559-bfc9-5ae177e0f305-1333/config.json`，SHA `ee088cf2c912a9440db2ebe000a0aded8c6ae5d907933bc12d37e40a74601d8d`。
- 真实 DPU 身份配置为 `/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-sface-int8-9025bd49fe52-333217/board_identity.sface_int8.json`，SHA `398ece6a4d5d81076c9a4f9f40a43e97cedd469e0b47e3a835e589a2255ca6e3`。
- 后端 API 确认 `DPU_SFACE_INT8`；主库采用 `sface-int8-12b2ff5c7de15713`/128 维及该模型专用私有 SQLite。源码确认 `identity_model_binding` 必须精确匹配此模型，不能使用旧 CPU 库或配置中的 fallback。

`camera_entry.json`、`camera_process_metadata.json`、`camera_source_index.json` 保存来源与摘要。只获取源码/配置；不复制模型、照片、身份库或模板。

## 已验证

- 34 项专项：完整实际回执、ACK/命令所有权、revision+1/唯一新增 ID、明确已有身份确认、状态/相机/图库变化拒绝、取消/迟到归属、仅摘要库存、SQLite 30ms 锁上限、原 FSM 三轮流程、实际 JSON 字节上限。
- 26 项原语音通道/身份查询/薄传输兼容，通过候选 overlay 运行。原登记 camera fixture 在 Windows 因 `fcntl` 收集失败已留档，没有伪造平台模块。
- 真实 ARM Python 3.9.9：8 个候选模块从 SSH stdin 在 RAM 编译加载；合成 codec、name-wait、原三轮 FSM→原命令/ACK/COMMITTED 回执通过。没有安装候选文件或触发真人登记。
- 同一次 ARM 只读检查按实际 DPU 配置打开 mode=ro 主库，模型绑定及 source pins 通过，仅读取模型/修订/数量作为证据：revision 1、1 模板。只在板内 RAM 校验并计算摘要；没有返回姓名、向量、照片或具体模板记录。

首次沙盒 Path.resolve 拒绝及一次测试快照遗漏 capability 的失败均保留。原父目录 49/55 专项和 115 兼容证据未改写，不与本轮计数相加。没有真人相似声纹、统一关联登记、多人/电视声、跨天或跨重启效果验收。

## 运行边界

`face_gallery_readback.local.json` SHA `9eb61314cb5155b6a87997e78b9856881be80fa3921146009804dc76cf2e0e74` 严格绑定本次 boot、相机 PID、start ticks、cmdline SHA，以及完整实际配置/源链 SHA。重启或相机代次改变后回执默认不可用，普通语音继续；不会自行重启相机或改写绑定。跨重启安全 refresh 尚未实现，不能宣称已验收。

后续只读 refresh 需要重新读取 actual systemd MainPID、`/proc`、相机运行源码引用链及本次生成配置，确认 DPU model、独立私有路径、dimension、源码 pins 与图库 binding；读取当前实际 snapshot 的 boot/epoch。只在核验一致后生成新 readback 配置、更新其组件 pin，并按父侧空闲双确认流程部署 UI。不能只替换旧 JSON 内的 boot/PID 来“通过”检查，也不能拿 pending unit 代替现役入口。现有 discover/read_config_chain 工具保留了本次发现步骤，但不是自动放宽绑定入口。

`INTEGRATION.md` 给出精确消息/组件与部署接点。只需父侧按实际入口一次整合 UI，保留并行 startup-speed 启动器字节/参数及相机进程；本子代理不部署、不重启、不真实登记、不开麦/播放/运动。
