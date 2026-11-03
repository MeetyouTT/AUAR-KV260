import sys
from pathlib import Path
AURA=Path(__file__).resolve().parent.parents[1]/'aura'
sys.path.insert(0,str(AURA))
from tools.device_hub import main
main()
