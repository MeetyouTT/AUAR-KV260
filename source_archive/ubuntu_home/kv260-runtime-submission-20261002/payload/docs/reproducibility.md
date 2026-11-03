# 固定源码复现

## 环境与外部输入

主机为 x86_64 Linux，使用已有 Vitis 2022.2 AArch64 SDK。实际新构建查询到 GCC 11.2.0、CMake 3.21.1；并行度 4。脚本只清理子进程环境，不修改全局 shell 配置。

需要 Python 3、patch、make、SDK 的 CMake/交叉工具链、SDK DRM 头文件和 chrpath。DFX 链接库须来自原测试镜像：libdfx.so.1.0，SHA-256 `1acb6c9ac1f27e0ea769dc231f32db5565f6ca02a53be00e969fc48c038d290f`。它是外部链接输入，本附件不带原镜像或系统运行库。

离线 ABI 检查还需原镜像四份运行库及其可执行 loader，和已有 qemu-aarch64。目录布局与哈希见 [runtime_requirements.json](../config/runtime_requirements.json)。构建不启动 daemon；QEMU 只运行镜像 loader 的 `--list`。

## 1. 从附件准备源码

从本附件根目录执行，路径是示例，需要替换外部输入位置。工作目录必须尚不存在；失败目录保留，不盲目重跑。

```bash
python3 -B scripts/prepare_sources.py --workspace /tmp/kv260_runtime_01
```

此步骤不联网：校验 XRT 运行时核心快照及两份补丁；原始树应用补丁时 fuzz=0；对 DFX 全树和所导出的 XRT 840 文件检查预期哈希。完整上游原始快照仍保留在主机证据区，正式附件没有改名或修改厂商源码来处理其无关目录中的特殊字符。没有修改原工作目录。

## 2. DFX manager

```bash
python3 -B scripts/build_dfx.py \
  --workspace /tmp/kv260_runtime_01 \
  --sdk /path/to/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux \
  --libdfx /path/to/original/libdfx.so.1.0 \
  --chrpath /path/to/chrpath \
  --jobs 4
```

构建入口为原上游 CMake 的 `dfx-mgrd-static` 和 `dfx-mgr-client-static`；名字中的 static 不表示最终程序完全静态链接。保留原 -Werror，采用已有成功构建的 -O2、FORTIFY、栈保护、branch protection、RELRO/NOW；剥离 debug 后删除主机 RPATH，并检查 AArch64 ELF。

需要同时执行离线 ABI 验证时，在同一命令添加：

```text
--runtime-root /path/to/extracted/image_runtime
--qemu /path/to/qemu-aarch64
```

输出与完整命令/日志在新工作区 `artifacts/dfx/`、`logs/build_dfx/`。脚本再次核对源码和链接库，源文件变化会拒绝构建。本次两个独立工作区的 daemon .text 哈希相同，完整 ELF 哈希不同；.rodata 中可观察到不同源路径。没有通过新编译标志改写厂商源码来追求相同 ELF 哈希。

## 3. 匹配内核和 ZOCL

内核固定 commit `19984dd147fa7fbb7cb14b17400263ad0925c189`；原镜像配置在 `config/kernel.config`。源码未打入附件，优先使用本机已有且固定、无 tracked 改动的 linux-xlnx checkout。只有缺失时才在独立目录取官方固定提交：

```bash
git init /tmp/kv260_kernel_source_01
git -C /tmp/kv260_kernel_source_01 remote add origin https://github.com/Xilinx/linux-xlnx.git
git -C /tmp/kv260_kernel_source_01 fetch --depth 1 origin 19984dd147fa7fbb7cb14b17400263ad0925c189
git -C /tmp/kv260_kernel_source_01 checkout --detach FETCH_HEAD
```

依次执行以下三阶段；上一阶段失败时停止，保留日志。full kernel 与 modules 会使用较多时间和空间。

```bash
python3 -B scripts/build_zocl.py prepare \
  --workspace /tmp/kv260_runtime_01 \
  --sdk /path/to/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux \
  --kernel-git /path/to/fixed/linux-xlnx --jobs 4
python3 -B scripts/build_zocl.py kernel \
  --workspace /tmp/kv260_runtime_01 \
  --sdk /path/to/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux --jobs 4
python3 -B scripts/build_zocl.py module \
  --workspace /tmp/kv260_runtime_01 \
  --sdk /path/to/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux --jobs 4
```

prepare 只读导出原 git，配置、.scmversion 与生成文件均写到新工作区。olddefconfig 仅允许 CONFIG_CC_VERSION_TEXT 的原有差异；kernelrelease 必须为 5.15.36-xilinx-v2022.2。KBUILD 用户/主机/时间戳使用原成功构建的固定输入，实际执行时间另记入日志。

kernel 阶段生成完整 vmlinux/modules 和 Module.symvers；module 阶段才按上游 Makefile 编译模块。未启用 KBUILD_MODPOST_WARN，未修改版本字符串或 force 加载。运行时核心导出覆盖旧完整构建 .cmd 中的 69 份 XRT 源码/头文件依赖，没有遗漏。XRT 原仓库的 PCIe libqdma 子模块不参与 ARM ZOCL，本附件不把它称为已获取依赖，也不提供完整 PCIe/XRT 工具构建入口。

**本次没有执行这三个 ZOCL 编译阶段。** 旧阶段完整执行并通过；新脚本完成语法和入口检查，移植入口还需在新工作区完整运行以验收。新模块生成后应重新审阅 modinfo、符号与板端结果，不能仅凭 vermagic 相同安装。

## 验证边界

本次构建复用本机已安装工具和原镜像提取库，不属于陌生主机从零安装复现。新 daemon 未上板；候选的有限板测属于 `tested_inputs/` 对应原哈希。附件没有 Vivado/Vitis 安装包、DPU IP 许可交付、完整 AURA 应用或 SD 镜像，也不含板端安装器。
