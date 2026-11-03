"""Local read-only source invariants; never compile, render or access the board."""
from pathlib import Path
import hashlib
import json
import re
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
original=(BASE/'host/gles2_renderer.cpp').read_text(encoding='utf8')
candidate=(HERE/'gles2_renderer.cpp').read_text(encoding='utf8')
base=json.loads((HERE/'base-provenance.json').read_text(encoding='utf8'))
def shader_blocks(text):
    return re.findall(r'const char\* (?:vertex_shader|fragment_shader)=R"\((.*?)\)";',text,re.S)
checks={
    'host_base_unchanged':all(hashlib.sha256((BASE/'host'/n).read_bytes()).hexdigest()==h
                              for n,h in base['hashes'].items()),
    'shaders_equal':shader_blocks(original)==shader_blocks(candidate) and len(shader_blocks(original))==2,
    'tile_uv_equal':(BASE/'host/tile_uv.hpp').read_bytes()==(HERE/'tile_uv.hpp').read_bytes(),
    'draw_elements_sites_equal_count':original.count('glDrawElements(')==candidate.count('glDrawElements('),
    'clear_sites_equal_count':original.count('glClear(GL_COLOR_BUFFER_BIT)')==candidate.count('glClear(GL_COLOR_BUFFER_BIT)'),
    'no_new_dynamic_container':candidate.count('std::vector')==original.count('std::vector'),
    'per_draw_reset_before_resize':'state_=StateCache{};\n GLint output_fbo' in candidate,
    'per_draw_reset_after_resize':'state_=StateCache{};\n glUseProgram(program_)' in candidate,
}
assert all(checks.values()),checks
state_calls=[]
for number,line in enumerate(candidate.splitlines(),1):
    if any(name in line for name in ['glUniform1i(','glBlendFuncSeparate(','glActiveTexture(',
        'glBindTexture(','glBindFramebuffer(','glViewport(','glScissor(','glClearColor(','GL_SCISSOR_TEST']):
        state_calls.append(dict(line=number,text=line.strip()))
report={'scope':'source invariants and manual state-flow review; not C++ or GPU validation',
    'checks':checks,'cached_state_bytes_upper_bound':160,'expected_arm_cache_bytes':120,
    'gpu_resident_bytes_added':0,'per_draw_heap_allocations_added':0,
    'state_setter_sites':state_calls,'compiled':False,'gpu_validated':False,'production_modified':False}
(HERE/'static-review.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(checks,indent=2))
for item in state_calls:print(str(item['line'])+': '+item['text'])
