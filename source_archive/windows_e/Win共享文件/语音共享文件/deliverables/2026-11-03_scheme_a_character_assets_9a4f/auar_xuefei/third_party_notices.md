# 来源与许可

根目录 `license` 是队伍既有权利说明，未指定一项新的整包公开许可。以下按组件保留原件和出处。

| 组件 | 来源和随包说明 |
|---|---|
| KV260 平台、DPU 与工具 | 使用本机授权的 AMD/Xilinx Vivado 和 Vitis 2022.2。`src/third_party/dpu` 保留组件、头文件及各源码自带声明。BD 使用工具安装的 IP 目录，安装介质和器件包由使用者自行准备。 |
| 原生角色运行时 | `src/native/avatar/native_integration/candidate_core/LICENSE` 为上游 AGPLv3 原文。`third_party_licenses` 保留 fast_float、nlohmann/json 的原许可与来源。适配层与核心分目录保存，组合发布的许可范围按 AGPLv3 第 5、6 节核对。 |
| 视觉输入 | YuNet MIT、SFace Apache-2.0 与 OpenCV 原许可在 `src/models/vision/licenses`，固定版本见 `src/models/readme.md`。ByteTrack 的两份同版源码各在其 board/vision/bytetrack 目录保留 LICENSE。 |
| 轨迹与字体 | Ruckig 及其随附依赖原许可在 `src/motion/trajectory_src/ruckig`，其它原始许可副本随转轴代码保留。Droid 字体的 Apache 许可与版权记录在 `src/assets/fonts/licenses`。 |
| 比赛 Skill | `skill/pynq-contract-testgen/license` 为 MIT。示例、说明、测试和原有离线证据属于该独立包。 |
| 模型和音频 | OmniVoice 0.2.1 为原主机安装源码的迁移副本，保留了已有文件内声明。外置权重的仓库、revision 与文件指纹见 `src/models/inputs`。选定的 soft_young 测试片段来自队伍的 Qwen3-TTS VoiceDesign 合成，选择记录和参考 SHA 随主机启动材料保存。 |
| 角色素材与系统镜像 | 本版收录9a4f正式角色的五件模型/纹理运行输入及匹配的ARM64渲染库，原件来源、大小和SHA见src/assets/yuki/manifest.json，素材原有来源与权利说明保留。SD镜像仍提供输入说明与哈希。公共数据集由使用者按其条件在包外取得，当前包不附基准人脸图像或其输出向量。 |

队伍原创独立代码可以在权利人选定后采用 MIT，根许可需明确其适用文件范围。MIT 授权保留版权和许可声明的要求见 [OSI MIT 原文](https://opensource.org/license/mit)。AGPLv3 对修改版及组合程序的分发条款见 [OSI AGPLv3 原文](https://opensource.org/license/agpl-3.0)。
