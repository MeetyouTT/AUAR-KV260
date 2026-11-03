import hashlib,json,sys
from pathlib import Path
runtime=Path(sys.argv[1]);sys.path.insert(0,str(runtime))
from tools.formal_yuki import prepare_pair
config=json.loads((runtime/'config/board_avatar_gtk.json').read_text())
pins={};pair=prepare_pair(config,runtime,pins)
assert pair.identity.formal_name=='御笠雪妃'
assert len(pins)==11
print(json.dumps({'status':'PASS','original_prepare_pair':True,'monkeypatch_used':False,'formal_name':pair.identity.formal_name,'verified_references':len(pins),'settings':len(config['formal_settings_paths']),'python':sys.version.split()[0],'read_only_staged_filesystem':True,'board_rendered':False,'native_library_executed':False}))
