# 单终端接续：首次迁移与新内核入口

用户改为只允许一个终端后，其他代理已中断/结束；后续实现、测试和板卡访问由root串行完成。冻结父版r1保持，r2代码在本目录。**没有重启板卡、切换服务或运行候选模型。**

本候选在实际214源底座上共222份Python：5份修改、8份新增，新增`native_boot.py`。C++ ABI v2完全沿用已冻结、已在目标板链接/常量验证的版本。

## 已补上的入口

1. 同boot仍只允许完整v2 seal/checkpoint；旧health不能当精确最终状态。同boot当前YuNet5/SFace3故障及LATCHED不会被清零或解除。
2. `allow_new_kernel_boot`缺省false；只有从`/proc`读到真正不同的kernel boot，才能归档旧计数并生成新计数域。旧单调时间不重放，旧故障/恢复/SFace累计保存在受控0700目录，文件/目录fsync。
3. 首次从旧版进入原生路径还须`allow_legacy_new_kernel_boot=true`。仅接受明确的`aura-native-legacy-boot-archive-1`包装、hash固定payload/完整源码manifest、来源boot/PID/出生时间/unit；目前支持`legacy_health_prefix_lower_bound`，未实现另一种protected-handoff包装。所有已知故障必须有status0/完成证据，fenced或未知完成拒绝。历史明确标为下界及unknown tail，绝不伪装成精确checkpoint。
4. 每个当前boot只有一个消费marker，不含seedhash，换seed也不能重新得到预算。归档和marker必须在Context创建/restore/adopt前完成；partial/fsync失败后保留已消费事实、拒绝重试。旧版采样期间不要求停止业务，也不宣称快照后没有新计数；只有新kernel边界才允许这一明确的新域入口。
5. 归档hash链接进入后续seal checkpoint，同boot重启只承接一份引用，不重复嵌套或丢失旧kernel记录。

模型/身份INT8域/阈值/数据库保持；实际启用仍须原YOLO架构与reference/blank检查。这些启动自检不会计作恢复所需的业务primary推进。重启不同kernel本身不等于模型效果/硬件重初始化已经验收。

## 实际验证

- 62项业务/新boot/legacy bootstrap检查通过，使用fake kernel/clock和真实数字故障样本，无设备操作。
- 原237项运行：235通过、2项私有ELF检查跳过、0失败/错误。GUI消费者按实际175源版本单独只读overlay。
- 所有222源逐SHA/AST通过；C/ctypes ABI、C++源及绑定接口没有改变，沿用父版12项真实CDLL/fake模型往返结果。
- 板上已在独立目录准备222源和拟用配置；仅调用preflight，当前真实boot正确拒绝legacy seed。没有创建Context/runner、没有推理/服务变更/重启，前后PID及5/3故障计数不变。

首次exact新boot测试曾有失败，中间记录保留；最后结果在`test-r2-final.log`和`test-r2-project-final.log`。`tests/fixtures/legacy-boot-archive.json`仅为数字故障/代码SHA样本，没有图像、向量或身份库。

冻结代码`native-v2-d7256b06808509c9`；实板预备目录`/home/root/aura-native-critical-20261024/candidates/native-v2-d7256b06808509c9`，配置`board_camera_ui.proposed.json`。**该配置未安装到systemd，不应在当前boot强行运行。** 真实模型原始INT8等价、正常三模型吞吐/帧龄/CPU与DPU收益、实际冷启动和长期业务仍待验证，不能称已根治或正式启用。
