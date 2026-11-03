import path from 'node:path';
import { fileURLToPath } from 'node:url';
process.env.RUNTIME_NODE_MODULES='C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const { finalizePresentation } = await import('file:///C:/Users/REVO1/.codex/plugins/cache/openai-primary-runtime/presentations/26.1026.10807/skills/presentations/container_tools/artifact_tool_utils.mjs');

const buildDir=path.dirname(fileURLToPath(import.meta.url));
const workspaceDir=path.dirname(buildDir);
const skillDir='C:/Users/REVO1/.codex/plugins/cache/openai-primary-runtime/presentations/26.1026.10807/skills/presentations';
const finalPath=path.join(workspaceDir,'output','AUAR_雪妃_28秒项目动画.pptx');
const result=await finalizePresentation({
  workspaceDir,
  candidatePath:path.join(buildDir,'animated_candidate.pptx'),
  finalPath,
  pythonExecutable:'C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
  integrityValidatorPath:path.join(skillDir,'container_tools','inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skillDir,'container_tools','inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
  explicitTotalSlideCount:6,
  requiredNativeTableOwnerSlides:[],
  requiredNativeChartOwnerSlides:[],
  fontPolicy:{basis:'design',families:['Microsoft YaHei']},
  verifyArtifactToolImport:true,
  receiptPath:path.join(buildDir,'final_validation.json'),
});
console.log(JSON.stringify(result));
