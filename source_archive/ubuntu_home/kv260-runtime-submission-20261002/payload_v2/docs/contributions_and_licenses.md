# 来源、修改和许可

## 贡献范围

| 层次 | 来源 | 本次整理或已有修改 |
|---|---|---|
| DPU IP 与参考平台 | AMD / Xilinx | 来源说明；本附件不改 DPU 或硬件参考 |
| M3 AXI-Lite | 独立自研最小寄存器 | 已有限板测；源码、资源/时序属于硬件附件，尚未合并到本包 |
| DFX manager | Xilinx dfx-mgr 固定提交 | 只改 src/daemon_helper.c；watch 去重、表洞/边界、登记与删除互斥，容量仍为 500 |
| ZOCL | 固定 XRT 提交 | 只改 cu.c、include/zocl_drv.h、zocl_drv.c；平衡相关查询引用并注明 drvdata 所有权 |
| 本附件 | 项目过程整理 | 便携构建入口、来源锁、技能、只读观测与预检、复现和协作说明 |

不得把整个 AMD DPU 或全部 XRT 宣称为本队自研。上游声明和四个修改文件的原 SPDX/版权头均保留，没有修改厂商规则、降低内核诊断等级或增加 watch 容量绕过缺陷。

## 保留的许可资料

| 组件 | 文件事实 | 随包原件 |
|---|---|---|
| dfx-mgr | MIT | licenses/dfx_mgr_license.txt 及源树 LICENSE |
| ZOCL 三个修改文件 | GPL-2.0 OR Apache-2.0 | licenses/zocl_license.txt；XRT 快照内原声明 |
| XRT 运行时核心快照 | 包含不同用户态/驱动许可，按各文件声明 | licenses/xrt_license.txt 和原目录文件 |
| libdfx.h / libdfx.c | SPDX MIT | libdfx/LICENSE.md 保留 MIT 与 GPL-2.0 文本 |
| libdfx 的 dmabuf_alloc.* | SPDX GPL-2.0 | 原文件头保留 |
| libdfx 的 dma-heap.h | GPL-2.0 WITH Linux-syscall-note | 原文件头保留 |
| 本附件新文档与 Python 工具 | 本地附件按 MIT 整理 | licenses/annex_mit.txt |

上表是实际文件声明的清单，未把完整第三方源码统一改标 MIT。SDK、系统库、原镜像、XMODEL、原图片与 DPU IP 不随本源码附件分发；本次新构建中的库和头文件为外部输入。运行时测试二进制对应源码及补丁随附，未发布仓库。

英文字母路径检查结果见 evidence/naming_review.json。完整 XRT 快照的 xrt++ 与 Yocto % 配方属于本次 ARM ZOCL 构建之外的目录；完整快照保存在主机证据区，附件只导出文件内容不变的运行时核心及原许可。保留上游构建所需大小写与标准文件名。若提交平台严格执行全小写，需要确认其对 CMakeLists.txt、Makefile、SKILL.md 等工具入口的处理，不能用破坏构建的改名替代可复现性。
