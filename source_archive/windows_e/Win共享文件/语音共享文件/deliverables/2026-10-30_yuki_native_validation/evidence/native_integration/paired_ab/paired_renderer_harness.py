"""Unified A/B entry; defaults to check-only. See OLD_HARNESS_README.txt."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from old_renderer_harness import main
if __name__=='__main__':raise SystemExit(main())
