import pytest

from scripts.verify_manuscript_v08 import FORBIDDEN, REQUIRED, verify


def valid_text() -> str:
    return "\n".join(REQUIRED)


def test_accepts_required_v08_claims() -> None:
    verify(valid_text())


def test_rejects_missing_required_claim() -> None:
    text = valid_text().replace(REQUIRED[0], "")
    try:
        verify(text)
    except AssertionError as error:
        assert "missing required v0.8" in str(error)
    else:
        raise AssertionError("expected missing v0.8 evidence to fail")


@pytest.mark.parametrize("forbidden", FORBIDDEN)
def test_rejects_every_stale_primary_claim(forbidden: str) -> None:
    try:
        verify(valid_text() + "\n" + forbidden)
    except AssertionError as error:
        assert "stale primary-matrix" in str(error)
    else:
        raise AssertionError("expected stale primary matrix to fail")


def test_rejects_external_preregistration_overclaim() -> None:
    try:
        verify(valid_text() + "\nExternally preregistered confirmation.")
    except AssertionError as error:
        assert "unsupported validation claim" in str(error)
    else:
        raise AssertionError("expected external preregistration overclaim to fail")
