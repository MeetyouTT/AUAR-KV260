# AMD 自主选题初级组提交要求

核对日期：2026-11-01（America/Los_Angeles）。用户给出的仓库正式名称为“自主选题赛道”，提交内容以完整指南第3.3.5节为主。

## 核对依据

- [仓库入口](https://gitee.com/Vickyiii/fpgachina26-amd)本轮显示master为e47e4a81c2a6a35dbd0b25dcaa4d2edef9daf643。本机/home/ghmd/fpgachina26-amd的HEAD相同、工作树干净，两指南对HEAD的diff为空。
- [完整指南](https://gitee.com/Vickyiii/fpgachina26-amd/blob/master/TRACK_GUIDE_2026.md)：3.3.1资格、3.3.3设计约束、3.3.5提交、3.3.6赛程。
- [分赛道指南](https://gitee.com/Vickyiii/fpgachina26-amd/blob/master/tracks/open-topic/GUIDE.md)供按赛道阅读；冲突时以完整指南及官方公告为准。
- 线上正文页/Raw抓取失败；本机网络先被沙箱阻止，获准主机重试后SSL握手超时。因此正文依据已核实提交号的本地同版文件，未声称重新下载成功。
- 完整指南SHA256：aa8c1880538663e106ed88d8a70fc864e6faa68a652f907d9b86a034cdfd0753。分赛道指南SHA256：bd57e4f8b911bd7b872eab51000576512b542410a7eca6166c31d319de0d5678。
- 官网入口本轮抓取超时，未进入队伍后台。附件格式、大小、视频要求、上传分栏和最终回执未验证。

## 指南明确要求

初级组面向大一至大三本科生，可用AMD FPGA/Zynq；队伍如含更高年级/学历者按指南归高级组。初级和高级提交内容相同，分组评奖。

| 材料 | 应有内容 |
| --- | --- |
| 完整工程 | 实际使用的RTL/HLS/PS软件、完整工程输入及关联依赖。 |
| 验证与实测 | 仿真或测试结果、正确性依据、板端输出及与参考/基线的对照。 |
| 综合实现 | 资源、时钟、时序和关键性能数据及报告。 |
| 构建运行 | 可复现脚本、部署/运行入口、从零复现步骤。 |
| Skill | 放在skill/，说明适用范围、用法、失效条件、已验证效果和提炼来源。可以是提示词流程、模板、校验脚本或结构化排错方法。 |
| 设计报告 | 背景创新、原理框图、软硬件划分和接口、优化前后对照、复现说明。 |
| 大模型协作记录 | 真实提示词、回答、自我纠错；智能体流程（如有）及Skill如何提炼、验证和确定边界。 |
| 开源 | 自己的GitHub/Gitee仓库及允许再分发的开源协议，指南推荐MIT/Apache-2.0；第三方内容保留其原许可。 |

PYNQ是推荐路线，通用PYNQ Skill另行加分；Skill本身为提交要求。工具推荐2026.1/2025.2，其他版本允许说明并保证脚本复现，因此AURA现有2022.2可依该规则继续使用。

目录和文件采用英文命名，正文可中文。src/sim/build/board/data/skill/report为推荐结构；其他结构应在README给出对照。

## AURA工程包怎么整理

下面是项目打包建议，不是后台附件格式规定：

    aura/
      readme.md
      license
      third_party_notices.md
      src/fpga/
      src/board/
      src/pc/
      build/scripts/
      build/reports/
      build/artifacts/
      board/firmware/
      board/config/
      board/scripts/
      sim/
      data/
      models/model.md
      skill/readme.md
      report/design_report.pdf
      report/ai_collaboration/
      demo/
      checksums.sha256

- src/fpga：实际联合DPU/运动IP的RTL、BD/Tcl、XDC、IP及工程输入；工程文件依赖要完整，路径应能在其他机器复现。
- src/board：KV260相机、三模型调度、身份/跟随、ASR/音频、业务/记忆、GUI、Native源码和构建方法。
- src/pc：Windows现有27B/OmniVoice推理服务及协议、依赖、配置和启停入口。
- build：重建脚本、工具锁、资源/时序/实现报告，配套BIT/XSA等实际生成物。
- board：实际采用的.bit.bin、.dtbo、.xclbin、shell.json、运行配置、服务脚本和校验清单。
- sim/data：测试方法、输入、参考输出、实测数据和指标；每项数字可追溯到版本及测量条件。
- models：模型来源、版本、许可、SHA与取得/编译/准备方法。大型语言模型权重仍放共享目录外；板端必要资源按许可和复现需要提供。
- skill/report：可复用经验、完整报告和真实AI协作记录；演示附件按后台实际要求准备。

指南按实际采用的实现方式收工程内容，没有列所有作品必须额外提交通用裸机ELF的要求。当前Linux Python/C++实现应交其真实源与构建部署内容。

现有submission/aura_junior仍标注FRAMEWORK_NOT_FINAL_COMPETITION_RELEASE。应用380项对应字节虽已定位，还需收拢独立相机、原25文件控制器、FPGA、模型、Windows和系统依赖，组成同一冻结版本。

## 最后怎样提交

1. 在团队自己的GitHub/Gitee开源仓库整理最终工程，固定tag/commit，写清许可、环境、模型准备、构建及运行步骤。用户所给AMD仓库是指南入口，作品工程包由参赛队自行组织。
2. 从冻结版本导出交付目录，核对外部依赖和路径。建议生成aura_submission_v1.zip并保存校验和；指南没有指定必须ZIP/RAR，也没有给出单附件大小限制。
3. 从[大赛官网](http://www.fpgachina.cn/)进入实际报名队伍/作品后台，按AMD自主选题初级组对应页面提交。工程、报告、视频、仓库链接合并还是分栏，以后台及后续公告为准。
4. 核对上传文件与开源冻结版本一致，完成页面要求的最终提交步骤并保存回执和文件校验和。文件打包或仓库公开不能单独证明比赛系统已提交成功。

[协办方高云公开通知](https://www.gowinsemi.com.cn/university/match2026)本轮仍列作品提交2026年11月4日18点。指南3.3.6说明时间以官方公告为准，本队最终截止和字段须以后台/后续官方公告核实；本轮未套用另一独立“芯片应用赛道”的视频/附件限制。

## 本轮结果

新增本说明并追加项目日志。未生成最终工程包、发布仓库、上传作品或操作板卡；Windows收件未验证。

