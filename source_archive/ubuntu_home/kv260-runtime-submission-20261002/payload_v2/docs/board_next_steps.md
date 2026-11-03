# 板端下一步与恢复

无需再次烧录 SD 卡。继续使用已保存基线的备用卡，网线可保持直连 Win11；Ubuntu 自动执行仍需要板卡电源和 USB 串口。当前没有新的板端连接证据。

## 先执行新的只读预检

将本附件的 scripts/board_preflight.py 与 config/ 中 source_lock.json、baseline_inputs.json 复制到独立板端目录。目标板 root 下执行：

```bash
python3 -B scripts/board_preflight.py --config config
```

脚本只读取状态，不切换。它核对本次卡号、根分区、内核、原驱动、26 个原文件、原服务/daemon、活动应用和 DRM/模块占用；输出新的 boot ID。发现差异即返回失败，不能因此直接覆盖文件。Ubuntu 上执行会拒绝，把它当板端预检通过是不成立的。

## 启用与复验

1. 保存本次独立恢复点：原 daemon、client、unit、配置、VART、ZOCL、固件、完整内核日志及模型/图片/文件哈希。核对 tested_inputs/ 两个输入与配置的哈希，不使用 host_rebuild/ 新 daemon 代替已板测候选。
2. 正常卸载活动官方应用，确认无其它活动包/DRM 客户端/模块持有者，停止原服务并正常替换加载的 ZOCL。记录原驱动退出可能出现的已知引用错误。
3. 用临时、独立 systemd 配置启动修复 manager，日志写到本次目录。核对 PID/exe 和 SOCK_SEQPACKET 就绪，再用原客户端检查功能。脚本连接成功不等于 DPU 验收。
4. 加载官方应用，核对 1 CU、B4096、300 MHz、0xa0010000、0x101000056010407，复跑哈希一致的原 ResNet18 和原图。完整 Top-5 须一致：258 Samoyed 0.949879、270 white wolf 0.00931229、259 Pomeranian 0.00821807、257 Great Pyrenees 0.00498451、279 Arctic fox 0.00388194。
5. 计划 30 轮受控重载及同图推理，随后至少 30 分钟推理与 RSS、MemAvailable、Slab、inotify、ZOCL refcnt、完整日志采样。每轮卸载前重新核对无客户端；发现新增目标引用错误、异常或 manager ERROR 停止，保存现场。采样工具在 skill/ 中；控制器需根据本次 boot/state 生成，旧控制器不重放。
6. 再核对 M3 查询和同图结果。本阶段没有 PWM 或执行器操作。

**上述受控启用和扩大复验本次未执行。** 永久启用与重启验收也未准备成自动安装器，须在临时复验通过后审阅实际启动顺序和恢复入口。

## 恢复

按实际状态正常移除活动应用；用原 SIGINT 刷新候选日志后停服务；恢复原服务，再恢复原 ZOCL 参数/模块、原 VART 和官方应用。最后逐项核对 26 文件哈希、DPU/同图结果、活动 slot、boot ID 和完整日志。

没有固件加载错误/占用分析前不 force 卸载或重试。已有 overlay 属性警告、重复 /boot 配置和 DRC/时序问题仍保留，不以本次软件修复声称已全部消除。
