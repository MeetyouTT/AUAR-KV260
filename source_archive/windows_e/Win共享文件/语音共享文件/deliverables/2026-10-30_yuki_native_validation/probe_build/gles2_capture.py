# SPDX-License-Identifier: AGPL-3.0-only
"""Diagnostic GLES2 rendering of native NekoMote frames, never a production host.

Ports the render-frame contract/shader composition from NekoMote commit
4fbf55aa6009df76ac40dc5f18e3781914bc464f (source/LICENSE is retained).
All surfaces are offscreen. Readback is for pictures, excluded from FPS claims.
"""
from pathlib import Path
import array
import ctypes as C
import json
import math
import os
import subprocess
import sys
from PIL import Image

I, U, F, V = C.c_int, C.c_uint, C.c_float, C.c_void_p
W, H = 423, 438
ROOT = Path('/home/root/aura-yuki-validation-20261030')
GL_ZERO = 0
GL_ONE = 1
GL_ONE_MINUS_SRC_COLOR = 0x0301
GL_SRC_ALPHA = 0x0302
GL_ONE_MINUS_SRC_ALPHA = 0x0303
GL_DST_ALPHA = 0x0304
GL_ONE_MINUS_DST_ALPHA = 0x0305
GL_DST_COLOR = 0x0306


class EGL:
    def __init__(self):
        pid = subprocess.check_output(['systemctl', 'show', 'aura-avatar-ui.service',
                                       '-p', 'MainPID', '--value'], text=True).strip()
        for item in Path('/proc/' + pid + '/environ').read_bytes().split(b'\0'):
            key, sep, value = item.partition(b'=')
            if sep and key in (b'DISPLAY', b'XAUTHORITY'):
                os.environ[key.decode()] = os.fsdecode(value)
        self.x = C.CDLL('libX11.so.6')
        self.x.XOpenDisplay.argtypes = [C.c_char_p]; self.x.XOpenDisplay.restype = V
        self.x.XCloseDisplay.argtypes = [V]
        self.e = C.CDLL('libEGL.so.1')
        signatures = [
            ('eglGetDisplay', V, [V]), ('eglInitialize', I, [V, C.POINTER(I), C.POINTER(I)]),
            ('eglBindAPI', I, [U]), ('eglChooseConfig', I, [V, C.POINTER(I), C.POINTER(V), I, C.POINTER(I)]),
            ('eglCreatePbufferSurface', V, [V, V, C.POINTER(I)]),
            ('eglCreateContext', V, [V, V, V, C.POINTER(I)]),
            ('eglMakeCurrent', I, [V, V, V, V]), ('eglDestroyContext', I, [V, V]),
            ('eglDestroySurface', I, [V, V]), ('eglTerminate', I, [V])]
        for name, restype, args in signatures:
            fun = getattr(self.e, name); fun.restype = restype; fun.argtypes = args
        self.xd = self.x.XOpenDisplay(None)
        if not self.xd: raise RuntimeError('Existing X display unavailable')
        self.d = self.e.eglGetDisplay(self.xd)
        if not self.e.eglInitialize(self.d, C.byref(I()), C.byref(I())):
            raise RuntimeError('EGL initialization failed')
        self.e.eglBindAPI(0x30A0)
        attrs = (I * 13)(0x3033, 1, 0x3040, 4, 0x3024, 8, 0x3023, 8, 0x3022, 8, 0x3021, 8, 0x3038)
        config, count = V(), I()
        if not self.e.eglChooseConfig(self.d, attrs, C.byref(config), 1, C.byref(count)) or count.value < 1:
            raise RuntimeError('No GLES2 pbuffer configuration')
        self.surface = self.e.eglCreatePbufferSurface(self.d, config, (I * 5)(0x3057, W, 0x3056, H, 0x3038))
        self.context = self.e.eglCreateContext(self.d, config, None, (I * 3)(0x3098, 2, 0x3038))
        if not self.context or not self.surface or not self.e.eglMakeCurrent(self.d, self.surface, self.surface, self.context):
            raise RuntimeError('GLES2 context creation failed')

    def close(self):
        self.e.eglMakeCurrent(self.d, None, None, None)
        self.e.eglDestroyContext(self.d, self.context)
        self.e.eglDestroySurface(self.d, self.surface)
        self.e.eglTerminate(self.d)
        self.x.XCloseDisplay(self.xd)


