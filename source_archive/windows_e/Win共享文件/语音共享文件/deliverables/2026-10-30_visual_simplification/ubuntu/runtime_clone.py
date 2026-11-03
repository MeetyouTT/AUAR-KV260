"""Clone a runtime without inheriting another supervisor's mutable run pointers."""
import shutil
from pathlib import Path

ROOT_RUN_ARTIFACTS = frozenset(('managed-runs','stage.log','launch.json'))


def clone_runtime(source, destination):
    source = Path(source)
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(str(destination))

    def ignore(directory, names):
        ignored = {n for n in names if n == '__pycache__' or n.endswith(('.pyc','.pyo'))}
        if Path(directory) == source:
            ignored.update(n for n in names if n in ROOT_RUN_ARTIFACTS
                           or n.startswith('stage.log.tmp-') or n == 'launch.json.tmp')
        return ignored

    shutil.copytree(str(source), str(destination), symlinks=True, ignore=ignore)
    for name in ROOT_RUN_ARTIFACTS:
        path = destination/name
        if path.exists() or path.is_symlink():
            raise RuntimeError('Run artifact leaked into new runtime: '+str(path))
    return destination
