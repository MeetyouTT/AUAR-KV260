"""Exact pinned original70second pre-spawn port guard; no call on import."""
import errno
import socket
import threading
import time
STOP=threading.Event()

def check_port_unused(port, wait_seconds=70):
    deadline = time.monotonic()+wait_seconds
    while not STOP.is_set():
        try:
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind(('127.0.0.1', port))
            return
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE or time.monotonic() >= deadline:
                raise
            # The old exclusive HTTP server can leave this port in TIME_WAIT.
            # Wait within TimeoutStartSec, without killing another process.
            STOP.wait(.25)
    raise RuntimeError('UI startup cancelled while waiting for its control port')
