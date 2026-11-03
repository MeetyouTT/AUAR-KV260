"""Keep an untested GPU-buffer experiment outside the candidate under test."""
from pathlib import Path
import difflib,json
root=Path(__file__).parent/'host';experiment=root/'experiments/static_quad'
experiment.mkdir(parents=True,exist_ok=True)
for name in ('gles2_renderer.hpp','gles2_renderer.cpp'):
    (experiment/name).write_bytes((root/name).read_bytes())
path=root/'gles2_renderer.hpp';text=path.read_text(encoding='utf8')
text=text.replace('GLuint program_{},vbo_{},ebo_{},quad_vbo_{},quad_ebo_{};','GLuint program_{},vbo_{},ebo_{};')
text=text.replace('  void attributes();\n','');path.write_text(text,encoding='utf8')
path=root/'gles2_renderer.cpp';text=path.read_text(encoding='utf8')
text=text.replace(''' glGenBuffers(1,&vbo_);glGenBuffers(1,&ebo_);glGenBuffers(1,&quad_vbo_);glGenBuffers(1,&quad_ebo_);
 constexpr std::array<std::uint16_t,6> quad_indices{0,1,2,0,2,3};
 glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,quad_ebo_);glBufferData(GL_ELEMENT_ARRAY_BUFFER,sizeof(quad_indices),quad_indices.data(),GL_STATIC_DRAW);
''',''' glGenBuffers(1,&vbo_);glGenBuffers(1,&ebo_);
''')
text=text.replace(' if(quad_vbo_)glDeleteBuffers(1,&quad_vbo_);\n if(quad_ebo_)glDeleteBuffers(1,&quad_ebo_);\n','')
quad=''' const std::array<RenderVertex,4> quad{{{0,0,0,1,{1,1,1,1}},{float(w),0,1,1,{1,1,1,1}},
  {float(w),float(h),1,0,{1,1,1,1}},{0,float(h),0,0,{1,1,1,1}}}};
'''
text=text.replace(quad+''' glBindBuffer(GL_ARRAY_BUFFER,quad_vbo_);glBufferData(GL_ARRAY_BUFFER,sizeof(quad),quad.data(),GL_STATIC_DRAW);
''','')
text=text.replace(''' attributes();
}
void Renderer::attributes(){
 static_assert(sizeof(RenderVertex)==32);''',''' static_assert(sizeof(RenderVertex)==32);''')
text=text.replace(''' // A separate immutable quad avoids overwriting vertices still used by model
 // draws; Mali otherwise waits for those GPU jobs inside glBufferSubData.
 glBindBuffer(GL_ARRAY_BUFFER,quad_vbo_);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,quad_ebo_);attributes();
''',quad+''' constexpr std::array<std::uint32_t,6> qi{0,1,2,0,2,3};geometry(quad,qi);
''')
assert 'quad_vbo_' not in text and 'Renderer::attributes' not in text
path.write_text(text,encoding='utf8')
(experiment/'status.json').write_text(json.dumps({'status':'UNTESTED_NOT_INCLUDED','reason':'candidate already entered timed validation; retain exactly tested renderer'},indent=2),encoding='utf8')
print('TESTED_RENDERER_RESTORED; STATIC_QUAD_EXPERIMENT_EXCLUDED')
