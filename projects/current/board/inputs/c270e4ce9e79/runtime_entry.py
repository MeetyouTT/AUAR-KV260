"""Stable entrypoint for the byte-identical validated process-local GIL wrapper."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import uuid

WRAPPER_SHA='0cec741d143a012b5d5aa5808f404e7b818510d2773f3b122dd1fb639222ae02'


def load_wrapper(path):
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=WRAPPER_SHA:
        raise RuntimeError('Validated runtime wrapper differs')
    spec=importlib.util.spec_from_file_location('_validated_camera_wrapper',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def launch(argv,*,root=None,boot_id=None,loader=load_wrapper):
    root=Path(root) if root is not None else Path(__file__).resolve().parent
    boot_id=boot_id if boot_id is not None else Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    if str(uuid.UUID(boot_id))!=boot_id:raise ValueError('Canonical boot UUID required')
    if not argv:raise ValueError('Camera entrypoint required')
    if root.resolve()!=root or (root/'process-settings').is_symlink():
        raise ValueError('Runtime record parent redirects outside release')
    directory=root/'process-settings'/boot_id
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    if directory.resolve()!=directory:raise ValueError('Runtime record path redirects outside release')
    # PID values can repeat across boots or after PID wrap. Keep every launch
    # in an owned directory; never overwrite an older validation record.
    record=Path(tempfile.mkdtemp(prefix='launch-',dir=str(directory)))
    wrapper=loader(root/'gil_camera_launcher.py')
    return wrapper.launch(argv,record_directory=record)


if __name__=='__main__':launch(sys.argv[1:])
