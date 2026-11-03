import contextlib,hashlib,http.server,json,os,subprocess,sys,tempfile,threading,time,types,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'aura'),str(ROOT/'deliverables/2026-10-18_board_dialogue')]
import deploy_5090 as deploy
import project_ollama
from common.model_inference_wire import audio_payload

class DeploymentGates(unittest.TestCase):
    def simulate(self,bad_hash=False,bad_tts=False):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'project';out=root/'deliverables/current';out.mkdir(parents=True)
            aura=root/'aura';host=root/'deliverables/2026-10-30_board_owner/integration/production_model_host'
            runtime=root/'deliverables/2026-10-18_board_dialogue/model_host';runtime.mkdir(parents=True);host.mkdir(parents=True)
            models=root/'models';models.mkdir()
            source_paths=['start_model_dashboard.ps1','aura/config/model_inference.local.json','aura/config/gpu_runtime.local.json',
                'aura/config/ollama_runtime.local.json','deliverables/2026-10-30_board_owner/integration/production_model_host/production_runtime.py',
                'deliverables/2026-10-30_board_owner/integration/production_model_host/manage.py','deliverables/2026-10-18_board_dialogue/board_ssh.py']
            for rel in source_paths:
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
            (host/'latest.json').write_text(json.dumps({'owner':{'executable':'C:\\Users\\35870\\old\\python.exe'}}))
            (out/'llm_download_verification.json').write_text(json.dumps({'status':'VERIFIED','sha256':'bad' if bad_hash else deploy.EXPECTED}))
            (out/'voice_py310_requirements_5090.txt').write_text('pip==26.2.1\n')
            logs=[];routes=[];clock=[0.]
            weights=types.SimpleNamespace(name='test.gguf',parent=models,stat=lambda:types.SimpleNamespace(st_size=14403496864))
            def run(args,log,**kwargs):
                logs.append(log)
                if log in ('tts_calibration_runtime.log','llm_calibration_runtime.log'):
                    kind='tts' if log.startswith('tts') else 'llm'
                    (out/(kind+'_calibration.json')).write_text(json.dumps(dict(passed=not(bad_tts and kind=='tts'),
                        gpu_before={'uuid':'GPU-public-test'},candidate_cold_extra_mib=4096 if kind=='tts' else 14336,candidate_steady_extra_mib=512)))
            def http(path,body=None,**kwargs):
                routes.append(path)
                if path=='/health':return {'role':'model_inference_only','backend':{'tts_ready':True}}
                base={k:body[k] for k in ('protocol_version','request_id','board_boot_id','session_id','generation')}
                if path=='/v1/inference/llm':return dict(base,ok=True,result={'text':'public response'})
                if path=='/v1/inference/tts':return dict(base,ok=True,result={'audio':audio_payload(b'\x01\x00'*480)})
                raise AssertionError('Unknown HTTP protocol route: '+path)
            def sleep(seconds):clock[0]+=seconds
            with contextlib.ExitStack() as stack:
                for name,value in dict(OUT=out,ROOT=root,AURA=aura,HOST=host,RUNTIME=runtime,PACKAGE=root/'package',
                    VOICE=Path(sys.executable),WEIGHTS=weights,START=0.,state={'complete':False}).items():stack.enter_context(patch.object(deploy,name,value))
                stack.enter_context(patch.object(deploy,'installers',return_value=[]))
                stack.enter_context(patch.object(deploy,'free_endpoint'))
                stack.enter_context(patch.object(deploy,'run',side_effect=run))
                stack.enter_context(patch.object(deploy,'http',side_effect=http))
                stack.enter_context(patch.object(deploy.time,'monotonic',side_effect=lambda:clock[0]))
                stack.enter_context(patch.object(deploy.time,'sleep',side_effect=sleep))
                stack.enter_context(patch.object(deploy.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)))
                stack.enter_context(patch.object(project_ollama,'ensure',return_value={'ready':True,'needs_controlled_restart':False}))
                if bad_hash or bad_tts:
                    with self.assertRaises(RuntimeError):deploy.main()
                    self.assertNotIn('ollama_model_import.log',logs)
                    self.assertFalse((out/'READY_LOCAL.json').exists())
                else:
                    deploy.main()
                    self.assertTrue(json.loads((out/'STATUS.json').read_bytes())['complete'])
                    self.assertEqual(json.loads((out/'READY_LOCAL.json').read_bytes())['status'],'READY_LOCAL_ONLY_BOARD_INTEGRATION_PENDING')
                    self.assertIn('/v1/inference/llm',routes);self.assertIn('/v1/inference/tts',routes)
                    self.assertTrue((host/'latest.before-5090-20261102.json').exists())
    def test_entire_success_path_requires_real_protocol_routes(self):self.simulate()
    def test_wrong_weight_sha_prevents_import_and_ready(self):self.simulate(bad_hash=True)
    def test_failed_tts_prevents_import_and_ready(self):self.simulate(bad_tts=True)

