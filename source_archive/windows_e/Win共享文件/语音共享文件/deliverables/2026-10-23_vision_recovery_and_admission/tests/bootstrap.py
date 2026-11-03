"""Overlay candidate modules on recovered board sources, then shared dependencies."""
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE
LIVE = Path(os.environ.get('AURA_LIVE_SOURCE', '/home/ghmd/aura-dpu-vision-20261021/live-source'))
SHARED = Path(os.environ.get('AURA_SHARED_SOURCE', '/home/ghmd/Win共享文件/语音共享文件/aura'))
RUNTIME = Path(os.environ.get('AURA_DPU_SOURCE', '/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start/candidate/aura'))
CANDIDATE = Path(os.environ.get('AURA_CANDIDATE_SOURCE', str(HERE/'candidate/aura')))
sys.path.insert(0, str(SHARED))
import board.identity
import board.vision
for package, suffix in ((board.identity, 'board/identity'), (board.vision, 'board/vision')):
    package.__path__[:0] = [str(CANDIDATE/suffix), str(HERE/'dependencies/aura'/suffix),
                           str(LIVE/suffix), str(RUNTIME/suffix)]

