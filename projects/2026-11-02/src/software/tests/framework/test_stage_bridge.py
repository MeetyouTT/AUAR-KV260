"""Real loopback requests verify the board command extension contract."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from tools.realtime_bridge import StageBridge


class BridgeTests(unittest.TestCase):
    def bridge(self,extra=()):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        bridge = StageBridge(Path(temp.name),0,extra_commands=extra)
        self.addCleanup(bridge.close)
        return bridge

    def request(self,bridge,data,origin=None):
        base = 'http://127.0.0.1:'+str(bridge.port)
        request = urllib.request.Request(base+'/api/command',data=json.dumps(data).encode(),
            headers={'Content-Type':'application/json','Origin':origin or base})
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        return opener.open(request,timeout=4)

    def test_explicit_board_commands_reach_the_bounded_queue(self):
        bridge = self.bridge(('record_toggle',))
        def consume():
            request = bridge.commands.get(timeout=2)
            request['result']={'ok':True,'type':request['data']['type']}
            request['done'].set()
        worker = threading.Thread(target=consume)
        worker.start()
        try:
            with self.request(bridge,{'type':'record_toggle'}) as response:
                self.assertEqual(json.load(response),{'ok':True,'type':'record_toggle'})
        finally:worker.join(timeout=2)

    def test_extension_is_opt_in_and_origin_is_still_checked(self):
        bridge = self.bridge()
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request(bridge,{'type':'record_toggle'})
        self.assertEqual(caught.exception.code,400)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request(bridge,{'type':'event','event':'cancel'},origin='http://example.invalid')
        self.assertEqual(caught.exception.code,403)
        self.assertTrue(bridge.commands.empty())
