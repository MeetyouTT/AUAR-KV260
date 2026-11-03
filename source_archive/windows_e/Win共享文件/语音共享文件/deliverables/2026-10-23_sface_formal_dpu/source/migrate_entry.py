"""One owned offline job phase; never prints identity labels or features."""
import json
from pathlib import Path
import sys

if __name__=='__main__':
    if sys.flags.optimize:raise RuntimeError('Assertions required')
    root,old_config,new_config,report=map(Path,sys.argv[1:])
    assert root.is_absolute() and root.resolve()==root
    sys.path.insert(0,str(root/'aura'))
    from migration import migrate
    print(json.dumps(migrate(old_config,new_config,report,source_root=root/'aura')))
