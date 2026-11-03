板端紧凑普通对话协议组装候选（未部署）

基线：现役v13 startup ae47311619310420b3215770b676c48a9f1d8e3d33d02c72fa04e21186ec903b。
本目录before由主控从板端按完整组件pin读取；baseline_manifest.json保留完整父证据。
仅6份after源，见candidate_manifest.json/extra_source_map.json。其中3份为已审研究候选原字节，3份为本次组装/能力接线。没有覆盖BoardMemoryPolicy、BoardBusiness、BoardDialogue、Jobs、GTK或录音链。

配置：在原board_business对象中合并dialogue_output_format；仅允许json或dialogue_abc_v1，省略等同json。config.fragment.json默认json，部署前仍由主控依据真实ABBA决定是否改为dialogue_abc_v1。不要在顶层另造同名配置键，也不替换整个board_business对象。

启动：ProductionGuiBoardBusiness先沿原路径创建runtime、绑定形象人格、完成原initialize_clock的health Date采样，然后安装普通对话transport选择器。原HTTP角色、peer、头/长度、JSON重复键、同boot/期限/可信Date校验全部保留；成功后仅保留backend.format_contract_version=1/output_formats白名单副本，不保存其他health正文。capability getter只读RAM，不新增HTTP。缺失/旧版/错误类型/未知格式回退原JSON，不伪造能力、不拖长启动。

默认json时controller.model_client仍为原对象。显式compact时，仅controller使用NegotiatedDialogueClient；runtime.client和summary的原client对象保持。研究CompactRequestAdapter仍只改普通非think、exact selected静态prompt的三字段名，原用户/历史文本不变。完整响应收到后才还原canonical JSON，再进入原BoardDialogue/Store/分句/每包授权/播放ACK。截断、重复键等失败不追加JSON重试，不会提前释放片段。

现有空闲Date refresh会更新同一RAM能力快照，可在已观察到旧host后恢复JSON；不添加每轮探测。若Windows在两个既有采样之间更换为不支持compact的版本，旧能力快照可能暂存，届时请求按原错误/取消机制失败，不能重复发JSON掩盖故障。主控成套更换host/board或正常重启并重新采样即可重新协商。能力快照只是协议选择，不是身份或记忆授权。

元数据：组装对象dialogue_output.public()仅含configured_format、negotiated_dialogue_format、capability_verified/source、per_turn_health_requests=0及完整响应标记；没有新增公共HTTP接口。无需再开设备或模型做inspect。

必要依赖：
  common/model_inference_wire.py：已审研究扩展，允许显式output_format及新增纯数值timings。
  common/inference_output_contract.py：已审研究纯函数库，原字节复制。
  board/runtime/compact_request_adapter.py：已审研究适配器，原字节复制。
  board/runtime/board_dialogue_client.py：仅增加已验证health能力快照/getter。
  tools/production_output_format.py：新组装选择器，无IO/服务/模型/数据库。
  tools/production_board_business_gui.py：仅配置验证及initialize_clock后安装调用。
Windows必须成套采用独立研究候选的host/wire/contract，实际health在backend中声明版本与格式；板端不能靠配置假定能力。

验证：21个新主测试/30子例，通过0.15s；与研究侧合同合并68主测试/79子例，通过0.27s。实际执行的是完整生产构造函数（模型/身份/设备依赖为fake）、完整原HTTP Date client（内存fake socket/response）、完整原BoardDialogueController和fakeStore直到24kPCM/完整ACK；并非只做源码字符串断言。未执行设备、模型HTTP、GPU、真实库或板端操作；没有性能收益声明。

定向复跑（无需PYTHONPATH/安装依赖）：
& 'C:\Users\35870\.codex\visualizations\2026\10\09\01a12110-3ba4-7651-b3d7-2e6560916eb6\omnivoice-runtime-py310\Scripts\python.exe' -B -X utf8 -m pytest -p no:cacheprovider '<本目录>\tests\test_integration.py' -q

集成只采用extra_source_map的6项，保留主控并行v14记忆改动；不要整树回拷before。真实部署、host/board版本组合核对、公开ABBA及实际首声验收由主控串行执行。默认JSON可回退；回退显式配置也须按原正常闭合启动流程和重算pins，不能在运行中随意换controller。
