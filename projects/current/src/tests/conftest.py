# -*- coding: utf-8 -*-
"""pytest 公共配置：确保工程根目录在 sys.path（不依赖 pip install -e）。"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
