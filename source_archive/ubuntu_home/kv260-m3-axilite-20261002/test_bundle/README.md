# KV260 M3 独立测试包

本包包含新构建的 DPU＋最小 AXI-Lite 寄存器配置。主机打包与静态一致性核验通过；板端尚未加载和验收。

先在本目录执行 `sha256sum -c SHA256SUMS`。只安装 `lib/firmware/xilinx/kv260-benchmark-b4096-m3/` 的四个运行文件，目标已存在则停止。

`provenance` 是审阅资料，不可写入 /boot、SD 整盘或 QSPI。`board/m3_board_check.py` 默认仅检查元数据，不切换应用；identity/scratch 是候选加载后的显式步骤。

完整操作、停点与恢复见 [M3_TEST_CARD_PLAN.md](docs/M3_TEST_CARD_PLAN.md)。旧 overlay 引用计数问题仍未解决，不能自动反复切换。
