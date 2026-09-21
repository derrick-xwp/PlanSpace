"""Package current verified manuscript without regenerating frozen experiments."""
import sys,shutil,tempfile,subprocess,zipfile,hashlib
from pathlib import Path
base=Path(__file__).resolve().parents[2];sys.path.insert(0,str(base/'scripts'))
from build_iclr_submission_package import package_files,verify_submission_archive,PACKAGE_NAME
paper=base/'paper';out=base/'release'/ (sys.argv[1] if len(sys.argv)>1 else 'native_home_revision');out.mkdir(parents=True,exist_ok=True)
files=package_files('v0_9')
with tempfile.TemporaryDirectory(prefix='planspace-native-paper-') as tmp:
    folder=Path(tmp)/PACKAGE_NAME;folder.mkdir()
    for name in files:
        dest=folder/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(paper/name,dest)
    archive=out/f'{PACKAGE_NAME}.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name in files:z.write(folder/name,f'{PACKAGE_NAME}/{name}')
    verify_submission_archive(archive,files)
    with (out/'standalone_compile.log').open('w') as log:
        subprocess.run(['latexmk','-pdf','-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=folder,stdout=log,stderr=subprocess.STDOUT,check=True)
    # Deliver the PDF compiled from exactly the files in this archive.
    shutil.copy2(folder/'main.pdf',out/'PlanSpace_ICLR2027.pdf')
    shutil.copy2(folder/'main.log',out/'standalone_final.log')
for path in (archive,out/'PlanSpace_ICLR2027.pdf'):
    (path.with_suffix(path.suffix+'.sha256')).write_text(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n')
print(out)
