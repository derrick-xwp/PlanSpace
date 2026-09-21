"""Package the paper and a reproducible, whitelisted local evidence bundle."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release/matched_reference_analysis_20260921"
PAPER = RELEASE / "PlanSpace_ICLR2027_LaTeX"
ANALYSIS = ROOT / "artifacts/matched_reference_analysis_20260921_verified"


def main():
    outputs = {}
    pdf = RELEASE / "PlanSpace_ICLR2027_matched_reference_analysis_20260921.pdf"
    shutil.copy2(PAPER / "build/main.pdf", pdf)
    outputs[pdf.name] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    tex_zip = RELEASE / "PlanSpace_ICLR2027_matched_reference_analysis_20260921_LaTeX.zip"
    with zipfile.ZipFile(tex_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(PAPER.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(PAPER)
            if any(part in {"build", "__pycache__", ".pytest_cache"} for part in rel.parts) or p.name == ".DS_Store":
                continue
            z.write(p, Path(PAPER.name) / rel)
    outputs[tex_zip.name] = hashlib.sha256(tex_zip.read_bytes()).hexdigest()

    manifest = json.loads((ANALYSIS / "manifest.json").read_text())
    files = {ROOT / p for p in manifest["inputs"]}
    files.update(ANALYSIS.glob("*.json"))
    for name in ("analyze_matched_references.py", "verify_matched_reference_analysis.py", "export_matched_reference_paper.py"):
        files.add(ROOT / "scripts" / name)
    for name in ("test_matched_references.py", "test_reviewer_revision_structures.py"):
        files.add(ROOT / "tests" / name)
    evidence_zip = RELEASE / "PlanSpace_matched_reference_evidence_20260921.zip"
    file_hashes = {}
    with zipfile.ZipFile(evidence_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files):
            assert p.is_file(), p
            rel = p.relative_to(ROOT)
            z.write(p, Path("PlanSpaceAnalysis") / rel)
            file_hashes[str(rel)] = hashlib.sha256(p.read_bytes()).hexdigest()
        z.write(RELEASE / "MATCHED_REFERENCE_ANALYSIS.md", "PlanSpaceAnalysis/MATCHED_REFERENCE_ANALYSIS.md")
        z.writestr("PlanSpaceAnalysis/PACKAGE_INPUTS.json", json.dumps(file_hashes, indent=2) + "\n")
    outputs[evidence_zip.name] = hashlib.sha256(evidence_zip.read_bytes()).hexdigest()
    (RELEASE / "DELIVERY_CHECKSUMS.json").write_text(json.dumps(outputs, indent=2) + "\n")
    print(json.dumps({name: (RELEASE / name).stat().st_size for name in outputs}, indent=2))


if __name__ == "__main__":
    main()
