from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader

root=Path(__file__).resolve().parent.parent
target=root/'output'/'poster'/'AUAR_项目海报_A3.pdf'
c=canvas.Canvas(str(target),pagesize=A3,pageCompression=1)
c.setTitle('AUAR·雪妃 项目海报')
c.setAuthor('AUAR 项目')
c.drawImage(ImageReader(str(root/'output'/'poster'/'AUAR_项目海报_A3_300dpi.png')),0,0,width=A3[0],height=A3[1])
c.showPage();c.save()
r=PdfReader(target)
assert len(r.pages)==1
assert abs(float(r.pages[0].mediabox.width)-A3[0])<.01
assert abs(float(r.pages[0].mediabox.height)-A3[1])<.01
print(str(target))
