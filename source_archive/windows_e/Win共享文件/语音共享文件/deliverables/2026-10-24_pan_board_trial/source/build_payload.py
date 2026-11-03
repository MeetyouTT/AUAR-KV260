import gzip,hashlib,io,json,tarfile,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OFFLINE=Path('/home/ghmd/aura-pan-joint-20261023')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def response(label):return json.loads((Path(json.loads((ROOT/('latest-'+label+'.json')).read_text())['evidence'])/'response.json').read_text())
parser=argparse.ArgumentParser();parser.add_argument('--suffix',default='');args=parser.parse_args()
assert args.suffix in ('','-r2','-r3')
c=response('context');i=response('inventory');h=response('health')
assert c['boot_id']==i['boot_id']==h['boot_id'] and c['sd_cid_matches_expected']
APP='aura-visual-servo-b4096-v2'
base={'boot_id':c['boot_id'],'fdt_sha256':c['fdt_sha256'],'vart_conf':c['vart_conf'],
 'app':'kv260-benchmark-b4096','firmware_name':c['firmware_name'],
 'firmware_files':i['firmware_files']['kv260-benchmark-b4096'],
 'services':c['services'],'ops_root':i['ops_meta']['root'],
 'ops_source_pins':i['ops_meta']['source_pins'],'ops_protected':i['ops_meta']['protected'],
 'camera_config':i['ops_meta']['candidate_config'],'camera_config_sha256':i['camera_config_sha256'],
 'checkpoint':i['camera_native_config']['checkpoint_output'],
 'gui_config':'/home/root/aura-video-cpu-20261023/66cde810eb059dce/startup/config.json',
 'gui_config_sha256':i['gui_startup_config_sha256'],'gui_runtime':i['gui_startup_config']['runtime'],
 'identity_config_sha256':i['identity_config_sha256'],'database_path':i['database_path'],
 'database_sha256':i['database_sha256'],'initial_camera_health':h['camera']}
files={}
for name in ['delta_codec.py','firmware-delta.json.gz','prepare_payload_board.py']:
 files[name]=(ROOT/name).read_bytes()
for name in ['inspect_board_context.py','bench_identity_stop.py','bench_finite_step.py']:
 files[name]=(OFFLINE/name).read_bytes()
bundle=OFFLINE/'bundle'
files['candidate-manifest.json']=(bundle/'candidate-manifest.json').read_bytes()
for p in (bundle/'driver').iterdir():files['driver/'+p.name]=p.read_bytes()
for p in (bundle/'lib/firmware/xilinx'/APP).iterdir():
 if not p.name.endswith('.bit.bin'):files['runtime/'+APP+'/'+p.name]=p.read_bytes()
meta={'schema':'aura-pan-board-payload-1','app':APP,'board_root':'/home/root/aura-pan-vsrv2-20261024/778d2512-'+c['boot_id'][:8]+args.suffix,
 'baseline':base,'candidate_manifest_sha256':sha(bundle/'candidate-manifest.json'),
 'delta_base':'/lib/firmware/xilinx/aura-visual-servo-b4096-v1/aura-visual-servo-b4096-v1.bit.bin',
 'files':{n:hashlib.sha256(data).hexdigest() for n,data in files.items()}}
files['payload.json']=(json.dumps(meta,indent=2)+'\n').encode()
data=io.BytesIO()
with tarfile.open(fileobj=data,mode='w') as tar:
 for name,raw in sorted(files.items()):
  item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o600;item.mtime=0;tar.addfile(item,io.BytesIO(raw))
raw=gzip.compress(data.getvalue(),mtime=0);digest=hashlib.sha256(raw).hexdigest()
out=Path('/home/ghmd/aura-dpu-vision-20261021/work')/('pan-vsrv2-'+digest[:16]+'.tar.gz')
with out.open('xb') as f:f.write(raw)
result={'path':str(out),'sha256':digest,'bytes':len(raw),'root':meta['board_root'],'boot_id':c['boot_id'],'payload_files':len(files)}
(ROOT/'payload.json').write_text(json.dumps(meta,indent=2)+'\n')
(ROOT/'payload-transfer.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
