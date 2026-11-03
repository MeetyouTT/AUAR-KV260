# AURA 单舵机完整接线方案（5 V）

电气结构可行；接线图仅表示逻辑连接，不表示实物针脚位置。用户KV260载板版本尚未确认，现有项目platform_manifest仍为design_only_not_board_verified、pin_map_verified=false。J2针号参照Xilinx 038-05058-01 Rev B03原理图，不能与常见Pmod标准编号混用。

## 器件与电压

- KV260沿用自己的独立供电。
- 舵机电池：用户提供12 V、1800 mAh、持续放电6 A；接头线极性、尺寸及额定电流仍需实测或查规格。
- SVPDB-8S输入5.5–36 V，默认输出5 V，全板合计持续4 A、短时7 A；输入没有反接保护。保持“6V”和“7.2V”焊桥均开路，先量Vx/G输出。
- 舵机：DS3230，一只；本方案先用5 V。实际负载、起动时压降、线缆与接头承载能力需实测。
- ADuM1201ARZ：VDD1=3.3 V、VDD2=5 V；PWM走VIB→VOB。正常供电2.7–5.5 V。

## 逐线连接

|从哪里来|接到哪里|说明|
|---|---|---|
|电池正极，经DC接头已确认的正极线|SVPDB-8S VBAT|12V电池只进降压板输入|
|电池负极，经DC接头已确认的负极线|SVPDB-8S 输入 G|先量极性，断电后焊接|
|KV260 J2 原理图11或12（3.3V）|ADuM1201 VDD1|KV260侧供电|
|KV260 J2 原理图9或10（GND）|ADuM1201 GND1|KV260侧地|
|KV260 J2 原理图1（拟选PWM；封装脚H12）|ADuM1201 VIB|需配置FPGA并确认载板版本/针1方向|
|SVPDB-8S 输出 Vx（5V）|ADuM1201 VDD2|舵机侧供电，禁止直接接12V或6V|
|SVPDB-8S 输出 G|ADuM1201 GND2|与电池负极同一电源域|
|ADuM1201 VOB|SVPDB-8S 单排输入编号1|PWM经隔离后送入供电板信号1|
|SVPDB-8S 输出第1列 信号1|舵机信号线S|供电板只是信号直通，不生成PWM|
|SVPDB-8S 输出第1列 Vx|舵机正极|通常红线，以舵机标识为准|
|SVPDB-8S 输出第1列 G|舵机负极|通常黑/棕线，以舵机标识为准|
|ADuM1201 VIA|ADuM1201 GND2|固定未使用输入为低电平|
|ADuM1201 VOA|留空，不连接|未使用输出|

GND1和GND2不连接。不要通过其他USB模块、调试线或电源线把两侧地再次连通。

## 供电板插排位置

以用户上传的元件面朝上、VBAT单排在上方的照片为参考，输入单排为VBAT、G、1、2、3、4、5、6；输出六列三行从靠电感到板边依次为信号1–6、Vx、G。同一列三根针组成一个舵机口。接线时以实物丝印为准，翻面会改变左右关系。

## FPGA 输出选择

本图拟选J2原理图1号（PMOD_HDA11，FPGA封装脚H12）作为PWM输出。官方参考约束可核对其封装脚，但不代表用户现有工程已输出PWM。需确认对应端口未被当前平台其他功能占用，再将PWM输出约束到H12，使用LVCMOS33。

## 首次上电

1. 断电设置焊桥、焊接并绝缘；先不接舵机及VDD2。
2. 先确认电源接头正负极，再只给供电板接电池，量Vx对G约5 V。
3. 断开电池，按表接线；先配置KV260 PWM，在舵机断开的情况下确认隔离后的信号。
4. 断电接上舵机，先无负载、小角度测试，检查5 V轨是否明显掉压以及接头、板子是否发热。
5. 停机先断舵机电池。ADuM1201在VDD1掉电而VDD2仍上电时，VOB为高电平；不能将FPGA掉电视为可靠停机。

## 来源

- [MATEKSYS SVPDB-8S](https://www.mateksys.com/?portfolio=svpdb-8s)，规格结合用户上传电压焊桥及插排图核对。
- [ADI ADuM1200/ADuM1201数据手册](https://www.analog.com/media/en/technical-documentation/data-sheets/ADuM1200_1201.pdf)，表16/18及供电范围。
- [Xilinx官方Kria-PYNQ base.xdc](https://github.com/Xilinx/Kria-PYNQ/blob/main/kv260/base/vivado/constraints/base.xdc)，H12/pmod[0]/LVCMOS33参考映射。
- [Xilinx原始B03载板原理图镜像](https://hacksterio.s3.amazonaws.com/uploads/attachments/1429052/038-05058-01-x-mlcc_revb03_skit_TqvbkQ3RNn.pdf)，第17页J2。
- 项目aura_fpga/contracts/platform_manifest.json：载板版本未填、针脚映射未验证。
