# PYNQ Contract Testgen

接口契约驱动的 PYNQ 调用与测试骨架生成工具，比赛 Skill 离线初版。

适用范围：具有明确启动/完成合同的 AXI4-Lite、32 位无符号标量寄存器 IP。生成器和示例验证只需 Python 3.8 及以上标准库，Windows 可将下列 `python3` 改为 `python`。

当前交付层级：契约与 HWH 静态检查、代码生成、软件 IP 模拟。没有已验证的 PYNQ 环境、真实 bitstream、PYNQ 板测或跨板运行证据。示例 HWH 是明确标记的合成解析样例，不是可直接供 PYNQ 加载的完整 Vivado 元数据。

## 1. 先运行完整示例

在本目录执行，输出目录应尚不存在：

```bash
python3 -B scripts/reproduce.py --out /tmp/pynq_demo_01
```

此入口用同一个生成器处理加法器与 CRC 两种布局，核对固定黄金结果，再各生成 32 个固定种子的随机输入。它执行生成后的测试脚本，输出 `summary.json` 及每例的 `validation_report.json`。成功时 `status` 为 `PASS`，`board_verified` 始终为 `false`。

这些耗时是主机模拟/调用耗时，不代表 FPGA 性能或加速比。

## 2. 单独生成和运行

```bash
python3 -B scripts/generate.py --contract examples/adder/contract.json --hwh examples/adder/metadata_fixture.hwh --vectors examples/adder/vectors.json --mock examples/adder/mock_ip.py --out /tmp/pynq_adder_01
python3 -B /tmp/pynq_adder_01/test_ip.py --mode mock
```

生成 `driver.py`、`test_ip.py`、规范化合同、测试向量、契约报告与说明；提供了模拟模块时将其复制为 `mock_ip.py`。默认拒绝覆盖已有生成目录，不在代码生成阶段执行模拟模块或访问硬件。

## 3. 怎样换成你的 IP

1. 按 [合同格式](contract_format.md) 写接口合同，真实偏移来自你的寄存器表，不能凭模型猜测。
2. 准备真实 HWH。若用于真实 PYNQ 后续验证，将 `metadata_source` 设为 `vivado_export`，并保留来源与版本。
3. 提供逐例输入和黄金期望值。运行前会检查名称、整数范围和字段是否齐全。
4. 可选提供独立模拟模块 `create_ip(contract)`，返回具有 `read(offset)` 和 `write(offset, value)` 的对象。模拟模块是使用者提供的 Python 程序，应与参考结果独立核对。
5. 重新执行生成命令，只改输入资料，不改生成器核心。

生成器检查寄存器偏移/位宽/访问权限与 HWH 的一致性；它不从 HWH 推断完整算法、控制语义或正确参考输出。若元数据只含地址窗口而没有寄存器定义，默认失败；显式使用 `--allow-incomplete-metadata` 时可以生成骨架，但报告状态保持 `INCOMPLETE`。已知冲突不能用此选项绕过。

## 4. 后续真实 PYNQ 验证

这一步尚未执行。需使用合适 PYNQ 环境、目标板对应的 `.bit` 与同名 `.hwh`，HWH 的 SHA 必须与生成时输入一致，实际硬件必须满足合同。官方 API 见 [Overlay](https://pynq.readthedocs.io/en/latest/pynq_libraries/overlay.html) 和 [DefaultIP](https://pynq.readthedocs.io/en/latest/pynq_package/pynq.overlay.html)。

用真实资料重新生成后，在对应 PYNQ 板上按以下入口运行，路径需替换为实际文件：

```bash
python3 test_ip.py --mode pynq --bit /path/to/overlay.bit --report board_report.json
```

该入口使用 `Overlay(..., download=False)`；未加载时会报错。只有显式增加 `--program` 才下载 Overlay。示例合成元数据不能进入硬件模式。元数据不完整时，须审阅合同并显式指定 `--accept-incomplete-metadata`，报告不能补造静态已验证字段。

真实测试报告中的板测通过只针对该 IP 的指定输入，不证明整机功能、机械输出、跨板或长期可靠性。不同板卡需各自的 bit/HWH 和已核对的环境。

## 5. 验证与打包

```bash
python3 -B -m unittest discover -s tests -v
python3 -B scripts/package.py --out /tmp/pynq_contract_testgen_01.zip
```

打包脚本创建新 ZIP，加入 SHA256 清单，复查 CRC 与每个文件的 SHA，严格要求小于 200,000,000 字节，并排除 Python 缓存。原始文件保持不变。

详见 [工作流](workflow.md)、[真实观察与纠错](case_studies.md)、[验证证据](evidence/readme.md)。本工具没有安装系统、加载固件、模型推理或控制机构的自动步骤。

## 6. 失效条件与限制

- 首版不支持 DMA、AXI-Stream、中断、浮点/有符号数、多字寄存器原子性或其他完成协议。
- `start.value` 是整个命令寄存器的写入值，不执行隐式读改写；完成标志必须按合同在启动时清除。输出数据寄存器须无读取副作用，完成寄存器可声明读清除。
- 缺少、冲突、未知协议均不能自动当作正确。HWH 静态匹配不证明 bitstream 与硬件行为一致；读写副作用和算法语义仍由合同及实测确认。
- 超时检查发生在寄存器读写调用之间，不能中断已经阻塞的底层 MMIO 调用。收到完成标志但观察时刻已超时，仍判超时。
- `examples/` 提供的是独立软件模型与合成 HWH，未提供 RTL/综合/时序或可上板位流。它们用于验证生成器的复用，不代替作品本体的板级验证。

许可证见 [license](license)。本包为项目自建工具，不代表 PYNQ 官方组件或官方评分承诺。
