#!/usr/bin/env python3
"""Reuse the preserved UART collector, storing new evidence separately."""
import importlib.util
from pathlib import Path

source = Path('/home/ghmd/AMD_Smart/logs/fpga/2026-09-30-kv260-readonly/collect_serial.py')
spec = importlib.util.spec_from_file_location('preserved_uart_collector', source)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)
collector.ROOT = Path(__file__).resolve().parent

if __name__ == '__main__':
    collector.main()
