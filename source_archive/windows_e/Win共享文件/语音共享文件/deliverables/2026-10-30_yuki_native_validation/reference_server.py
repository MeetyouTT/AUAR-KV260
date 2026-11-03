"""Loopback-only, allowlisted static reference; no chat, model APIs or audio."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import mimetypes
import json

SOURCE = Path('D:/share、/项目开发/美冬本地女友项目')
FIXTURES = Path(__file__).resolve().parent / 'native_integration/mask_fixtures'
CONTROLLED = Path(__file__).resolve().parent / 'reference_controlled'
MESH_FIXTURES = Path(__file__).resolve().parent / 'native_integration/mesh_fixtures'
MESH_RIGS = {p.name for p in MESH_FIXTURES.glob('*-rig.json')}
ALLOWED = {
    '/web/tachie.html': 'web/tachie.html',
    '/web/tachie/emote-stage.js': 'web/tachie/emote-stage.js',
    '/web/tachie/yuki-rig.json': 'web/tachie/yuki-rig.json',
    '/web/vendor/freemote/FreeMoteDriver.js': 'web/vendor/freemote/FreeMoteDriver.js',
    '/web/vendor/freemote/emoteplayer.js': 'web/vendor/freemote/emoteplayer.js',
    '/assets/fuyukiss/webgl/yuk_0.ems.psb': 'assets/fuyukiss/webgl/yuk_0.ems.psb',
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        fixture_name = path.removeprefix('/fixtures/').split('/')
        rig_name = path.removeprefix('/web/tachie/')
        if path=='/fixtures/yuki_controlled/model.psb':
            file=CONTROLLED/'model.psb'
        elif path=='/web/tachie/controlled-rig.json':
            file=CONTROLLED/'controlled-rig.json'
        elif path in ('/fixtures/rebuilt_combo/model.psb','/fixtures/rebuilt_no_combo/model.psb'):
            file=CONTROLLED/path.split('/')[2]/'model.psb'
        elif path in ('/web/tachie/rebuilt-combo-rig.json','/web/tachie/rebuilt-no-combo-rig.json'):
            file=CONTROLLED/('rebuilt_combo' if 'rebuilt-combo-' in path else 'rebuilt_no_combo')/'rig.json'
        elif path in ('/web/tachie/probe-combo-rig.json','/web/tachie/probe-no-combo-rig.json'):
            file=CONTROLLED/rig_name
        elif path.startswith('/web/tachie/') and rig_name in MESH_RIGS:
            file=MESH_FIXTURES/rig_name
        elif path.startswith('/mesh-fixtures/') and path.removeprefix('/mesh-fixtures/') in ('absolute_with_bp/model.psb','absolute_plus_delta/model.psb','bp_only/model.psb'):
            file=MESH_FIXTURES/path.removeprefix('/mesh-fixtures/')
        elif path.startswith('/fixtures/') and len(fixture_name)==2 and fixture_name[0] in ('motion_self','sprite_self','ordinary_child','other_stencil') and fixture_name[1]=='model.psb':
            file = FIXTURES / fixture_name[0] / 'model.psb'
        elif path.startswith('/web/tachie/') and rig_name in ('motion-self-rig.json','sprite-self-rig.json','ordinary-child-rig.json','other-stencil-rig.json'):
            file = FIXTURES / rig_name
        elif path in ALLOWED:
            file = SOURCE / ALLOWED[path]
        else:
            self.send_error(404)
            return
        data = file.read_bytes()
        if path.endswith('.html'):
            data = data.replace(b'</head>', b'''<style>body{background:#FCFCF3}</style>
<script>addEventListener('tachie-ready',()=>{
 if(new URLSearchParams(location.search).get('diagnostic_png')!=='1')return;
 const button=document.createElement('button');button.textContent='Export reference PNG';
 button.style.cssText='position:fixed;top:4px;left:4px;z-index:9999';document.body.appendChild(button);
 const link=document.createElement('a');link.id='lossless-reference';link.download='reference.png';
 link.style.cssText='position:fixed;top:36px;left:4px;z-index:9999';document.body.appendChild(link);
 button.onclick=()=>{const cv=document.getElementById('cv'),out=document.createElement('canvas');
 out.width=cv.width;out.height=cv.height;const context=out.getContext('2d');
 context.fillStyle='#FCFCF3';context.fillRect(0,0,out.width,out.height);context.drawImage(cv,0,0);
 link.href=out.toDataURL('image/png');link.textContent='Reference PNG ready';};
});</script></head>''')
        if path.endswith('emote-stage.js'):
            canvas_marker=b'EmotePlayer.createRenderCanvas(config.view.maxRenderSize, config.view.maxRenderSize);'
            assert data.count(canvas_marker)==1
            data=data.replace(canvas_marker,b'''if(qs.get('matchviewport')==='1'){
      EmotePlayer.createRenderCanvas(window.innerWidth,window.innerHeight);
      cv.dataset.referenceViewport=window.innerWidth+'x'+window.innerHeight;
    }else{EmotePlayer.createRenderCanvas(config.view.maxRenderSize,config.view.maxRenderSize);
      cv.dataset.referenceViewport=config.view.maxRenderSize+'x'+config.view.maxRenderSize;}''')
            marker = b'cv.dataset.renderer = s.renderer;'
            assert data.count(marker) == 1
            observation = b'cv.dataset.parameters = JSON.stringify(Object.fromEntries(player.variableList.map(v => [v.label, player.getVariable(v.label)])));\n    '
            data = data.replace(marker, observation + marker)
        if path.endswith('/emoteplayer.js'):
            marker=b'player.modified = false;'
            assert data.count(marker)==1
            hidden=['fade_'+x for x in 'abcde']+['hair_LR','hair_LR_M','hair_LR_M_front',
              'hair_LR_M_sideL','hair_LR_M_sideR','hair_LR_front','hair_LR_sideL','hair_LR_sideR',
              'hair_UD','hair_UD_front','hair_UD_sideL','hair_UD_sideR','quake_LR','quake_LR_M','quake_UD']
            observation=('\nif(player.canvas){ const labels=[...new Set([...player.variableList.map(v=>v.label),...'+json.dumps(hidden)+'])];'
              'player.canvas.dataset.parameters=JSON.stringify(Object.fromEntries(labels.map(label=>[label,player.getVariable(label)])));'
              'player.canvas.dataset.sampleOrder="after-core-update-before-draw";}\n').encode()
            data=data.replace(marker,marker+observation)
        self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)


if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 18766), Handler).serve_forever()
