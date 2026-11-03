#!/usr/bin/env python3
"""Real localhost HTTP tests; all provider responses are explicitly fixtures."""
import json
from pathlib import Path
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

REPO = Path('/home/ghmd/Win共享文件/共享文件夹/aura')
sys.path.insert(0,str(REPO))
from board.interaction.ui_contract import millis
from board.interaction.ui_services import HttpTransport, UiServiceClient
from tests.framework.test_board_ui_services import snapshot,wait_for


class HttpTests(unittest.TestCase):
    def setUp(self):
        test = self
        self.mode = 'normal'
        self.commands = []
        self.sequence = 0
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                if test.mode == 'redirect':
                    self.send_response(302);self.send_header('Location','http://127.0.0.1:1/no');self.end_headers();return
                test.sequence += 1
                value = snapshot(now=millis(),sequence=test.sequence)
                body = b'x'*131073 if test.mode == 'oversized' else json.dumps(value).encode()
                self.send_response(200);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            def do_POST(self):
                value = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                test.commands.append(value)
                keys = ('protocol_version','board_boot_id','service_epoch','command_id','ui_epoch','ui_generation')
                ack = {key:value[key] for key in keys};ack.update(accepted=True,detail='fixture queued')
                if test.mode == 'wrong-ack':ack['board_boot_id'] = 'other-boot'
                body = json.dumps(ack).encode()
                self.send_response(200);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        self.server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base = 'http://127.0.0.1:'+str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(1)

    def client(self):
        value = UiServiceClient('boot-1',{'enabled':True,'host':'127.0.0.1','port':self.server.server_port},poll_seconds=.05)
        self.addCleanup(value.close)
        wait_for(lambda:value.read()['snapshot'] is not None)
        return value

    def test_real_http_status_command_and_ack(self):
        client = self.client();client.submit('record_start')
        wait_for(lambda:bool(client.read()['results']))
        self.assertTrue(client.read()['results'][-1]['accepted'])
        self.assertEqual(client.read()['snapshot']['source_kind'],'fixture')
        self.assertEqual(self.commands[0]['action'],'record_start')

    def test_wrong_boot_receipt_is_not_success(self):
        client = self.client();self.mode = 'wrong-ack';client.submit('record_start')
        wait_for(lambda:bool(client.read()['results']))
        self.assertFalse(client.read()['results'][-1]['accepted'])

    def test_oversized_http_response_rejected(self):
        self.mode = 'oversized'
        with self.assertRaises(ValueError):HttpTransport().json(self.base,'/v1/ui/status')

    def test_http_redirect_is_not_followed(self):
        self.mode = 'redirect'
        with self.assertRaises(ValueError):HttpTransport().json(self.base,'/v1/ui/status')


if __name__ == '__main__':unittest.main(verbosity=2)
