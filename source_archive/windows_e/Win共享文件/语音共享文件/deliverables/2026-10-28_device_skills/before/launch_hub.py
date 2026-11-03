import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(AURA))
import tools,common
tools.__path__=[str(HERE/'candidate_source/tools'),str(AURA/'tools')]
common.__path__=[str(HERE/'candidate_source/common'),str(AURA/'common')]
from tools.device_hub import main
main()
