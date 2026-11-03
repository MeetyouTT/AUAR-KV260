# 验证证据

当前状态：离线工具初版。真实 PYNQ 环境、板卡执行、跨板及非作者独立复用尚未验证。

本轮 Python 3.8.10：15 项单元测试通过，两个例子共 73 组输入通过；在全新目录复制后复现通过，源文件 SHA 一致。这里的复现由本助手执行，不称为非作者独立复用。

- `offline_validation.json`：本轮固定环境、单元测试和两例生成代码模拟的汇总。
- `unit_tests.log`：最终单元测试的原始输出。
- `reproduction.log`：新目录执行生成器和两个例子的原始输出。
- `adder_report.json` / `crc32_report.json`：生成后的测试脚本逐例输出；mode 为 mock，board_verified 为 false。
- `ai_collaboration.md`：本轮可见任务与纠错摘要，非聊天平台原始导出。

HWH 样例、模拟 IP、黄金参考和软件耗时不能代替真实 PYNQ 加载、接口波形、综合实现或作品整机验收。
