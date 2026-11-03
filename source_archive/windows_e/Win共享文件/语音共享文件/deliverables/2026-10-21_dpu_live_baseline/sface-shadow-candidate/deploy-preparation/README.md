# Shadow 短 pilot 部署准备

本目录仅为主负责人提供可审查的部署脚本，没有在板卡执行。候选原有 13 文件校验范围及直接身份冻结目录均未修改。

`board_shadow_pilot.py` 绑定当前已保留的 YuNet DPU runtime `81fdb11903abb71e-live-134783`、其服务单元 SHA、7 个基线源码 SHA、6 个 shadow 源码 SHA。它复制到独立目录，只追加无余弦/1000ms 间隔的 shadow 配置，保持原 Windows feature_backend、原库、阈值和照片策略；始终回退当前 YuNet DPU。

运行必须由主负责人明确控制时机，使用已经完整校验的部署包、boot ID、SFace模型和manifest绝对路径及SHA。部署包格式为 6 个源码和 patch-manifest.json；manifest 使用 `files:{rel:{sha256,bytes}}`、`baseline:{rel:sha256}`，并与脚本固定值完全匹配。

```sh
python3 -B /已暂存/board_shadow_pilot.py \
  /home/root/aura-dpu-vision-20261021/staging/d6f06aa970649c9e/bundle.tar.gz \
  --patch-sha256 d6f06aa970649c9e076ccc916ca0c5c3257dcf79639082dd026fa7e90fed95bc \
  --boot 215c4292-ce84-4828-9827-83c32ba66564 \
  --model /已校验kit/sface_public_int8.xmodel \
  --manifest /已校验kit/sface-manifest.json \
  --manifest-sha256 实际manifestSHA \
  --observe-seconds 20 --min-completed 3
```

以上含占位路径，需要主负责人替换真实路径；本目录不代替 UART 暂存或启动。推荐 systemd-run 异步运行、限定生命周期，再读取 `/home/root/aura-dpu-vision-20261021/shadow-pilots/d6f06aa970649c9e-*/deployment-result.json`。必须等待 `complete=true` 且 `rollback_verified=true`，中间报告的 passed 不能当最终完成。

预检包含单 camera PID/实际 DPU flock owner、当前源码/配置/单元、UI IDLE且无录音/转写在途、实际 face_count=1。预检不创建第二 DPU owner，不运行 xdputil 或 --check。准备独立原单元备份、5秒 CPU 基线、原 GUI PID 与原配置哈希后，先启动180秒回退 timer，再更换单元。

验收要求实际 `execution.completed>=3` 且目标/TTL复核后的 `accepted>=3`，YOLO≥8.5Hz、YuNet≥1.5Hz、无 optional overrun/降级、无新增 USB 音频告警、GUI PID及原配置保持。0次计算不会通过。无论测试是否通过都恢复原 YuNet 单元，恢复健康/源码/owner核对通过后才取消回退 timer；如失败则 timer 保持武装。

原生调用若卡死不能通过第二 owner 绕过。回退先停止原相机服务并等待原进程退出，再恢复单元启动；超时需保留回退及失败状态，不宣称成功。自动回退只接受备份的原单元或本候选单元字节，遇到其它后续修改会拒绝覆盖。

kernel cursor 使用 journalctl -k -n0 --show-cursor。若板端版本不返回cursor，会在服务修改前安全失败；主负责人可在受控执行 wrapper 中改成 -n1 并记录最终执行源码SHA。此处不重写已交付脚本。

本地 `python3 -B -m unittest -v test_preparation.py` 验证脚本/生成rollback语法、6个overlay与冻结源码哈希一致、合成临时单元能恢复精确YuNet原字节、后续无关单元在任何停止/写入前被拒绝。它不等于板上部署或真实模型验收，实际结果见 `local-test-results.txt`。
