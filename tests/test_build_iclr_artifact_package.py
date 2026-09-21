from scripts.build_iclr_artifact_package import (
    PACKAGE_NAME,
    ROOT,
    verify_zip,
    write_manifest,
    write_zip,
    ignored,
)


def test_release_ignores_build_products_but_keeps_final_pdf_and_sources():
    assert ignored(ROOT / "paper" / "main.aux")
    assert ignored(ROOT / "paper" / "main.log")
    assert ignored(ROOT / "paper" / "build" / "main.pdf")
    assert not ignored(ROOT / "paper" / "main.pdf")
    assert not ignored(ROOT / "paper" / "main.tex")
    assert not ignored(ROOT / "artifacts" / "multi_model_comparison_v0_6.json")


def test_artifact_zip_is_manifest_complete(tmp_path):
    package = tmp_path / PACKAGE_NAME
    package.mkdir()
    (package / "result.json").write_text('{"complete": true}\n', encoding="utf-8")
    write_manifest(package)
    archive = tmp_path / "artifact.zip"
    write_zip(package, archive)
    verify_zip(archive)
