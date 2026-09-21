"""Render every delivered page and record textual/layout build gates."""
from pathlib import Path
import hashlib,json,re,sys
import pymupdf
from PIL import Image,ImageOps,ImageDraw

root=Path(__file__).resolve().parents[2]
release=root/'release/reviewer_clean_20260919'
pdf=release/'PlanSpace_ICLR2027.pdf'
out=release/'visual_qa';out.mkdir(exist_ok=True)
doc=pymupdf.open(pdf)
conclusion=[];conclusion_end=[];images=[]
for i,page in enumerate(doc):
    text=page.get_text()
    assert '??' not in text,(i+1,'unresolved reference')
    if re.search(r'\bCONCLUSION\b',text):conclusion.append(i+1)
    if 'source of each failure explicit' in text:conclusion_end.append(i+1)
    pix=page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
    path=out/f'page_{i+1:02d}.png';pix.save(path)
    im=Image.open(path).convert('RGB');im.thumbnail((612,792))
    tile=Image.new('RGB',(632,822),'#dddddd');tile.paste(im,(10,22))
    ImageDraw.Draw(tile).text((10,5),f'Page {i+1}',fill='black');images.append(tile)
    for d in page.get_drawings():
        fill=d.get('fill')
        assert not(fill and len(fill)==3 and fill[0]>.9 and fill[1]>.9 and fill[2]<.2),(i+1,'yellow fill')
for start in range(0,len(images),4):
    sheet=Image.new('RGB',(1264,1644),'white')
    for j,im in enumerate(images[start:start+4]):sheet.paste(im,((j%2)*632,(j//2)*822))
    sheet.save(out/f'sheet_{start//4+1:02d}.png')
log=(release/'standalone_final.log').read_text()
assert not re.search(r'Overfull|undefined references|Citation .* undefined|^!',log,re.M)
assert len(conclusion)==1 and conclusion[0]<=9,conclusion
assert conclusion_end==[9],conclusion_end
report={'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'pages':len(doc),
        'conclusion_page':conclusion[0],'metadata':doc.metadata,
        'text_and_build_gates':'PASS','visual_inspection':'PENDING',
        'rendered_pages':len(images)}
(release/'pdf_qa.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
