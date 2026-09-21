"""Package the explicitly selected older manuscript, without replacing paper/."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import zipfile

base = Path(__file__).resolve().parents[2]
original = base / 'release/section3_gap_revision_20260920'
name = 'PlanSpace_ICLR2027_LaTeX'
source = original / name
out = base / 'release/appendix_reproducibility_20260920'
out.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(original / (name + '.zip')) as z:
    files = [str(Path(n).relative_to(name)) for n in z.namelist() if not n.endswith('/')]
files.append('DIFF_SUMMARY_ZH.md')
with tempfile.TemporaryDirectory(prefix='planspace-appendix-release-') as tmp:
    folder = Path(tmp) / name
    for item in files:
        dest = folder / item
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / item, dest)
    archive = out / (name + '.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for item in files:
            z.write(folder / item, name + '/' + item)
    with (out / 'standalone_compile.log').open('w') as log:
        subprocess.run(['latexmk', '-pdf', '-interaction=nonstopmode',
                        '-halt-on-error', 'main.tex'], cwd=folder,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    shutil.copy2(folder / 'main.pdf', out / 'PlanSpace_ICLR2027.pdf')
    shutil.copy2(folder / 'main.log', out / 'standalone_final.log')
for path in (archive, out / 'PlanSpace_ICLR2027.pdf'):
    path.with_suffix(path.suffix + '.sha256').write_text(
        hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n')
print(out)
