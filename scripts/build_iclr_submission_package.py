#!/usr/bin/env python3
"""Build and independently compile-check the PlanSpace ICLR submission package."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
PACKAGE_NAME = "PlanSpace_ICLR2027_LaTeX"
PDF_NAME = "PlanSpace_ICLR2027.pdf"
COMMON_PACKAGE_FILES = (
    "README.md",
    "EDITORIAL_FINAL_CHECK.md",
    "Makefile",
    "main.tex",
    "real_dag_gallery.tex",
    "dag_style.tex",
    "dag_matching_cases.tex",
    "data/dag_matching_cases.json",
    "data/real_dag_manifest.json",
    "reviewer_results.tex",
    "reviewer_appendix.tex",
    "extended_examples.tex",
    "generated_cap_resources.tex",
    "data/cap_resources_manifest.json",
    "generated_reviewer_revision.tex",
    "figures/reviewer_family_decomposition.tex",
    "data/reviewer_family_decomposition.dat",
    "data/reviewer_revision_manifest.json",
    "math_commands.tex",
    "references.bib",
    "generated_confirmatory.tex",
    "generated_semantic_v05.tex",
    "generated_coverage_v05.tex",
    "generated_v05_uniform.tex",
    "generated_output_validity.tex",
    "generated_context_compatibility.tex",
    "generated_revision_audits.tex",
    "iclr2027_conference.sty",
    "iclr2027_conference.bst",
    "fancyhdr.sty",
    "natbib.sty",
    "figures/planspace_architecture.pdf",
    "figures/figure1_A_technical_pipeline.png",
    "figures/figure2_metric_separation.tex",
    "figures/figure3_structure_replication.tex",
    "figures/figure4_failure_interface.tex",
    "figures/simulation_terminal/front.png",
    "figures/simulation_terminal/camera_config_v3.json",
    "figures/simulation_terminal/manifest.sha256",
    "data/postoutcome_v04_compact.csv",
    "data/corrected_pilot_v05_compact.csv",
    "data/revision_audits_manifest.json",
    "figures/native_home_contact.tex",
    "figures/native_home_contact/A_initial.png",
    "figures/native_home_contact/A_lift.png",
    "figures/native_home_contact/A_final.png",
    "figures/native_home_contact/B_initial.png",
    "figures/native_home_contact/B_lift.png",
    "figures/native_home_contact/B_final.png",
    "data/native_home_contact_manifest.json",
)


def package_files(matrix_version: str) -> tuple[str, ...]:
    if matrix_version == "v0_2":
        return COMMON_PACKAGE_FILES + ("generated_v02.tex", "results_v02_tables.tex")
    if matrix_version == "v0_4":
        return COMMON_PACKAGE_FILES + (
            "generated_v04.tex",
            "results_v04_tables.tex",
            "results_v02_tables.tex",
        )
    if matrix_version == "v0_6":
        return COMMON_PACKAGE_FILES + (
            "generated_v06.tex",
            "generated_prompt_effect.tex",
            "generated_expanded_v07.tex",
            "results_v06_tables.tex",
            "results_v02_tables.tex",
        )
    if matrix_version == "v0_8":
        return COMMON_PACKAGE_FILES + (
            "generated_v08_expanded.tex",
            "generated_cross_run_v08.tex",
            "generated_prompt_effect.tex",
            "generated_expanded_v08.tex",
            "results_v06_tables.tex",
            "results_v02_tables.tex",
        )
    if matrix_version == "v0_9":
        return COMMON_PACKAGE_FILES + (
            "generated_v09_context.tex",
            "generated_cross_run_v09.tex",
            "generated_prompt_effect.tex",
            "generated_expanded_v09.tex",
            "results_v06_tables.tex",
            "results_v02_tables.tex",
        )
    raise ValueError(f"unsupported matrix version: {matrix_version}")


def paper_version_tag(matrix_version: str) -> str:
    """Map artifact tags (v0_4) to the established compact TeX filenames (v04)."""
    return matrix_version.replace("_", "")


def run(command: list[str], *, cwd: Path) -> None:
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join((str(ROOT), str(ROOT / "src"))),
    }
    subprocess.run(command, cwd=cwd, env=env, check=True)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write_sidecar(path: Path) -> Path:
    sidecar = path.with_name(path.name + ".sha256")
    temporary = sidecar.with_name("." + sidecar.name + ".tmp")
    temporary.write_text(f"{digest(path)}  {path.name}\n", encoding="utf-8")
    os.replace(temporary, sidecar)
    return sidecar


def verify_submission_archive(path: Path, expected_files: tuple[str, ...]) -> None:
    prefix = f"{PACKAGE_NAME}/"
    expected = {prefix + name for name in expected_files}
    with zipfile.ZipFile(path, "r") as archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            raise RuntimeError(f"corrupt LaTeX archive member: {corrupt}")
        actual = {name for name in archive.namelist() if not name.endswith("/")}
        if actual != expected:
            unexpected = sorted(actual - expected)
            missing = sorted(expected - actual)
            raise RuntimeError(
                f"LaTeX archive content mismatch: unexpected={unexpected}, missing={missing}"
            )


def validate_inputs(matrix_version: str) -> None:
    files = package_files(matrix_version)
    missing = [name for name in files if not (PAPER / name).is_file()]
    if missing:
        raise FileNotFoundError("missing paper package inputs: " + ", ".join(missing))
    manuscript = (PAPER / "main.tex").read_text(encoding="utf-8")
    tag = paper_version_tag(matrix_version)
    generated = f"generated_{tag}.tex"
    tables = f"results_{tag}_tables.tex"
    if matrix_version in {"v0_8", "v0_9"}:
        generated = (
            "generated_v08_expanded.tex"
            if matrix_version == "v0_8"
            else "generated_v09_context.tex"
        )
        # The table body is version-agnostic and consumes the VTwo* macros
        # materialized by generated_v08_expanded.tex.
        tables = "results_v06_tables.tex"
    if rf"\input{{{generated}}}" not in manuscript:
        raise ValueError(f"main.tex does not consume {generated}")
    if r"\input{generated_semantic_v05.tex}" not in manuscript:
        raise ValueError("main.tex does not consume generated_semantic_v05.tex")
    if r"\input{generated_coverage_v05.tex}" not in manuscript:
        raise ValueError("main.tex does not consume generated_coverage_v05.tex")
    if r"\input{generated_output_validity.tex}" not in manuscript:
        raise ValueError("main.tex does not consume generated_output_validity.tex")
    if r"\input{generated_revision_audits.tex}" not in manuscript:
        raise ValueError("main.tex does not consume generated_revision_audits.tex")
    if matrix_version in {"v0_6", "v0_8", "v0_9"}:
        if r"\input{generated_prompt_effect.tex}" not in manuscript:
            raise ValueError("main.tex does not consume generated_prompt_effect.tex")
    if matrix_version == "v0_6":
        if r"\input{generated_expanded_v07.tex}" not in manuscript:
            raise ValueError("main.tex does not consume generated_expanded_v07.tex")
    elif matrix_version == "v0_8":
        if r"\input{generated_expanded_v08.tex}" not in manuscript:
            raise ValueError("main.tex does not consume generated_expanded_v08.tex")
        if r"\input{generated_cross_run_v08.tex}" not in manuscript:
            raise ValueError("main.tex does not consume generated_cross_run_v08.tex")
    elif matrix_version == "v0_9":
        if r"\input{generated_expanded_v09.tex}" not in manuscript:
            raise ValueError("main.tex does not consume generated_expanded_v09.tex")
        if r"\input{generated_cross_run_v09.tex}" not in manuscript:
            raise ValueError("main.tex does not consume generated_cross_run_v09.tex")
    if rf"\input{{{tables}}}" not in manuscript:
        raise ValueError(f"main.tex does not consume {tables}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "release")
    parser.add_argument(
        "--matrix-version",
        choices=("v0_2", "v0_4", "v0_6", "v0_8", "v0_9"),
        default="v0_2",
    )
    args = parser.parse_args()

    files = package_files(args.matrix_version)
    validate_inputs(args.matrix_version)
    python = sys.executable
    run([python, "-m", "pytest", "-q", "tests"], cwd=ROOT)
    # Materialize the human-review macros before verifying that the manuscript
    # consumes complete review evidence. This prevents a stale pending-status
    # file from entering an otherwise complete release.
    run(["make", "data", f"PYTHON={python}"], cwd=PAPER)
    verifier = "scripts/verify_v02_release.py"
    verifier_args = ["--require-paper-data", "--require-human-review"]
    if args.matrix_version == "v0_4":
        verifier = "scripts/verify_v04_release.py"
        verifier_args = ["--require-paper-data"]
    elif args.matrix_version == "v0_6":
        verifier = "scripts/verify_v06_release.py"
        verifier_args = ["--require-paper-data"]
    elif args.matrix_version == "v0_8":
        verifier = "scripts/verify_v08_expanded_release.py"
        verifier_args = ["--require-paper-data"]
    elif args.matrix_version == "v0_9":
        verifier = "scripts/verify_v09_context_release.py"
        verifier_args = ["--require-paper-data"]
    run([python, verifier, *verifier_args], cwd=ROOT)
    run([python, "scripts/verify_output_validity_audit.py"], cwd=ROOT)
    run([python, "scripts/verify_revision_audits.py"], cwd=ROOT)
    if args.matrix_version in {"v0_6", "v0_8", "v0_9"}:
        run([python, "scripts/verify_prompt_serialization_effect.py", "--require-paper-data"], cwd=ROOT)
    if args.matrix_version == "v0_6":
        run([python, "scripts/verify_v07_expanded_release.py", "--require-paper-data"], cwd=ROOT)
        run([python, "scripts/verify_manuscript_v06.py"], cwd=ROOT)
    elif args.matrix_version == "v0_8":
        # Preserve the historical expansion as an independently verified
        # artifact, but require the manuscript itself to consume the v0.8
        # same-run structural macros.
        run([python, "scripts/verify_v07_expanded_release.py"], cwd=ROOT)
        run([python, "scripts/verify_manuscript_v08.py"], cwd=ROOT)
    elif args.matrix_version == "v0_9":
        run([python, "scripts/verify_v07_expanded_release.py"], cwd=ROOT)
        run([python, "scripts/verify_manuscript_v09.py"], cwd=ROOT)
    run(["make", "pdf", f"PYTHON={python}"], cwd=PAPER)
    built_pdf = PAPER / "build" / "main.pdf"
    if not built_pdf.is_file():
        raise FileNotFoundError(built_pdf)

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="planspace-release-") as temporary_root:
        temporary_root_path = Path(temporary_root)
        package_dir = temporary_root_path / PACKAGE_NAME
        package_dir.mkdir()
        for name in files:
            destination = package_dir / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PAPER / name, destination)

        compile_check = temporary_root_path / "compile-check"
        shutil.copytree(package_dir, compile_check)
        run(
            ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
            cwd=compile_check,
        )
        if not (compile_check / "main.pdf").is_file():
            raise RuntimeError("standalone LaTeX package did not produce main.pdf")

        archive_base = temporary_root_path / PACKAGE_NAME
        archive = Path(shutil.make_archive(str(archive_base), "zip", temporary_root_path, PACKAGE_NAME))
        temporary_archive = output_dir / f".{PACKAGE_NAME}.zip.tmp"
        shutil.copy2(archive, temporary_archive)
        final_archive = output_dir / f"{PACKAGE_NAME}.zip"
        os.replace(temporary_archive, final_archive)
        verify_submission_archive(final_archive, files)

        temporary_pdf = output_dir / f".{PDF_NAME}.tmp"
        shutil.copy2(built_pdf, temporary_pdf)
        final_pdf = output_dir / PDF_NAME
        os.replace(temporary_pdf, final_pdf)

    archive_sidecar = write_sidecar(final_archive)
    pdf_sidecar = write_sidecar(final_pdf)
    print(final_archive)
    print(archive_sidecar)
    print(final_pdf)
    print(pdf_sidecar)


if __name__ == "__main__":
    main()
