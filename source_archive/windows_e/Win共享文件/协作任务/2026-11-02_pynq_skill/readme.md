# 通用 PYNQ Skill：离线初版

日期：2026-11-02。围绕用户“怎么做”的当前任务，在独立目录落实新 PYNQ 补充包；原 A/B/C 三包实现及设备任务未恢复。

入口：[包的使用说明](skill/pynq-contract-testgen/readme.md)。包名 `pynq-contract-testgen`，不依赖 AURA 业务目录、PYNQ 安装或第三方 Python 包即可完成离线生成与模拟验证。

交付：[离线初版 ZIP](pynq_contract_testgen_offline_v1.zip)，36,668 字节（约 36.7 KB），含 28 个源/说明/证据文件及校验清单；[打包回执](archive_report.json)。ZIP CRC、逐文件 SHA 和解压到新目录后两例复现均通过；[解压复现记录](validation/archive_reproduction.json)。

ZIP SHA256：`c6f2c56307677cc1f873910d30cae898ea138dc0e991fcf1b4802f2f07ae2ddc`。

## 已实现

- AXI4-Lite uint32 接口合同检查：实例、地址范围、寄存器偏移/位宽/权限、启动/完成和超时。
- HWH 静态校验：严格区分 MATCHED、INCOMPLETE 和冲突；支持不同逻辑名/HWH 名及 XML 命名空间。
- 生成 PYNQ 驱动、测试脚本、合同报告和使用入口，缺省只做软件模拟。
- 加法器与 CRC32 两例使用同一生成器，改变实例、地址布局、命令位和读清除语义；参考实现与模拟模型分开。
- 新目录复制复现、原始验证日志、代码/输入 SHA、ZIP 打包/CRC/清单校验。

## 实际验证

Python 3.8.10。15 项单元测试通过；生成后执行加法 36 例、CRC 37 例，共 73 例通过；在新的临时目录复制后再次通过，源码 SHA 一致。

证据：[汇总](skill/pynq-contract-testgen/evidence/offline_validation.json)、[单元测试原始输出](skill/pynq-contract-testgen/evidence/unit_tests.log)、[生成与模拟输出](skill/pynq-contract-testgen/evidence/reproduction.log)。

本次没有 PYNQ 导入/安装、固件加载、板卡访问或控制机构动作。真实 PYNQ、跨板、非作者复用均未验证。HWH 示例明确为合成解析样例；没有伪造位流或板测结果。

## 使用

进入 `skill/pynq-contract-testgen/`，执行：

```bash
python3 -B scripts/reproduce.py --out /tmp/pynq_demo_01
```

换成自己的 IP 时，替换合同、真实 HWH、向量和可选模拟模块，按包内 readme 重新生成。实际 PYNQ 验证须另备兼容环境与真实板卡工件，使用包内独立入口；本轮没有为此改变现役系统。

当前初版用于审阅和离线复用，不能据此声称完成官方作品验收或已获 PYNQ 加分。最终提交前仍需队伍核对实际资料、真实问答记录、许可与对应验证范围。
