# -*- coding: utf-8 -*-
"""MockBoard —— 板端硬件/外设模拟（Week A1 · 9/5 任务）

背景：人1 于 9/6 正式交接 MockBoard 与寄存器合同。本文件是人3 的接口占位 +
最小模拟实现，保证上层（Event Bus / FSM / Validator / UI）可先行联调。

合同（V1.0 §11.2 初始寄存器合同）：
  0x00 IP_ID_VERSION  0x04 CONTROL  0x08 FRAME_SEQ_IN  0x0C COMMIT_SEQ
  0x10 STATUS         0x14 FRAME_COUNT 0x18 DROP_COUNT 0x1C UNDERFLOW_COUNT
  0x20 TIMESTAMP_LO   0x24 TIMESTAMP_HI 0x28 FIFO_STATUS 0x2C FIFO_DATA0
  0x30 FIFO_DATA1     0x40-0x7C BOX0-BOX3  0x80 ZONE  0x90 PRIVACY_COLOR

⚠️ 环境标签：本文件为 PC/SIMULATED 级模拟，任何结果不得写成实体板卡实测。
"""
import time
import typing
from dataclasses import dataclass, field


@dataclass
class DeviceStatus:
    """外设健康状态。"""
    name: str
    online: bool = True
    error_code: int = 0
    last_change_ms: int = 0
    extra: typing.Dict = field(default_factory=dict)

    def to_dict(self) -> typing.Dict:
        return {
            "name": self.name,
            "online": self.online,
            "error_code": self.error_code,
            "last_change_ms": self.last_change_ms,
            "extra": dict(self.extra),
        }


class MockBoard:
    """板端模拟：外设状态 + 寄存器读写 + 实体键 + 计数器。

    板卡到货后由 MmioBoardIO 替换（保留本类接口签名），上层不感知差异。
    """

    # 寄存器偏移 → 名称（V1.0 §11.2）
    REGISTER_MAP = {
        0x00: "IP_ID_VERSION", 0x04: "CONTROL", 0x08: "FRAME_SEQ_IN",
        0x0C: "COMMIT_SEQ", 0x10: "STATUS", 0x14: "FRAME_COUNT",
        0x18: "DROP_COUNT", 0x1C: "UNDERFLOW_COUNT", 0x20: "TIMESTAMP_LO",
        0x24: "TIMESTAMP_HI", 0x28: "FIFO_STATUS", 0x2C: "FIFO_DATA0",
        0x30: "FIFO_DATA1", 0x40: "BOX0_X0", 0x44: "BOX0_Y0",
        0x48: "BOX0_X1", 0x4C: "BOX0_Y1", 0x50: "BOX0_COLOR_WIDTH_EN",
        0x54: "BOX1_X0", 0x58: "BOX1_Y0", 0x5C: "BOX1_X1",
        0x60: "BOX1_Y1", 0x64: "BOX1_COLOR_WIDTH_EN",
        0x68: "BOX2_X0", 0x6C: "BOX2_Y0", 0x70: "BOX2_X1",
        0x74: "BOX2_Y1", 0x78: "BOX2_COLOR_WIDTH_EN",
        0x7C: "BOX3_X0", 0x80: "BOX3_Y0", 0x84: "BOX3_X1",
        0x88: "BOX3_Y1", 0x8C: "BOX3_COLOR_WIDTH_EN",
        0x90: "ZONE_X0", 0x94: "ZONE_Y0", 0x98: "ZONE_X1",
        0x9C: "ZONE_Y1", 0xA0: "ZONE_STYLE",
        0xA4: "PRIVACY_COLOR",
    }
    RW_REGISTERS = {0x04, 0x08, 0x0C, 0x40, 0x44, 0x48, 0x4C, 0x50,
                    0x54, 0x58, 0x5C, 0x60, 0x64, 0x68, 0x6C, 0x70,
                    0x74, 0x78, 0x7C, 0x80, 0x84, 0x88, 0x8C, 0x90,
                    0x94, 0x98, 0x9C, 0xA0, 0xA4}
    # 实体键（V1.0 §5.3：PS_KEY wake/confirm；PL_KEY1 privacy；PL_KEY2 cancel）
    KEY_WAKE = "wake"
    KEY_PRIVACY = "privacy"
    KEY_CANCEL = "cancel"

    def __init__(self, config: typing.Optional[typing.Dict] = None) -> None:
        self.config = config or {}
        self.camera = DeviceStatus("camera")
        self.audio = DeviceStatus("audio")
        self.npu = DeviceStatus("npu")
        self.pl = DeviceStatus("pl")
        self.network = DeviceStatus("network")
        self._registers = {off: 0 for off in self.REGISTER_MAP}
        self._registers[0x00] = 0x00010001  # IP_ID=1, VERSION=1
        self._registers[0x10] = 0x1         # STATUS.ready
        self._counters = {"frame": 0, "drop": 0, "underflow": 0, "overflow": 0}
        self._start_ms = int(time.time() * 1000)

    # ---- 寄存器读写（后续对接人1 寄存器合同，仅保留 AXI-Lite 语义） ----
    def read_register(self, offset: int) -> int:
        if offset not in self.REGISTER_MAP:
            raise KeyError("未定义寄存器偏移 0x%02X" % offset)
        if offset == 0x14:  # FRAME_COUNT 实时返回
            return self._counters["frame"]
        if offset == 0x18:
            return self._counters["drop"]
        if offset == 0x1C:
            return self._counters["underflow"]
        if offset == 0x20:  # TIMESTAMP_LO
            return int(time.time() * 1000) & 0xFFFFFFFF
        if offset == 0x24:  # TIMESTAMP_HI
            return (int(time.time() * 1000) >> 32) & 0xFFFFFFFF
        return self._registers[offset]

    def write_register(self, offset: int, value: int) -> bool:
        if offset not in self.RW_REGISTERS:
            return False  # RO 或未定义：拒绝写
        self._registers[offset] = int(value) & 0xFFFFFFFF
        return True

    # ---- 外设状态（模拟）/ 故障注入 ----
    def set_device(self, name: str, online: bool, error_code: int = 0,
                   extra: typing.Optional[typing.Dict] = None) -> DeviceStatus:
        dev = getattr(self, name, None)
        if dev is None or not isinstance(dev, DeviceStatus):
            raise ValueError("未知外设: %s" % name)
        dev.online = online
        dev.error_code = error_code
        dev.last_change_ms = int(time.time() * 1000)
        if extra:
            dev.extra.update(extra)
        return dev

    def devices(self) -> typing.Dict[str, typing.Dict]:
        return {d.name: d.to_dict() for d in
                (self.camera, self.audio, self.npu, self.pl, self.network)}

    # ---- 实体键 ----
    def press_key(self, key: str) -> str:
        """按下实体键，返回对应事件类型（不依赖 EventBus 注入）。"""
        mapping = {
            self.KEY_WAKE: "board.key_pressed:wake",
            self.KEY_PRIVACY: "board.key_pressed:privacy",
            self.KEY_CANCEL: "board.key_pressed:cancel",
        }
        if key not in mapping:
            raise ValueError("未知按键: %s" % key)
        return mapping[key]

    # ---- 计数器/证据 ----
    def bump(self, counter: str, n: int = 1) -> None:
        if counter in self._counters:
            self._counters[counter] += n

    def metrics(self) -> typing.Dict:
        return {
            "registers": dict(self._registers),
            "counters": dict(self._counters),
            "devices": self.devices(),
            "uptime_ms": int(time.time() * 1000) - self._start_ms,
            "environment": "SIMULATED",  # 严禁冒充板端实测
        }
