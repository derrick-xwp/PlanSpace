#!/usr/bin/env python3
"""Build and independently verify the complete PlanSpace ICLR artifact bundle."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "PlanSpace_ICLR2027_Artifacts"
TOP_FILES = ("README.md", "pyproject.toml", "uv.lock")
TOP_DIRS = ("src", "scripts", "configs", "tests", "examples", "docs", "artifacts", "paper", "cluster")


def ignored_relative(relative: Path) -> bool:
    return (
        any(part in {"__pycache__", ".pytest_cache", "build"} for part in relative.parts)
        or relative.name == ".DS_Store"
        or relative.name.endswith(".synctex.gz")
        or relative.suffix
        in {
            ".aux",
            ".blg",
            ".fdb_latexmk",
            ".fls",
            ".log",
            ".out",
            ".pyc",
        }
    )


def ignored(path: Path) -> bool:
    return ignored_relative(path.relative_to(ROOT))


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def copy_release_tree(destination: Path) -> None:
    for name in TOP_FILES:
        source = ROOT / name
        if source.is_file():
            shutil.copy2(source, destination / name)
    for directory in TOP_DIRS:
        source_root = ROOT / directory
        for source in source_root.rglob("*"):
            if not source.is_file() or ignored(source):
                continue
            target = destination / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def write_manifest(package: Path) -> None:
    files = sorted(
        path for path in package.rglob("*") if path.is_file() and path.name != "MANIFEST.sha256"
    )
    lines = [f"{digest(path)}  {path.relative_to(package).as_posix()}" for path in files]
    (package / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    metadata = {
        "evidence_status": "complete_v06_matrix_v07_expansion_and_internal_ai_audits",
        "primary_config": "configs/model_matrix_v0_6_v04_uniform_compact.json",
        "expanded_config": "configs/model_matrix_v0_7_expanded_173_gpuhub.json",
        "human_validation_claimed": False,
        "simulator_or_real_robot_validation_claimed": False,
    }
    (package / "RELEASE_METADATA.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    # Include metadata in the final manifest after it is materialized.
    metadata_line = f"{digest(package / 'RELEASE_METADATA.json')}  RELEASE_METADATA.json\n"
    with (package / "MANIFEST.sha256").open("a", encoding="utf-8") as handle:
        handle.write(metadata_line)


def run_checks(package: Path) -> None:
    env = {**os.environ, "PYTHONPATH": os.pathsep.join((str(package), str(package / "src")))}
    commands = (
        [sys.executable, "scripts/verify_v06_release.py", "--require-paper-data"],
        [sys.executable, "scripts/verify_v07_expanded_release.py", "--require-paper-data"],
        [sys.executable, "scripts/verify_output_validity_audit.py"],
        [sys.executable, "scripts/verify_prompt_serialization_effect.py", "--require-paper-data"],
        [sys.executable, "scripts/verify_manuscript_v06.py"],
        [sys.executable, "scripts/verify_goal_completion_audit.py"],
        [sys.executable, "-m", "pytest", "-q"],
    )
    for command in commands:
        subprocess.run(command, cwd=package, env=env, check=True)


def write_zip(package: Path, output: Path) -> None:
    temporary = output.with_name(f".{output.name}.tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(package.rglob("*")):
            relative = path.relative_to(package)
            if path.is_file() and not ignored_relative(relative):
                archive.write(path, f"{PACKAGE_NAME}/{relative.as_posix()}")
    os.replace(temporary, output)


def verify_zip(output: Path) -> None:
    prefix = f"{PACKAGE_NAME}/"
    with zipfile.ZipFile(output, "r") as archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            raise RuntimeError(f"corrupt artifact archive member: {corrupt}")
        members = {name for name in archive.namelist() if not name.endswith("/")}
        manifest_name = prefix + "MANIFEST.sha256"
        if manifest_name not in members:
            raise RuntimeError("artifact archive has no checksum manifest")
        declared: dict[str, str] = {}
        for line in archive.read(manifest_name).decode("utf-8").splitlines():
            checksum, relative = line.split("  ", 1)
            if relative in declared:
                raise RuntimeError(f"duplicate manifest path: {relative}")
            declared[relative] = checksum
        payload = {name.removeprefix(prefix) for name in members if name != manifest_name}
        if payload != set(declared):
            missing = sorted(payload - set(declared))
            extra = sorted(set(declared) - payload)
            raise RuntimeError(f"manifest/archive mismatch: unlisted={missing}, missing={extra}")
        for relative, expected in declared.items():
            actual = hashlib.sha256(archive.read(prefix + relative)).hexdigest()
            if actual != expected:
                raise RuntimeError(f"artifact checksum mismatch: {relative}")


def main() -> None:
    output_dir = ROOT / "release"
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="planspace-artifact-release-") as temporary:
        package = Path(temporary) / PACKAGE_NAME
        package.mkdir()
        copy_release_tree(package)
        write_manifest(package)
        run_checks(package)
        output = output_dir / f"{PACKAGE_NAME}.zip"
        write_zip(package, output)
        verify_zip(output)
    sidecar = output.with_name(output.name + ".sha256")
    sidecar.write_text(f"{digest(output)}  {output.name}\n", encoding="utf-8")
    print(output)
    print(sidecar)


if __name__ == "__main__":
    main()
