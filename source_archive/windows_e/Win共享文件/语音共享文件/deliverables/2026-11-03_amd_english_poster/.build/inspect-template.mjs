import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Presentation,PresentationFile,FileBlob} from '@oai/artifact-tool';

const here=path.dirname(fileURLToPath(import.meta.url));
const p=await PresentationFile.importPptx(await FileBlob.load(path.join(here,'template-original.pptx')));
const info=await p.inspect({kind:'slide,shape,textbox,image,layout',maxChars:65000});
await fs.writeFile(path.join(here,'artifact-template-inspection.ndjson'),info.ndjson);
await fs.writeFile(path.join(here,'template-artifact.png'),new Uint8Array(await (await p.export({slide:p.slides.items[0],format:'png',scale:1.5})).arrayBuffer()));
await fs.writeFile(path.join(here,'template-layout.json'),new Uint8Array(await (await p.slides.items[0].export({format:'layout'})).arrayBuffer()));
console.log(JSON.stringify({slides:p.slides.items.length,shapes:p.slides.items[0].shapes.items.length,images:p.slides.items[0].images.items.length}));
