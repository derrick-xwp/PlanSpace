"""Read-only manuscript evidence checks and PDF QA thumbnails."""
from pathlib import Path
import re
import json
import fitz
from PIL import Image, ImageDraw

paper = Path(__file__).resolve().parents[1]
old = (paper / 'revisions/pre_syg_20260919/main.tex').read_text()
new = (paper / 'main.tex').read_text()
out = paper / 'tmp/syg_review'
out.mkdir(parents=True, exist_ok=True)

def citations(text):
    return sorted({key.strip() for block in re.findall(r'\\cite\w*\{([^}]+)\}', text)
                   for key in block.split(',')})

assert citations(old) == citations(new), 'Citation inventory changed'
assert re.findall(r'\\label\{([^}]+)\}', old) == re.findall(r'\\label\{([^}]+)\}', new)
assert re.findall(r'\\begin\{equation\}.*?\\end\{equation\}', old, re.S) == re.findall(
    r'\\begin\{equation\}.*?\\end\{equation\}', new, re.S)
old_rows = [s.strip() for s in old.splitlines() if '&' in s and re.search(r'\d/\d', s)]
new_rows = [s.strip() for s in new.splitlines() if '&' in s and re.search(r'\d/\d', s)]
assert old_rows == new_rows, 'Physical audit rows changed'

doc = fitz.open(paper / 'build/main.pdf')
texts = [p.get_text() for p in doc]
(out / 'full_text.txt').write_text('\n\f\n'.join(texts))
assert all('??' not in t for t in texts), 'Unresolved reference in PDF'
for start in range(0, len(doc), 4):
    sheet = Image.new('RGB', (1240, 1660), '#bbbbbb')
    draw = ImageDraw.Draw(sheet)
    for offset in range(4):
        page_id = start + offset
        if page_id >= len(doc):
            break
        pix = doc[page_id].get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
        img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        img.thumbnail((600, 800))
        x, y = (offset % 2) * 620 + 10, (offset // 2) * 830 + 22
        sheet.paste(img, (x, y))
        draw.text((x, y-17), f'Page {page_id+1}', fill='black')
    sheet.save(out / f'contact_{start+1:02d}.png')
report = {
    'pages': len(doc), 'citations_unchanged': True,
    'labels_unchanged': True, 'display_equations_unchanged': True,
    'physical_table_values_unchanged': True,
    'figure_pages': {str(i+1): [m.group(0) for m in re.finditer(r'Figure \d+:', t)]
                     for i,t in enumerate(texts) if re.search(r'Figure \d+:', t)},
}
(out / 'checks.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
