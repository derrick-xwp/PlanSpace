"""Check the compiled final review and render every page for visual inspection."""
from pathlib import Path
import json
import re
import sys
import pymupdf as fitz
from PIL import Image, ImageDraw

base = Path(__file__).resolve().parents[2]
release_name = sys.argv[1] if len(sys.argv)>1 else 'final_check_20260919'
root = base/'release'/release_name
qa = base/'paper/tmp'/release_name
qa.mkdir(parents=True, exist_ok=True)
doc = fitz.open(root/'PlanSpace_FinalCheck.pdf')
assert '??' not in ''.join(p.get_text() for p in doc)
log = (root/'PlanSpace_ICLR2027_LaTeX/main.log').read_text()
assert not re.search(r'Overfull|undefined|^! ', log, re.M)
yellow = {}
for i, p in enumerate(doc):
    fills = [d for d in p.get_drawings() if d.get('fill') and
             d['fill'][0] > .9 and d['fill'][1] > .9 and d['fill'][2] < .1]
    yellow[i+1] = len(fills)
    assert all(p.rect.contains(d['rect']) for d in fills)
    if 'Generative AI tools' in p.get_text():
        assert fills
    p.get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(qa/f'page_{i+1:02d}.png')
for start in range(0,len(doc),4):
    sheet = Image.new('RGB',(1240,1660),'#bbbbbb')
    draw = ImageDraw.Draw(sheet)
    for j in range(4):
        n = start+j
        if n >= len(doc):
            break
        im = Image.open(qa/f'page_{n+1:02d}.png').convert('RGB')
        im.thumbnail((600,800))
        x,y = (j%2)*620+10,(j//2)*830+22
        sheet.paste(im,(x,y)); draw.text((x,y-17),f'Page {n+1}',fill='black')
    sheet.save(qa/f'contact_{start+1:02d}.png')
result = {'pages':len(doc),'yellow_shapes_by_page':yellow,
          'no_overfull_or_unresolved_references':True,
          'highlights':len(json.loads((root/'PlanSpace_ICLR2027_LaTeX/highlight_manifest.json').read_text()))}
(qa/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
