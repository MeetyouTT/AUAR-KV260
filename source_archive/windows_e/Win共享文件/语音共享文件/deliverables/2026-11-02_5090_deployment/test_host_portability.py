import importlib.util, json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
HOST=ROOT/'deliverables/2026-10-30_board_owner/integration/production_model_host'
sys.path[:0]=[str(HOST),str(ROOT/'aura')]
import production_runtime as runtime
import manage

class LocalEndpointTests(unittest.TestCase):
    def config(self,host,peers):
        return dict(schema_version=1,host=host,port=8797,allowed_peers=peers,
            local_health=True,startup_seconds=300,lifetime_seconds=None,voice_python=sys.executable)
    def load(self,value):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'config.json';p.write_text(json.dumps(value))
            with patch.object(runtime,'CONFIG',p):return runtime.config()[0]
    def test_offline_loopback_and_dedicated_board_are_accepted(self):
        for host,peers in [('127.0.0.1',['127.0.0.1']),('192.168.50.1',['192.168.50.2'])]:
            self.assertEqual(self.load(self.config(host,peers))['host'],host)
    def test_wildcard_arbitrary_lan_and_mixed_peer_scopes_are_rejected(self):
        for host,peers in [('0.0.0.0',['127.0.0.1']),('192.168.137.116',['127.0.0.1']),
                ('127.0.0.1',['192.168.50.2']),('192.168.50.1',['127.0.0.1']),
                ('127.0.0.1',['127.0.0.1','192.168.50.2'])]:
            with self.subTest(host=host,peers=peers),self.assertRaises(ValueError):self.load(self.config(host,peers))
    def test_health_follows_configured_loopback_and_checks_service_role(self):
        class Response:
            status=200
            def read(self,size):return b'{"protocol_version":1,"role":"model_inference_only"}'
        class Connection:
            def request(self,*args):pass
            def getresponse(self):return Response()
            def close(self):pass
        with patch.object(manage,'config',return_value=(self.config('127.0.0.1',['127.0.0.1']),'sha')),\
             patch.object(manage.http.client,'HTTPConnection',return_value=Connection()) as factory:
            self.assertEqual(manage.health()['role'],'model_inference_only')
            factory.assert_called_once_with('127.0.0.1',8797,timeout=2)

if __name__=='__main__':unittest.main()
