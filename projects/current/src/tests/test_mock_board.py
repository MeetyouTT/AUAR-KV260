# -*- coding: utf-8 -*-
"""MockBoard 单测：寄存器读写、外设状态、计数器、环境标签。"""
import time

import pytest

from board.runtime.mocks import MockBoard


def test_register_read_only_id():
    b = MockBoard()
    assert b.read_register(0x00) == 0x00010001  # IP_ID_VERSION
    assert b.read_register(0x10) & 0x1 == 1     # STATUS.ready


def test_register_write_read():
    b = MockBoard()
    assert b.write_register(0x04, 0x3) is True   # CONTROL RW
    assert b.read_register(0x04) == 0x3


def test_readonly_register_rejected():
    b = MockBoard()
    assert b.write_register(0x00, 999) is False  # IP_ID 只读
    assert b.read_register(0x00) == 0x00010001


def test_unknown_register_raises():
    b = MockBoard()
    with pytest.raises(KeyError):
        b.read_register(0xF0)


def test_box_register_contract():
    b = MockBoard()
    # BOX0 坐标（V1.0 §11.2 合同 0x40-0x50）
    assert b.write_register(0x40, 120)
    assert b.write_register(0x44, 80)
    assert b.read_register(0x40) == 120
    assert b.read_register(0x44) == 80


def test_device_status_fault_injection():
    b = MockBoard()
    b.set_device("camera", online=False, error_code=5)
    b.set_device("network", online=False)
    d = b.devices()
    assert d["camera"]["online"] is False
    assert d["camera"]["error_code"] == 5
    assert d["network"]["online"] is False
    assert d["npu"]["online"] is True


def test_unknown_device_raises():
    b = MockBoard()
    with pytest.raises(ValueError):
        b.set_device("gpu", online=False)


def test_counters():
    b = MockBoard()
    b.bump("frame", 10)
    b.bump("drop")
    b.bump("underflow")
    m = b.metrics()
    assert m["counters"]["frame"] == 10
    assert m["counters"]["drop"] == 1
    assert m["counters"]["underflow"] == 1


def test_frame_count_register_mirrors_counter():
    b = MockBoard()
    b.bump("frame", 5)
    assert b.read_register(0x14) == 5  # FRAME_COUNT


def test_timestamp_monotonic():
    b = MockBoard()
    lo1 = b.read_register(0x20)
    time.sleep(0.003)
    lo2 = b.read_register(0x20)
    assert lo2 >= lo1


def test_metrics_environment_tag():
    """红线：MockBoard 必须标注 SIMULATED，不得冒充板端实测。"""
    assert MockBoard().metrics()["environment"] == "SIMULATED"


def test_key_mapping():
    b = MockBoard()
    assert "wake" in b.press_key(b.KEY_WAKE)
    assert "privacy" in b.press_key(b.KEY_PRIVACY)
    assert "cancel" in b.press_key(b.KEY_CANCEL)
    with pytest.raises(ValueError):
        b.press_key("reset")
