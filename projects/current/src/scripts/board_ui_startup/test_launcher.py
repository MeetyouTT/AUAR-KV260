#!/usr/bin/env python3
"""Real loopback regressions for occupied ports and HTTP TIME_WAIT reuse."""
import errno
import socket
import unittest

from launcher import check_port_unused


class PortLifecycleTests(unittest.TestCase):
    def test_active_listener_is_rejected(self):
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            with self.assertRaises(OSError) as caught:
                check_port_unused(port)
            self.assertEqual(caught.exception.errno, errno.EADDRINUSE)

    def test_closed_http_style_listener_can_restart_immediately(self):
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            with socket.create_connection(('127.0.0.1', port)) as client:
                connection, unused = listener.accept()
                connection.close()
                self.assertEqual(client.recv(1), b'')
        # The old non-reusable probe rejects TIME_WAIT despite no live server.
        with socket.socket() as old_probe:
            with self.assertRaises(OSError) as caught:
                old_probe.bind(('127.0.0.1', port))
            self.assertEqual(caught.exception.errno, errno.EADDRINUSE)
        check_port_unused(port)


if __name__ == '__main__':
    unittest.main(verbosity=2)
