import zipfile, xml.etree.ElementTree as ET, pathlib, collections, json, sys
sys.stdout.reconfigure(encoding='utf-8')
root=pathlib.Path(__file__).parent
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
for file in ['template-original.pptx','poster-v1.candidate.pptx']:
    with zipfile.ZipFile(root/file) as z:
        print(file)
        for part in ['ppt/slides/slide1.xml','ppt/slideMasters/slideMaster1.xml','ppt/slideLayouts/slideLayout8.xml']:
            if part not in z.namelist():continue
            t=ET.fromstring(z.read(part))
            shapes=t.findall('.//p:sp',ns)
            lines=t.findall('.//p:cxnSp',ns)
            print(part,'shapes',len(shapes),'lines',len(lines),'pics',len(t.findall('.//p:pic',ns)))
            print('colors',collections.Counter(n.get('val') for n in t.findall('.//a:srgbClr',ns)))
            if 'Master' in part:
                for s in t.findall('.//p:sp',ns)+lines:
                    n=s.find('.//p:cNvPr',ns)
                    print(n.attrib)
            if 'slides/' in part:
                for s in shapes:
                    name=s.find('.//p:cNvPr',ns).get('name','')
                    if name in ['verification-body','dialogue-sequence','implementation-body']:
                        print(name,ET.tostring(s.find('p:txBody',ns),encoding='unicode')[:5500])