class GL:
    def __init__(self):
        self.lib = C.CDLL('libGLESv2.so.2')
        signatures = {
            'GetString': (C.c_char_p, [U]), 'GetError': (U, []),
            'CreateShader': (U, [U]), 'ShaderSource': (None, [U, I, C.POINTER(C.c_char_p), C.POINTER(I)]),
            'CompileShader': (None, [U]), 'GetShaderiv': (None, [U, U, C.POINTER(I)]),
            'GetShaderInfoLog': (None, [U, I, C.POINTER(I), V]),
            'CreateProgram': (U, []), 'AttachShader': (None, [U, U]),
            'BindAttribLocation': (None, [U, U, C.c_char_p]), 'LinkProgram': (None, [U]),
            'GetProgramiv': (None, [U, U, C.POINTER(I)]), 'UseProgram': (None, [U]),
            'GetProgramInfoLog': (None, [U, I, C.POINTER(I), V]),
            'GetUniformLocation': (I, [U, C.c_char_p]), 'Uniform1i': (None, [I, I]),
            'Uniform2f': (None, [I, F, F]), 'Uniform3f': (None, [I, F, F, F]),
            'GenTextures': (None, [I, C.POINTER(U)]), 'BindTexture': (None, [U, U]),
            'TexImage2D': (None, [U, I, I, I, I, I, U, U, V]),
            'TexParameteri': (None, [U, U, I]), 'ActiveTexture': (None, [U]),
            'GenFramebuffers': (None, [I, C.POINTER(U)]), 'BindFramebuffer': (None, [U, U]),
            'FramebufferTexture2D': (None, [U, U, U, U, I]), 'CheckFramebufferStatus': (U, [U]),
            'GenBuffers': (None, [I, C.POINTER(U)]), 'BindBuffer': (None, [U, U]),
            'BufferData': (None, [U, C.c_ssize_t, V, U]),
            'VertexAttribPointer': (None, [U, I, U, U, I, V]),
            'EnableVertexAttribArray': (None, [U]), 'Viewport': (None, [I, I, I, I]),
            'ClearColor': (None, [F, F, F, F]), 'Clear': (None, [U]),
            'Enable': (None, [U]), 'Disable': (None, [U]), 'Scissor': (None, [I, I, I, I]),
            'BlendFuncSeparate': (None, [U, U, U, U]), 'BlendEquationSeparate': (None, [U, U]),
            'DrawElements': (None, [U, I, U, V]), 'ReadPixels': (None, [I, I, I, I, U, U, V]),
            'PixelStorei': (None, [U, I])}
        for name, (restype, args) in signatures.items():
            fun = getattr(self.lib, 'gl' + name); fun.restype = restype; fun.argtypes = args
            setattr(self, name, fun)

    def check(self, operation):
        code = self.GetError()
        if code: raise RuntimeError(operation + ': GL error ' + hex(code))

    def program(self, vs, fs):
        shaders = []
        for kind, source in [(0x8B31, vs), (0x8B30, fs)]:
            shader = self.CreateShader(kind); encoded = C.c_char_p(source.encode())
            self.ShaderSource(shader, 1, C.byref(encoded), None); self.CompileShader(shader)
            ok = I(); self.GetShaderiv(shader, 0x8B81, C.byref(ok))
            if not ok.value:
                log = C.create_string_buffer(8192)
                self.GetShaderInfoLog(shader, 8192, None, log)
                raise RuntimeError(log.value.decode(errors='replace'))
            shaders.append(shader)
        program = self.CreateProgram()
        for shader in shaders: self.AttachShader(program, shader)
        for index, name in enumerate([b'position', b'uv', b'color']): self.BindAttribLocation(program, index, name)
        self.LinkProgram(program); ok = I(); self.GetProgramiv(program, 0x8B82, C.byref(ok))
        if not ok.value:
            log = C.create_string_buffer(8192)
            self.GetProgramInfoLog(program, 8192, None, log)
            raise RuntimeError('Shader link failed: ' + log.value.decode(errors='replace'))
        return program


