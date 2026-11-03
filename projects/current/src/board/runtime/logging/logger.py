# -*- coding: utf-8 -*-
"""轻量日志与证据缓冲（Week A1）。

要求（主计划 §10.1）：日志批量写盘，不能阻塞实时线程。
实现：标准 logging + 环形缓冲 handler（最近 N 条内存快照，供证据/诊断导出）。
"""
import logging
import os
import threading
import time
import typing
from collections import deque

_FMT = "[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s] %(message)s"
_DATEFMT = "%H:%M:%S"


class RingBufferHandler(logging.Handler):
    """内存环形缓冲 handler：保存最近 capacity 条已格式化日志。"""

    def __init__(self, capacity: int = 512) -> None:
        super().__init__()
        self._buf = deque(maxlen=max(1, capacity))
        self._lock = threading.Lock()
        self.setFormatter(logging.Formatter(_FMT, datefmt=_DATEFMT))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:  # noqa: BLE001
            msg = repr(record)
        with self._lock:
            self._buf.append(msg)

    def snapshot(self) -> typing.List[str]:
        with self._lock:
            return list(self._buf)


_created = {}


def get_logger(name: str, level: int = logging.INFO,
               file_path: typing.Optional[str] = None,
               ring_capacity: int = 512) -> typing.Tuple[logging.Logger, RingBufferHandler]:
    """获取（或创建）命名 logger。

    返回 (logger, ring_handler)。同一 name 返回相同实例；file_path 仅首次生效。
    """
    key = name
    if key in _created:
        return _created[key]

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    ring = RingBufferHandler(ring_capacity)
    logger.addHandler(ring)

    if file_path:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        fh = logging.FileHandler(file_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter(_FMT, datefmt=_DATEFMT))
        logger.addHandler(fh)

    _created[key] = (logger, ring)
    return logger, ring
