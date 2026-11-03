const sharp = require('C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const fs = require('node:fs');
const root = 'E:/报告制作_20261103/face_redaction';
const patch = 'C:/Users/REVO1/.codex/generated_images/01a1a1a5-f4c1-79c1-a40b-42b8c58a0e47/exec-e254c70a-ae87-4ded-a0d7-45cba29edba8.png';
(async()=>{
 const rect=JSON.parse(fs.readFileSync(root+'/face_rect.json'));
 const mosaic=await sharp(patch).resize(rect.width,rect.height,{kernel:'nearest',fit:'fill'}).removeAlpha().png().toBuffer();
 await sharp(root+'/current_raw.png').composite([{input:mosaic,left:rect.left,top:rect.top}]).png().toFile(root+'/board_x11_mosaic.png');
 const a=await sharp(root+'/current_raw.png').removeAlpha().raw().toBuffer({resolveWithObject:true});
 const b=await sharp(root+'/board_x11_mosaic.png').removeAlpha().raw().toBuffer({resolveWithObject:true});
 let outside=0;let inside=0;
 for(let y=0;y<a.info.height;y++)for(let x=0;x<a.info.width;x++){
  const pos=(y*a.info.width+x)*a.info.channels;
  let different=false;for(let c=0;c<a.info.channels;c++)if(a.data[pos+c]!==b.data[pos+c])different=true;
  if(different){if(x>=rect.left&&x<rect.left+rect.width&&y>=rect.top&&y<rect.top+rect.height)inside++;else outside++;}
 }
 if(outside!==0)throw new Error('Pixels changed outside the face redaction area');
 const result={width:a.info.width,height:a.info.height,rect,changed_pixels_inside:inside,changed_pixels_outside:outside,edit_tool:'imagegen built-in privacy mosaic patch; deterministic placement preserves all other pixels'};
 fs.writeFileSync(root+'/redaction_verification.json',JSON.stringify(result,null,2));
 console.log(JSON.stringify(result));
})().catch(e=>{console.error(e);process.exit(1)});