VS = '''attribute vec2 position; attribute vec2 uv; attribute vec4 color;
uniform mediump vec2 output_size; uniform vec3 view;
varying mediump vec2 texture_uv; varying lowp vec4 vertex_color;
void main(){vec2 p=position*view.z+view.xy;
gl_Position=vec4(p.x*2.0/output_size.x-1.0,1.0-p.y*2.0/output_size.y,0.0,1.0);
texture_uv=uv;vertex_color=color;}'''
FS = '''precision mediump float;
varying mediump vec2 texture_uv;varying lowp vec4 vertex_color;
uniform sampler2D atlas;uniform sampler2D alpha_mask;uniform mediump vec2 output_size;
uniform int mask_write;uniform int use_mask;uniform int premultiply;uniform int protection_pass;
void main(){vec4 s=texture2D(atlas,texture_uv);
if(mask_write!=0){gl_FragColor=vec4(0.0,s.a,0.0,0.0);return;}
vec4 c=s*vertex_color;if(use_mask!=0)c.a*=texture2D(alpha_mask,gl_FragCoord.xy/output_size).g;
if(protection_pass!=0&&c.a<0.0000001)discard;
gl_FragColor=vec4(premultiply!=0?c.rgb*c.a:c.rgb,c.a);}'''


def bounds(frame, commands):
    points = [frame['vertices'][i][:2] for c in commands
              for i in frame['indices'][c['first_index']:c['first_index'] + c['index_count']]]
    if not points: raise RuntimeError('Empty draw bounds')
    return min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)


def mask_clip(frame, sources, contents, view):
    ox, oy, scale = view
    def rectangle(commands):
        left, top, right, bottom = bounds(frame, commands)
        return (max(0, math.floor(left * scale + ox) - 2),
                max(0, H - math.ceil(bottom * scale + oy) - 2),
                min(W, math.ceil(right * scale + ox) + 2),
                min(H, H - math.floor(top * scale + oy) + 2))
    a, b = rectangle(sources), rectangle(contents)
    left, bottom, right, top = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    return left, bottom, max(0, right - left), max(0, top - bottom)


