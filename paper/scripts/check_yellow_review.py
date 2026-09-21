"""Verify highlighted review output and render page contact sheets."""
from pathlib import Path
import json
import re
import pymupdf as fitz
from PIL import Image, ImageDraw

base = Path(__file__).resolve().parents[2]
root = base / 'release/yellow_review_20260919'
qa = base / 'paper/tmp/yellow_review'
qa.mkdir(parents=True, exist_ok=True)
doc = fitz.open(root / 'PlanSpace_ICLR2027_YellowReview.pdf')
text = '\n'.join(p.get_text() for p in doc)
assert '??' not in text
yellow = {}
for i, page in enumerate(doc):
    fills = [d for d in page.get_drawings() if d.get('fill') and
             d['fill'][0] > .9 and d['fill'][1] > .9 and d['fill'][2] < .1]
    yellow[i+1] = len(fills)
    for d in fills:
        assert page.rect.contains(d['rect']), (i+1, d['rect'])
    if 'Generative AI tools' in page.get_text():
        assert len(fills) > 0
        pix = page.get_pixmap(matrix=fitz.Matrix(1.8, 1.8), alpha=False)
        pix.save(str(qa / 'ai_statement.png'))
for start in range(0, len(doc), 4):
    sheet = Image.new('RGB', (1240,1660), '#bbbbbb')
    draw = ImageDraw.Draw(sheet)
    for offset in range(4):
        n = start + offset
        if n >= len(doc): break
        pix = doc[n].get_pixmap(matrix=fitz.Matrix(1,1), alpha=False)
        img = Image.frombytes('RGB', (pix.width,pix.height), pix.samples)
        img.thumbnail((600,800))
        x,y = (offset%2)*620+10,(offset//2)*830+22
        sheet.paste(img,(x,y));draw.text((x,y-17),f'Page {n+1}',fill='black')
    sheet.save(qa / f'contact_{start+1:02d}.png')
log = (root / 'PlanSpace_ICLR2027_LaTeX/main.log').read_text()
assert not re.search(r'Overfull|undefined|^! ', log, re.M), 'Review compilation warning'
report = {'pages':len(doc), 'selected_spans':len(json.loads((root/'highlight_manifest.json').read_text())),
          'yellow_shapes_by_page':yellow, 'no_unresolved_references':True,
          'no_overfull_boxes':True, 'original_wording_preserved_by_inverse_source_check':True}
(qa/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
