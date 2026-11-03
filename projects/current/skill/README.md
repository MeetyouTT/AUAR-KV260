# 比赛 Skill

主包为 `pynq-contract-testgen/`。28 个原文件按原目录收录，入口和使用约定在该目录的 `readme.md`、`workflow.md` 与 `contract_format.md`。原包自带 MIT 许可。其用途是根据寄存器契约、黄金模型与输入向量生成 PYNQ 调用及测试骨架。

在工程根目录运行以下两条命令。第一条运行 15 项生成器单元测试，第二条生成加法器和 CRC32 用例并在 mock IP 上执行 73 个用例，输出写到新的包外目录。

```sh
(cd skill/pynq-contract-testgen && python3 -B -m unittest discover -s tests -v)
python3 -B build/reproduce.py --stage skill --out ~/auar-skill-test
```

原包内的 `evidence/` 属于较早记录。本次回执见 `report/validation_summary.md`。PYNQ 真板、跨板和非作者复用尚待单独验证。`src/skills/` 由雪妃业务运行时使用。
