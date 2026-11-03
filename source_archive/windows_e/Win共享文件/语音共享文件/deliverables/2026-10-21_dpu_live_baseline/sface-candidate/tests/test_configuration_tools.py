"""Run the read-only CLI with forbidden runtime/device modules blocked."""
import bootstrap
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from board.identity.model_store import MODEL_ID, WINDOWS_MODEL_ID


class ConfigurationToolTests(unittest.TestCase):
    def test_prepare_is_disabled_nonoverwriting_and_check_needs_no_runtime_imports(self):
        previous = Path(os.environ['AURA_PREVIOUS_DELIVERABLE'])
        root = Path(__file__).resolve().parents[1]
        tools = root/'candidate/aura/tools'
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            fallback = folder/'windows.json'
            fallback.write_text(json.dumps({'schema_version':'aura-camera-identity-1',
                'model_id':WINDOWS_MODEL_ID,'database':str(folder/'windows.sqlite3'),
                'result_ttl_ms':1500,'threshold':.85,'ambiguity_margin':.1,
                'feature_backend':{'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}}))
            before = hashlib.sha256(fallback.read_bytes()).hexdigest()
            output = folder/'new-candidate.json'
            database = folder/(MODEL_ID+'.sqlite3')
            command = [sys.executable, '-I', '-B', str(tools/'prepare_dpu_identity_config.py'),
                '--fallback-config',str(fallback), '--model',str(previous/'artifacts/sface/sface_public_int8.xmodel'),
                '--manifest',str(previous/'artifacts/sface/compiler-manifest.json'),
                '--database',str(database),'--output',str(output)]
            raw = subprocess.check_output(command)
            result = json.loads(raw)
            self.assertFalse(result['runtime_enabled'])
            self.assertFalse(result['threshold_configured'])
            config = json.loads(output.read_text())
            self.assertIsNone(config['threshold'])
            self.assertIsNone(config['ambiguity_margin'])
            self.assertFalse(database.exists())
            self.assertEqual(hashlib.sha256(fallback.read_bytes()).hexdigest(), before)
            original = output.read_bytes()
            repeated = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(hashlib.sha256(fallback.read_bytes()).hexdigest(), before)
            wrapper = """import sys, runpy
class BlockRuntime:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('board','numpy','cv2','xir','vart'):
            raise AssertionError('Unexpected runtime import: '+fullname)
sys.meta_path.insert(0, BlockRuntime())
sys.argv = %r
runpy.run_path(%r, run_name='__main__')
""" % ([str(tools/'check_dpu_identity_config.py'),'--config',str(output)],
         str(tools/'check_dpu_identity_config.py'))
            checked = json.loads(subprocess.check_output([sys.executable,'-I','-B','-c',wrapper]))
            self.assertEqual(checked['status'], 'CONFIG_VALIDATED_NOT_RUNTIME_TESTED')
            self.assertFalse(checked['runner_created'])
            self.assertFalse(checked['database_created'])
            self.assertFalse(checked['threshold_configured'])
            self.assertFalse(database.exists())
            self.assertEqual(hashlib.sha256(fallback.read_bytes()).hexdigest(), before)


if __name__ == '__main__':unittest.main()
