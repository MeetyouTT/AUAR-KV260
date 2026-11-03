"""Apply the independently reviewed resource formulas to one saved stage."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('stage',choices=('before','gtk_after','combined_after','joint'))
parser.add_argument('--label')
args=parser.parse_args()
label=args.label or args.stage
assert re.fullmatch('[a-z][a-z0-9_]{0,39}',label)
source=HERE.parent/'performance_check_20261102/summarize_performance.py'
code=source.read_text(encoding='utf-8')
needle="HERE = Path(__file__).resolve().parent\nsource = max(HERE.glob('BOARD_PERFORMANCE_*.json'),key=lambda p:p.stat().st_mtime_ns)"
assert code.count(needle)==1
replacement='HERE = Path('+repr(str(HERE))+')\nsource = HERE / '+repr('RESOURCE_'+label+'.json')
code=code.replace(needle,replacement)
namespace={'__file__':str(HERE/'stage_summary_generated.py')}
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(code,'<reviewed-resource-summary>','exec'),namespace)
summary=namespace['summary']
print(json.dumps({'stage':args.stage,'duration':summary['duration_seconds'],
    'cpu_mean_percent':summary['system_cpu_busy_percent']['weighted_mean'],
    'cpu_interval_peak':summary['system_cpu_busy_percent']['max'],
    'camera':summary['camera'],'gui':summary['gui'],
    'summary_path':str(namespace['destination'])}))