class Renderer:
    def __init__(self, gl, document):
        self.g = g = gl; self.program = g.program(VS, FS); g.UseProgram(self.program)
        self.uniforms = {n: g.GetUniformLocation(self.program, n.encode()) for n in
                         ['atlas', 'alpha_mask', 'output_size', 'view', 'mask_write', 'use_mask', 'premultiply', 'protection_pass']}
        g.Uniform1i(self.uniforms['atlas'], 0); g.Uniform1i(self.uniforms['alpha_mask'], 1)
        self.textures = {}
        for texture in document['texture_bindings']:
            path = (ROOT / 'inputs/ems' / texture['path']).resolve()
            assert path.is_relative_to(ROOT / 'inputs/ems')
            with Image.open(path) as im:
                rgba = im.convert('RGBA'); data = rgba.tobytes()
                self.textures[texture['id']] = self.texture(*rgba.size, data)
        self.color = self.target(W, H, False)
        self.mw = 2 ** int(math.log2(W)); self.mh = 2 ** int(math.log2(H))
        self.mask = self.target(self.mw, self.mh, True)
        handles = (U * 2)(); g.GenBuffers(2, handles); self.vbo, self.ebo = handles
        for state in [0x0B71, 0x0B90, 0x0B44, 0x0BD0]: g.Disable(state)
        g.BlendEquationSeparate(0x8006, 0x8006); g.Enable(0x0BE2)
        g.check('renderer initialization')

    def texture(self, width, height, data=None, fivebit=False):
        g = self.g; handle = U(); g.GenTextures(1, C.byref(handle)); g.ActiveTexture(0x84C0)
        g.BindTexture(0x0DE1, handle.value); g.PixelStorei(0x0CF5, 1)
        pointer = C.cast(C.c_char_p(data), V) if data else None
        g.TexImage2D(0x0DE1, 0, 0x1908, width, height, 0, 0x1908, 0x8034 if fivebit else 0x1401, pointer)
        for key, val in [(0x2801, 0x2601), (0x2800, 0x2601), (0x2802, 0x812F), (0x2803, 0x812F)]:
            g.TexParameteri(0x0DE1, key, val)
        g.check('texture upload')
        return handle.value

    def target(self, width, height, fivebit):
        texture = self.texture(width, height, fivebit=fivebit)
        handle = U(); self.g.GenFramebuffers(1, C.byref(handle)); self.g.BindFramebuffer(0x8D40, handle.value)
        self.g.FramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, texture, 0)
        if self.g.CheckFramebufferStatus(0x8D40) != 0x8CD5: raise RuntimeError('Incomplete FBO')
        return handle.value, texture

    def geometry(self, frame):
        g = self.g
        vertices = array.array('f', (v for row in frame['vertices'] for v in row)).tobytes()
        if max(frame['indices'], default=0) >= 65536: raise RuntimeError('Probe index exceeds GLES2 uint16 range')
        indices = array.array('H', frame['indices']).tobytes()
        g.BindBuffer(0x8892, self.vbo); g.BufferData(0x8892, len(vertices), C.cast(C.c_char_p(vertices), V), 0x88E8)
        g.BindBuffer(0x8893, self.ebo); g.BufferData(0x8893, len(indices), C.cast(C.c_char_p(indices), V), 0x88E8)
        for index, count, offset in [(0, 2, 0), (1, 2, 8), (2, 4, 16)]:
            g.EnableVertexAttribArray(index); g.VertexAttribPointer(index, count, 0x1406, 0, 32, V(offset))

    def command(self, command):
        g = self.g; g.ActiveTexture(0x84C0); g.BindTexture(0x0DE1, self.textures[command['texture']])
        g.DrawElements(4, command['index_count'], 0x1403, V(command['first_index'] * 2))

    def render(self, frame, view, output):
        g = self.g; g.UseProgram(self.program); self.geometry(frame)
        g.Uniform2f(self.uniforms['output_size'], W, H); g.Uniform3f(self.uniforms['view'], *view)
        def mode(**values):
            for key, value in values.items(): g.Uniform1i(self.uniforms[key], value)
        mode(mask_write=0, use_mask=0, premultiply=0, protection_pass=0)
        g.BindFramebuffer(0x8D40, self.color[0]); g.Viewport(0, 0, W, H)
        g.Disable(0x0C11); g.ClearColor(0, 0, 0, 0); g.Clear(0x4000)
        straight = frame['composition'] == 1; previous_mask = None
        for command in frame['commands']:
            mid = command['mask']
            if mid and mid != previous_mask:
                definition = frame['masks'][mid - 1]
                sources = frame['mask_commands'][definition['first_command']:definition['first_command'] + definition['command_count']]
                clip = mask_clip(frame, sources, [c for c in frame['commands'] if c['mask'] == mid], view)
                g.ActiveTexture(0x84C1); g.BindTexture(0x0DE1, 0)
                g.BindFramebuffer(0x8D40, self.mask[0]); g.Viewport(0, 0, self.mw, self.mh)
                g.Disable(0x0C11); g.ClearColor(0, 0, 0, 0); g.Clear(0x4000)
                g.Enable(0x0C11)
                g.Scissor(int(clip[0] * self.mw / W), int(clip[1] * self.mh / H),
                          int(clip[2] * self.mw / W), int(clip[3] * self.mh / H))
                mode(mask_write=1, use_mask=0)
                g.BlendFuncSeparate(GL_ONE, GL_ONE_MINUS_SRC_COLOR, GL_ZERO, GL_ONE)
                for source in sources: self.command(source)
                g.BindFramebuffer(0x8D40, self.color[0]); g.Viewport(0, 0, W, H)
                g.ActiveTexture(0x84C1); g.BindTexture(0x0DE1, self.mask[1])
                mode(mask_write=0); previous_mask = mid
            if mid: g.Enable(0x0C11); g.Scissor(*clip)
            else: g.Disable(0x0C11)
            mode(use_mask=int(bool(mid)), premultiply=int(command['blend'] == 2 or not straight))
            if straight and command['protection'] == 1:
                mode(protection_pass=1)
                g.BlendFuncSeparate(GL_ONE_MINUS_DST_ALPHA, GL_DST_ALPHA, GL_ZERO, GL_ONE)
                self.command(command); mode(protection_pass=0)
            if command['blend'] == 2:
                g.BlendFuncSeparate(GL_DST_COLOR, GL_ONE_MINUS_SRC_ALPHA, GL_ZERO, GL_ONE)
            elif command['blend'] == 0:
                g.BlendFuncSeparate(GL_SRC_ALPHA if straight else GL_ONE, GL_ONE_MINUS_SRC_ALPHA,
                                    GL_ONE, GL_ONE_MINUS_SRC_ALPHA)
            else: raise RuntimeError('Unsupported probe blend')
            self.command(command)
        # Composite the protected-straight model once over the board background.
        quad = {'vertices': [[0,0,0,1,1,1,1,1],[W,0,1,1,1,1,1,1],[W,H,1,0,1,1,1,1],[0,H,0,0,1,1,1,1]], 'indices': [0,1,2,0,2,3]}
        self.geometry(quad); g.BindFramebuffer(0x8D40, 0); g.Viewport(0, 0, W, H)
        g.Disable(0x0C11)
        g.ClearColor(252/255, 252/255, 243/255, 1); g.Clear(0x4000)
        g.Uniform3f(self.uniforms['view'], 0, 0, 1); mode(use_mask=0, mask_write=0, premultiply=int(straight))
        g.ActiveTexture(0x84C0); g.BindTexture(0x0DE1, self.color[1])
        g.BlendFuncSeparate(GL_ONE, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA)
        g.DrawElements(4, 6, 0x1403, None)
        g.check('render')
        pixels = (C.c_ubyte * (W * H * 4))(); g.ReadPixels(0, 0, W, H, 0x1908, 0x1401, pixels)
        g.check('diagnostic readback')
        Image.frombytes('RGBA', (W, H), bytes(pixels)).transpose(Image.FLIP_TOP_BOTTOM).save(output)


