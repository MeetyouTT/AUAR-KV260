from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def apply_simsun(doc):
    def fonts(parent):
        f=parent.find(qn('w:rFonts'))
        if f is None:
            f=OxmlElement('w:rFonts');parent.insert(0,f)
        for key in list(f.attrib):
            if 'Theme' in key or key.endswith('hint'):
                del f.attrib[key]
        for attr in ['ascii','hAnsi','eastAsia','cs']:
            f.set(qn('w:'+attr),'宋体')
    for st in doc.styles:
        rp=st.element.find(qn('w:rPr'))
        if rp is None:rp=OxmlElement('w:rPr');st.element.append(rp)
        fonts(rp)
    defaults=doc.styles.element.find(qn('w:docDefaults'))
    if defaults is None:defaults=OxmlElement('w:docDefaults');doc.styles.element.insert(0,defaults)
    rd=defaults.find(qn('w:rPrDefault'))
    if rd is None:rd=OxmlElement('w:rPrDefault');defaults.append(rd)
    rp=rd.find(qn('w:rPr'))
    if rp is None:rp=OxmlElement('w:rPr');rd.append(rp)
    fonts(rp)
    roots=[doc.element]
    for sec in doc.sections:
        roots.extend([sec.header._element,sec.footer._element])
    for root in roots:
        for run in root.iter(qn('w:r')):
            rp=run.find(qn('w:rPr'))
            if rp is None:rp=OxmlElement('w:rPr');run.insert(0,rp)
            fonts(rp)
