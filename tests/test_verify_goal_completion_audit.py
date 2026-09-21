import pytest

from scripts.verify_goal_completion_audit import REQUIRED_EVIDENCE, verify


def _complete_text():
    return "The goal is complete.\n" + "\n".join(REQUIRED_EVIDENCE)


def test_completion_audit_requires_final_state_and_evidence_index():
    verify(_complete_text())


def test_completion_audit_rejects_pending_state():
    with pytest.raises(AssertionError, match="incomplete work"):
        verify(_complete_text() + "\n**Pending final experiment.**")
