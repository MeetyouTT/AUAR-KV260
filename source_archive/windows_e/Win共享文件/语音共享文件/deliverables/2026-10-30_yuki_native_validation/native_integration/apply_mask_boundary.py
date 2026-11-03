"""Apply only after mesh owner freezes candidate_core. Pinned source is untouched.

The source layer contributes its own draw resource. A referenced motion expands
that resource in a separate compiled scope; authored children attached to the
source layer are independent draws and must not feed its mask alpha.
"""
from pathlib import Path
import hashlib,json
BASE=Path(__file__).resolve().parent
path=BASE/'candidate_core/src/runtime/geometry_scene.cpp'
old='''                if (ancestor.valid())
                {
                    mask.members.push_back(NodeId{static_cast<std::uint32_t>(j)});
                    data->nodes[j].mask_source = true;
                }
'''
new='''                if (ancestor.valid())
                {
                    // A source label names its own draw resource, not every
                    // authored child attached to that layer. Referenced motion
                    // expansion has a new scope; explicit children retain the
                    // source's scope and are separate draws. Including those
                    // children makes a stencil content its own coverage source.
                    // Original-engine PSB fixtures: motion_self, sprite_self,
                    // ordinary_child and other_stencil (Yuki validation).
                    auto branch = NodeId{static_cast<std::uint32_t>(j)};
                    while (branch != ancestor && data->nodes[branch.value].parent != ancestor)
                        branch = data->nodes[branch.value].parent;
                    if (branch != ancestor && data->nodes[branch.value].scope ==
                                                  data->nodes[ancestor.value].scope)
                        continue;
                    mask.members.push_back(NodeId{static_cast<std::uint32_t>(j)});
                    data->nodes[j].mask_source = true;
                }
'''
before=path.read_bytes()
text=before.decode('utf8')
if new in text:print('MASK_BOUNDARY_ALREADY_APPLIED');raise SystemExit(0)
assert text.count(old)==1,'Mask patch anchor changed; review required'
path.write_text(text.replace(old,new),encoding='utf8')
report={'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
 'semantics':'source own resource plus its referenced-motion expansion; exclude source explicit child branches',
 'original_mask_assertions_retained':True,'diagnostic_selfguard_bypass_used':False,
 'reference_fixtures':['motion_self','sprite_self','ordinary_child','other_stencil'],
 'pixel_validation':'pending board build','production_deployed':False}
(BASE/'mask-boundary-provenance.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
