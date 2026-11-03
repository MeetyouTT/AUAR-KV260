# AUAR·雪妃：两份技术报告

版本：审阅稿V1，2026-11-02。作品名称按用户最新确认填写为“AUAR·雪妃”。

| 用途 | 可编辑Word | PDF审阅版 | 正文源稿 |
| --- | --- | --- | --- |
| AMD自主选题，覆盖3.3.5.3七项要求 | [AMD报告](auar_xuefei_amd_report.docx) | [21页PDF](auar_xuefei_amd_report.pdf) | [Markdown](amd_design_report.md) |
| 赛事方技术文档模板，五部分结构 | [赛事方报告](auar_xuefei_competition_report.docx) | [13页PDF](auar_xuefei_competition_report.pdf) | [Markdown](competition_technical_report.md) |

两份报告共用同一批技术数值和证据。AMD稿详细展开背景、原理、软硬件接口、优化、AI协作、Skill和复现；赛事方稿保留原模板的摘要及五部分章节、指定子项与限字要求。没有向报告中加入学校、指导教师或未确认的队员姓名。

## 需要优先准备的材料

完整清单见[材料准备表](materials_to_prepare.md)。当前最重要的是：最终实物图与机械/电路图、同版整机验收与release、构建依赖闭包、原始AI开发问答，以及最终Windows主机信息。文内灰色图位明确是待补项；角色图片为原样复制的历史隔离渲染输出，不能代替实物照片。

## 对照与依据

- [要求映射表](requirements_matrix.csv)：AMD七项、模板结构、字数及上传限制。
- [统一指标表](metrics.csv)：单位、样本范围与原始证据编号。
- [来源索引](source_index.json)：输入文件和28项内部证据的路径、大小与SHA256。
- [证据副本](evidence/)：对应原始报告、数据、接口与少量源码；不是完整工程提交包。
- [文档检查记录](validation.json)：Word压缩包/XML、PDF文字、限字、大小与证据校验。
- [框图及占位图](figures/)：PDF矢量图与PNG插图；生成代码见tools/build_figures.py。

本轮读取参考设计报告后借鉴“约束→方法→结果”的组织方式，未沿用其光计算命题的4-bit约束、得分公式或实验结论。截图和完整AMD指南用于确定七项内容，上传PDF用于确定文件格式/大小/截止时间，Word模板用于确定赛事稿结构及字数。

## 验证与使用

生成结果：AMD PDF 21页，约1.11MB；赛事方PDF 13页，约1.33MB，均小于50,000,000字节。两个Word的ZIP CRC及全部XML/关系文件可解析；九项限字检查通过，统计将数字和英文也逐字符计入，排除Markdown排版符号与空白。具体值见validation.json。

Word是在用户原DOCX包基础上替换正文，保留其页面设置与模板页眉标志，补入图表及页码，并清空原模板作者信息。PDF由相同Markdown独立排版生成，不是通过Word/WPS转换；二者正文一致，分页可能不同。尚未在Windows Word/WPS实际打开检查，定稿时须检查分页、表格、图片和页码。

较新保存版本仍存在MCP01未枚举/GUI未READY、转轴异常中止和最终release未收拢的问题；报告按对应阶段如实陈述。历史原始AI问答、真实机械行程、同会话摘要召回、长稳及完整陌生环境复现并未因本轮写文档而完成。

本轮只进行材料阅读、静态核对、图表及文档生成，没有运行工程测试、模型推理、构建固件、连接板卡或修改业务服务。未开源发布、未比赛上传、未代填Windows回执，也未确认微力同步收件。

## 本地重建文档

在当前Ubuntu环境、本目录下执行：

```bash
python3 -B tools/build_reports.py
```

依赖已安装的ReportLab、Pillow、Poppler及本机中文字体；生成器读取代码中登记的原始输入与用户Word模板，不执行工程入口。若迁移文档生成环境，需要相应调整来源位置；这与作品工程的从零复现是两项不同工作。