def main():
    document = json.loads(Path(sys.argv[1]).read_text()); output = Path(sys.argv[2]); output.mkdir(exist_ok=True)
    if not document['ok']: raise RuntimeError('Native runtime did not produce a valid frame')
    context = EGL()
    try:
        g = GL(); renderer = Renderer(g, document); rendered = []
        authored = json.loads((ROOT / 'inputs/ems/yuk_0.ems.json').read_text(encoding='utf-8-sig'))
        markers = authored['metadata']['charaProfile']['pixelMarker']
        for scenario in document['scenarios']:
            left, top, right, bottom = (markers['boundsLeft'], markers['boundsTop'],
                                        markers['boundsRight'], markers['boundsBottom'])
            bottom = top + (bottom - top) * 0.48
            scale = min(W / (right - left), H / (bottom - top)) * 0.88
            view = (W/2 - (left + right)/2 * scale, H/2 - (top + bottom)/2 * scale, scale)
            for snapshot in scenario['snapshots']:
                name = scenario['name'] + '-' + str(snapshot['tick']).zfill(4) + '.png'
                renderer.render(snapshot['frame'], view, output / name); rendered.append(name)
        report = {'ok': True, 'renderer': g.GetString(0x1F01).decode(), 'version': g.GetString(0x1F02).decode(),
                  'offscreen_only': True, 'production_host': False, 'performance_certified': False,
                  'pixel_equivalence_certified': False, 'view_basis': 'original authored charaProfile markers, bustFraction .48, pad .06',
                  'mask_contract': 'five-bit alpha union, source/content clip, two-pixel border', 'images': rendered}
        (output / 'render-report.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report))
    finally: context.close()


if __name__ == '__main__': main()
