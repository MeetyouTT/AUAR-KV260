# 方案A：运行根与配置收集说明

用途：供后续工程的 `src/config/readme.md` 直接参考。本文是说明，未创建业务配置或执行软件/硬件测试。

## 1. 运行根

`src/` 对应原 `aura/` 根：`board/`、`host/`、`common/`、`ui/`、`tools/`、`config/`、`models/`、`assets/`、`data/`、`hardware/`、`tests/` 等按原相对位置收录。

`common/config.py` 保持 `PROJECT_ROOT = Path(__file__).resolve().parents[1]`，打包后自然指向 `src/`。相对模型、配置、数据路径均从这里解析；RAR顶层的投稿数据目录不是此运行根。

如某入口需要设置 `PYTHONPATH`，应指向 `src/`（`common` 的父目录），不能只指向 `src/common/`。既有 `tools/aura_project.py` 已加入自己的运行根，无需重复修改。其他入口逐个核对，不假设都具备同样的启动逻辑。

## 2. 主配置：严格校验

`load_config()` 默认打开 `config/runtime.sim.json`，路径相对于运行根。`validate_config()` 要求顶层键精确等于：

| 键 | 内容 |
| --- | --- |
| schema_version | 固定为 `aura-project-1` |
| release_id | 非空的真实版本标识 |
| environment | `simulation`、`reference`、`kv260` |
| vision | 后端、跟踪、目标选择、模型及观测参数 |
| freshness | 有效期策略及对应参数 |
| scheduler | 调度策略、成本估计、身份周期 |
| motion | 此框架允许的运动后端和物理执行标志 |
| identity | 身份后端、维度、阈值、歧义、缓存 |
| dialogue | 后端、超时及说话人阈值 |
| logging | 日志设置，沿用实际有效配置 |

嵌套字段继续参与校验，不能只填写十个空对象。应由完整有效的原配置脱敏。此校验器属于既有框架，明确禁止其直接开启物理运动；`runtime.kv260` 这个文件名本身不表示正式整机运行已就绪。

推荐收集：

| 包内文件 | 使用方式 |
| --- | --- |
| runtime.sim.json | 无敏感内容时原名收录，供默认doctor/demo |
| runtime.experiment.sim.json | 实际采用才收，保留原名和完整结构 |
| runtime.reference.example.json | 完整脱敏模板，使用前生成实际文件或明确传入此模板路径 |
| runtime.kv260.example.json | 完整脱敏模板，设备准备时按原profile/入口生成实际配置 |
| model_manifest.json | doctor硬编码读取，保留原名和有效结构；只含清单，不含权重 |
| source_import_manifest.json | 脱敏来源记录，保留结构与真实版本关系 |
| servo_calibration.example.json | 安装时生成原程序期望的文件名，标定项如实填写 |
| toolchain_lock.json | 与build/env.json保持统一来源，由流程派生/核对，不能手工维护矛盾版本 |

若某配置没有需要隐去的字段，可保留原名；不强制所有JSON改成example。

## 3. 子系统配置：按各自加载器

GTK、相机、身份、音频、模型服务等可能直接读取JSON或要求 `*.local.json`。不套用主配置的十键校验，也不凭文档新增一套原代码不支持的覆盖顺序。

`board/deploy.json` 逐项记录：模板源路径、实际目标路径和文件名、必填本机字段、资源/模型根、权限、解释器、工作目录和消费者。

例如，`board_avatar_gtk.example.json` 应生成 `board_avatar_gtk.json` 还是其他路径，由实际入口决定；`model_storage.example.json` 若对应代码的 `model_storage.local.json`，生成后才使用该名称。不能把所有example统一改成local。

共享目录内不放27B等大语言模型权重、下载分段、Ollama模型库或外部权重目录联接。公开配置用明确占位与准备步骤，本机数据由所属设备初始化，不能把私有路径、身份模板、真实数据库和密钥写进公开包。

## 4. 正确的CLI路径示例

从RAR根目录运行，以下是后续复核命令示例，本轮未执行：

```bash
python3 src/tools/aura_project.py --config config/runtime.sim.json doctor
python3 src/tools/aura_project.py --config config/runtime.sim.json demo --out /tmp/auar_framework_demo_01
```

`--config` 已相对于 `src/`；写成 `src/config/runtime.sim.json` 会再拼接一层src。`--out` 每次选择尚不存在的新目录。

使用example作为参数时，也必须满足其真实加载器，并准备其另外固定读取的文件；特别是doctor还会读取原名 `config/model_manifest.json`。

## 5. 自检结果能说明什么

doctor只检查所选profile的部分依赖和输入；模拟profile返回0不能代替真实模型、GUI、音频、转轴和Windows服务验收。其能力字段含旧框架状态，不能直接抄进当前正式报告。

原 `scripts/package_project.py` 的 `FRAMEWORK_SOURCE_BUNDLE_NOT_DEVICE_RELEASE` 白名单可作历史参考，不是最终整机收集真源。最终文件版本由实际发布清单决定，较新交付修订与独立服务入口须另行回收。

配置和路径格式可静态检查；完整软件自检、构建和部署只有实际执行后才能记录通过。当前仍按用户要求不构建。
