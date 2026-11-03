import math,html
from pathlib import Path
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
INK='#142638'
MUTED='#536576'
LINE='#AAB8C4'
class Figure:
    """One geometry source for editable SVG and vector PDF."""

    def __init__(self, width: int, height: int):
        self.w, self.h = width, height
        self.ops = []
        self.text_bounds = []

    def rect(self, x, y, w, h, fill='white', stroke=LINE, radius=12, sw=2):
        self.ops.append(('rect', x, y, w, h, fill, stroke, radius, sw))

    def path(self, points, color=INK, sw=3, arrow=False, start_arrow=False, dash=None):
        self.ops.append(('path', points, color, sw, arrow, start_arrow, dash))

    def circle(self, x, y, radius=4, fill=INK):
        self.ops.append(('circle', x, y, radius, fill))

    def text(self, x, y, value, size=27, color=INK, bold=False, align='left', maxw=None):
        font = 'YaHeiBold' if bold else 'YaHei'
        width = pdfmetrics.stringWidth(value, font, size)
        if maxw is not None and width > maxw + 0.2:
            raise ValueError(f'Text too wide: {value!r}: {width:.1f} > {maxw:.1f}')
        left = x if align == 'left' else x - width if align == 'right' else x - width / 2
        if left < 0 or left + width > self.w + 0.1 or y < size * 0.8 or y > self.h - 2:
            raise ValueError(f'Text outside figure: {value!r}')
        self.text_bounds.append([left, y - size, left + width, y + size * .25, value])
        self.ops.append(('text', x, y, value, size, color, bold, align))

    def wrap(self, x, y, value, width, size=24, leading=36, color=MUTED, bold=False):
        lines, line = [], ''
        font = 'YaHeiBold' if bold else 'YaHei'
        for ch in value:
            if ch == '\n' or (line and pdfmetrics.stringWidth(line + ch, font, size) > width):
                lines.append(line)
                line = '' if ch == '\n' else ch
            else:
                line += ch
        if line:
            lines.append(line)
        for i, line in enumerate(lines):
            self.text(x, y + leading * i, line, size, color, bold, maxw=width)
        return y + leading * len(lines)

    @staticmethod
    def head(tip, prev, length=13, half_width=6):
        dx, dy = tip[0] - prev[0], tip[1] - prev[1]
        n = math.hypot(dx, dy)
        ux, uy = dx / n, dy / n
        bx, by = tip[0] - ux * length, tip[1] - uy * length
        return [tip, (bx - uy * half_width, by + ux * half_width), (bx + uy * half_width, by - ux * half_width)]

    def to_svg(self, path: Path):
        s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">',
             '<title>KV260 接线资料核对图 V1</title>',
             '<desc>工程约束、B03参考映射与既有5V方案整理；外部接线尚待实物复核。</desc>',
             '<rect width="100%" height="100%" fill="white"/>']
        for op in self.ops:
            if op[0] == 'rect':
                _, x, y, w, h, fill, stroke, radius, sw = op
                s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
            elif op[0] == 'path':
                _, points, col, sw, arrow, start, dash = op
                pts = ' '.join(f'{x},{y}' for x, y in points)
                dashed = f' stroke-dasharray="{dash}"' if dash else ''
                s.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-linejoin="round"{dashed}/>')
                for tip, prev in ([(points[-1], points[-2])] if arrow else []) + ([(points[0], points[1])] if start else []):
                    pts = ' '.join(f'{x:.3f},{y:.3f}' for x, y in self.head(tip, prev))
                    s.append(f'<polygon points="{pts}" fill="{col}"/>')
            elif op[0] == 'circle':
                _, x, y, r, col = op
                s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')
            else:
                _, x, y, value, size, col, bold, align = op
                anchor = {'left': 'start', 'right': 'end', 'center': 'middle'}[align]
                s.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{col}">{html.escape(value)}</text>')
        s.append('</svg>')
        path.write_text('\n'.join(s), encoding='utf8')

    def to_pdf(self, c: canvas.Canvas, page_size):
        pw, ph = page_size
        scale = min(pw / self.w, ph / self.h)
        ox, oy = (pw - self.w * scale) / 2, (ph - self.h * scale) / 2
        c.saveState()
        c.translate(ox, oy)
        c.scale(scale, scale)
        for op in self.ops:
            if op[0] == 'rect':
                _, x, y, w, h, fill, stroke, radius, sw = op
                c.setFillColor(colors.toColor(fill))
                c.setStrokeColor(colors.HexColor(stroke))
                c.setLineWidth(sw)
                c.roundRect(x, self.h-y-h, w, h, radius, fill=1, stroke=1)
            elif op[0] == 'path':
                _, points, col, sw, arrow, start, dash = op
                c.setStrokeColor(colors.HexColor(col))
                c.setLineWidth(sw)
                c.setDash([float(x) for x in dash.split(',')] if dash else [])
                p = c.beginPath()
                p.moveTo(points[0][0], self.h-points[0][1])
                for x, y in points[1:]:
                    p.lineTo(x, self.h-y)
                c.drawPath(p, stroke=1)
                c.setDash([])
                c.setFillColor(colors.HexColor(col))
                for tip, prev in ([(points[-1], points[-2])] if arrow else []) + ([(points[0], points[1])] if start else []):
                    tri = self.head(tip, prev)
                    p = c.beginPath()
                    p.moveTo(tri[0][0], self.h-tri[0][1])
                    for x, y in tri[1:]:
                        p.lineTo(x, self.h-y)
                    p.close()
                    c.drawPath(p, fill=1, stroke=0)
            elif op[0] == 'circle':
                _, x, y, r, col = op
                c.setFillColor(colors.HexColor(col))
                c.circle(x, self.h-y, r, stroke=0, fill=1)
            else:
                _, x, y, value, size, col, bold, align = op
                c.setFont('YaHeiBold' if bold else 'YaHei', size)
                c.setFillColor(colors.HexColor(col))
                getattr(c, {'left': 'drawString', 'right': 'drawRightString', 'center': 'drawCentredString'}[align])(x, self.h-y, value)
        c.restoreState()
