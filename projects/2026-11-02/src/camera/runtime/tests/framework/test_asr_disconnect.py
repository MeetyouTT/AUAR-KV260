import io
import unittest
from tools.asr_server import Handler


class AsrDisconnectTests(unittest.TestCase):
    def handler(self, fail_headers=False, fail_body=False):
        class Output(io.BytesIO):
            def write(self, data):
                if fail_body:raise ConnectionAbortedError('client cancelled')
                return super().write(data)
        handler=Handler.__new__(Handler)
        handler.wfile=Output()
        handler.send_response=lambda status: None
        handler.send_header=lambda name,value: None
        def headers():
            if fail_headers:raise ConnectionAbortedError('client cancelled')
        handler.end_headers=headers
        handler.close_connection=False
        return handler

    def test_disconnect_during_headers_is_not_retried_as_500(self):
        handler=self.handler(fail_headers=True)
        handler.send(200,{'text':'完成'})
        self.assertTrue(handler.close_connection)

    def test_disconnect_during_body_closes_connection(self):
        handler=self.handler(fail_body=True)
        handler.send(200,{'text':'完成'})
        self.assertTrue(handler.close_connection)

    def test_success_still_writes_utf8(self):
        handler=self.handler()
        handler.send(200,{'text':'完成'})
        self.assertIn('完成'.encode(),handler.wfile.getvalue())
        self.assertTrue(handler.close_connection)
