import {FileBlob,PresentationFile} from '@oai/artifact-tool';
import {fileURLToPath} from 'node:url';
const p=await PresentationFile.importPptx(await FileBlob.load(fileURLToPath(new URL('./template-original.pptx',import.meta.url))));
for (const surface of [...p.masters.items,...p.layouts.items]) {
  if(surface.shapes.items.length) console.log(JSON.stringify({surface:surface.name,id:surface.id,shapes:surface.shapes.items.map(s=>({id:s.id,name:s.name,geometry:s.geometry,position:s.position,text:String(s.text)}))}));
}
console.log(p.help('layout.shapes',{search:'delete|remove',include:['index','notes'],maxChars:3000}));
