const sharp = require('C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const fs = require('node:fs');
const path = require('node:path');
const root = 'E:/报告制作_20261103/face_redaction';
const rect = {left:211,top:164,width:127,height:150};
(async()=>{
 await sharp(path.join(root,'current_raw.png')).extract(rect).png().toFile(path.join(root,'face_edit_target.png'));
 fs.writeFileSync(path.join(root,'face_rect.json'),JSON.stringify(rect,null,2));
 console.log(JSON.stringify({target:path.join(root,'face_edit_target.png'),rect}));
})().catch(e=>{console.error(e);process.exit(1)});