class RangeResume(unittest.TestCase):
    def run_case(self,orphan=False,bad_header=False):
        data=bytes(range(251))*1327
        prefix=12345;chunk=65536;cut=[False];requests=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                start,end=map(int,self.headers['Range'].split('=')[1].split('-'));requests.append((start,end))
                body=data[start:end+1]
                self.send_response(206);self.send_header('Content-Range',f'bytes {start}-{end}/{len(data)}')
                self.send_header('Content-Length',str(len(body)));self.end_headers()
                if not cut[0]:cut[0]=True;self.wfile.write(body[:321]);self.wfile.flush();self.close_connection=True
                else:self.wfile.write(body)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                base=Path(directory)/'models';out=Path(directory)/'reports';parts=base/'download-parts-5090'
                parts.mkdir(parents=True);out.mkdir();name='public-synthetic.bin'
                (base/(name+'.partial')).write_bytes(data[:prefix])
                (parts/'0000.partial').write_bytes(data[prefix:prefix+1000])
                if orphan:
                    (parts/'0000.tail').write_bytes(data[prefix+1000:prefix+1321])
                    first=prefix+999 if bad_header else prefix+1000
                    (parts/'0000.resume-headers').write_text(f'HTTP/1.1 206 Partial Content\nContent-Range: bytes {first}-{prefix+chunk-1}/{len(data)}\n\n')
                (parts/'plan.json').write_text(json.dumps({'prefix_bytes':prefix,'chunk_bytes':chunk,'url':f'http://127.0.0.1:{server.server_port}/model'}))
                source=(HERE/'download_llm_ranges.py').read_text(encoding='utf-8-sig')
                source=source.replace("BASE=Path('D:/AIModels/qwen3.8-27b-abliterated')",'BASE=Path('+repr(str(base))+')')
                source=source.replace("OUT=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment')",'OUT=Path('+repr(str(out))+')')
                source=source.replace("NAME='Huihui-Qwen3.8-27B-abliterated-UD-IQ4_XS.gguf'",'NAME='+repr(name))
                source=source.replace('SIZE=14403496864','SIZE='+str(len(data)))
                source=source.replace("EXPECTED='d83adbbbaace8acdfcfe28004f779326176b9df00b4ec99dc6c24d749723d3b9'",'EXPECTED='+repr(hashlib.sha256(data).hexdigest()))
                script=out/'synthetic_range_test.py';script.write_text(source,encoding='utf-8')
                result=subprocess.run([sys.executable,'-B',str(script)],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual((base/name).read_bytes(),data)
                self.assertEqual(json.loads((out/'llm_download_verification.json').read_bytes())['status'],'VERIFIED')
                expected_start=prefix+1321 if orphan and not bad_header else prefix+1000
                self.assertTrue(any(s==expected_start for s,e in requests))
                if orphan and bad_header:self.assertTrue(list(parts.glob('0000.tail.retained-*')))
                if orphan and not bad_header:self.assertEqual(json.loads((parts/'0000.tail-recovery.json').read_bytes())['recovered_bytes'],321)
                self.assertGreater(len(requests),5)
        finally:server.shutdown();server.server_close();thread.join()
    def test_partial_http_body_and_existing_chunk_resume_to_exact_sha(self):self.run_case()
    def test_verified_orphan_tail_is_recovered_without_redownloading(self):self.run_case(orphan=True)
    def test_ambiguous_orphan_tail_is_preserved_and_never_appended(self):self.run_case(orphan=True,bad_header=True)

if __name__=='__main__':unittest.main()
