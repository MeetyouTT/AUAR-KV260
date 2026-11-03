const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const conf = path.join(root, 'qa', 'fonts.conf');
fs.writeFileSync(conf, '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><dir>C:/Windows/Fonts</dir><cachedir>'+path.join(root,'qa','fontcache').replaceAll('\\','/')+'</cachedir></fontconfig>');
process.env.FONTCONFIG_FILE = conf;
const sharp = require('C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
(async()=>{
  const records=[];
  for(const name of fs.readdirSync(path.join(root,'figures')).filter(n=>n.endsWith('.svg'))){
    const file=path.join(root,'figures',name);
    let xml=fs.readFileSync(file,'utf8');
    xml=xml.replace(/font-family:[^;"]+/g,"font-family:SimSun").replace(/font-family="[^"]+"/g,'font-family="SimSun"');
    if(name==='live_resources.svg'){
      xml=xml.replace('2026-11-03 | listening and following disabled','2026-11-03 21:52:23-21:53:24 Beijing time | listening and following disabled');
      xml=xml.replace('KV260 live observation | 2026-11-03 21:52:23-21:53:24 Beijing time | listening and following disabled','KV260 资源观察 | 北京时间 2026-11-03 21:52:23-21:53:24');
    }
    fs.writeFileSync(file,xml);
    const out=file.replace(/\.svg$/,'.png');
    await sharp(Buffer.from(xml),{density:220}).flatten({background:'#ffffff'}).png().toFile(out+'.tmp.png');
    fs.renameSync(out+'.tmp.png',out);
    const m=await sharp(out).metadata();
    records.push({name,font:'SimSun',width:m.width,height:m.height});
  }
  fs.writeFileSync(path.join(root,'qa','chart_font_revision.json'),JSON.stringify({font:'SimSun',data_unchanged:true,charts:records},null,2));
  process.stdout.write(JSON.stringify(records,null,2));
})();
