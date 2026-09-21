import pytest

from scripts.verify_manuscript_v06 import FORBIDDEN, REQUIRED, verify


def _valid_text():
    return "\n".join(REQUIRED)


def test_v06_manuscript_gate_accepts_required_evidence():
    verify(_valid_text())


def test_v06_manuscript_gate_rejects_stale_and_overclaimed_text():
    with pytest.raises(AssertionError, match="stale v0.4"):
        verify(_valid_text() + "\n" + FORBIDDEN[2])
    with pytest.raises(AssertionError, match="unsupported validation"):
        verify(_valid_text() + "\nHuman-validated outcomes")
