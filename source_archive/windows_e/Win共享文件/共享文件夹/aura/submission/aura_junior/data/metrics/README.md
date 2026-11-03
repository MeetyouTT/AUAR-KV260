<!-- aura-architecture-generated -->
# data/metrics

<!-- aura-structure-details -->
## 复核后的目录职责

主责：A/B/C；运行/使用位置：实验分析。

内容：G0–G5、延迟、误差、覆盖、身份等待与分析入口。

边界：记录真实 run_id；空值代表未测，合成数字不填进板测对比。

依据：P3、C11，见 report/structure_detail.md 的依据登记。

现有来源：

- `config/experiments.json`
- `metrics/raw/framework-validation-20261009/validation.json`

目标目录已建立；本轮没有将实际源文件迁移到此处。
