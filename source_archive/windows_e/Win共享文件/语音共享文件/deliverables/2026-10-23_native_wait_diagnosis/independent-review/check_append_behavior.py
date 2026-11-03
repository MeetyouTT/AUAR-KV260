"""Local-only nonmutating append-open check on procfs; never writes comm."""
import os
from pathlib import Path

p = Path("/proc/self/comm")
try:
    with p.open("a"):
        pass
    print("Path.open append succeeded")
except OSError as error:
    print("Path.open append error", error.errno)
fd = os.open(str(p), os.O_WRONLY | os.O_APPEND | os.O_CLOEXEC)
os.close(fd)
print("os.open O_APPEND succeeded without write")
