# GUI CPU 同输入验证与现役恢复（2026-10-23）

**GUI候选未部署。** 修正版164帧逐像素一致，但待机渲染的进程CPU仅下降 **5.4643%**，未达到预先声明的10%门槛。正式GUI源码、原native库、8fps配置均保持。这个数字只对应headless像素路径，不是整板CPU降幅。

**现役已同版本恢复：** camera499773 / GUI450525 / Xserver1077，boot `7924ac9f-311d-4fcd-98be-57bf023cf1aa`、camera unit `29786434…`保持。YOLO和YuNet实际DPU运行，SFace后端`DPU_SFACE_INT8`就绪；恢复后本窗口SFace没有新请求，不能称三模型持续混跑或身份精度验收。

## 同输入结果

相同现役素材、seed20261023、时间序列和native threads=3；按baseline/candidate/candidate/baseline测进程CPU，包含native工作线程。计时排除素材初始化。共享只读素材，分别重置播放/身体/瞬态状态。

| 指标 | 原路径 | exact融合候选 |
|---|---:|---:|
| 待机计时帧 | 64 | 64 |
| 进程CPU总用时 | 2857.724818ms | 2701.569070ms |
| 每帧平均CPU | 44.651950ms | 42.212017ms |
| CPU下降 | — | 5.464338%，未过10%门槛 |

7组共164帧：待机32、说话16、倾听8、点头8、微动关闭8、说话退出28、说话池轮换64；RGB和所检metadata全部一致。22组native校验比较2,165,691个RGB通道值，最大差0；重编库的旧入口在所测输入上与现役库一致。18项Python行为/分发测试、最终3项基准/封装测试和3项旧C++分支结构检查通过。软件假ABI/源码检查与ARM实测分别记录。

候选仅涉及以下源码，均在`source/candidate/aura/`：

- `tools/idle_body_compositor.py`：仅安全的IDLE分支推迟身体插值。
- `tools/realtime_facials.py`：约束启用条件，保留说话/动作/关闭微动的材料化路径。
- `tools/native_pixels.py`：exact代理和专用入口；端点不污染原代理。
- `tools/native_pixels.cpp`：新增exact入口，明确FMA以匹配现役float截断；旧API保留原分支。

现役融合是Q16，原材料化插值是float。首版IDLE最差帧mean0.21727超过0.1，已拒绝；第一次float NEON仍因乘加分步舍入产生max1/1070通道差异，再次拒绝。最终明确`vfmaq_n_f32`后实测一致，仍因CPU收益不足未部署。**未降低画质门槛、帧率或30ms/5ms保护。**

## YuNet故障与恢复

原camera450495本轮观测到3次硬占用超限：35.295113 / 31.706147 / 30.362253ms；均native status0、正常完成、未越guard，前两次自动恢复，第三次因600秒内两次额度耗尽而LATCHED退CPU。它们与测试时间的先后关系有记录，尚不能把并发负载、GIL或VART认定为唯一根因。旧故障和计数保留在恢复前快照中。

所有额外测试结束后，只进行了一次原相机版本的显式重启：核对源码/配置/库，原进程正常退出status0，确认DPU设备句柄与owner锁释放，再启动同一unit。GUI、偏好和模型/身份数据保持。首次恢复预检错误地寻找`/dev/dpu*`，实际板上使用`/dev/dri/renderD128`，因此预检拒绝、没有停服务；修正为实际节点并同时检查既有owner锁后才执行。

新进程60.214秒：YOLO **9.9644Hz**、人脸发布 **3.7367Hz**，未新增optional或主周期超限、gap。旧进程3次故障没有被解释成消失；新进程计数因这一次显式重启重新开始，跨此恢复的总数仍为3。最终源核对、单owner、原回退入口`--check`通过，恢复controller/timer及额外测试均已结束。

随后10.171秒普通负载点测：整板CPU **63.25%**，GUI进程组 **38.40%**，相机 **21.94%**，Xserver进程组 **1.95%**（均以整板CPU时间为分母）。这不是配对输入或优化收益；没有新采DPU busy百分比。

另3.023秒线程定位中，GUI `queue1:src`约占单核36.71%，是该样本最大的单线程项；另有多个Python/native线程和常驻音频worker。它支持下一步辨认实际视频pipeline成本，不足以证明某个组件有缺陷或可直接关闭。

## 证据与复用

- [最终源/服务/CPU与完整恢复快照](evidence/final-audit.json)
- [最终同输入结果及四轮原值](evidence/exact-v2-result.json)
- [独立最终门槛判断](independent-review/FINAL_GATE.md)
- `evidence/failures/`保留超时、画质失败、FMA失败和恢复预检失败。
- `source/`保留候选、基线、基准脚本、helper与测试；`SHA256SUMS`校验交付文件。

离线重跑行为测试需要完整AURA依赖目录和已有PIL/NumPy环境：`AURA_SHARED_SOURCE=/path/to/aura python3 -B -m unittest discover -s source/tests -p test_gui_cpu_review.py -v`。其余两个测试仅用标准库。板端helper绑定本boot、源SHA和旧PID，已有报告时会拒绝覆盖；不可不经复核直接重放恢复脚本。这里没有Windows回执、身份原库、权重、真人照片/音频/向量或原始串口日志。

下一项应定位真实GUI各进程/线程的CPU成本，当前headless结果已证明这处材料化只是有限收益；同时保留YuNet保护并继续调查准入后/提交中的等待。罕见长尾、SFace有界自动恢复、陌生人/多人、冷启动和整机长稳仍未完成。
