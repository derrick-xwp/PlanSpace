import pytest

from scripts.analyze_metric_validity_audit import auroc, binary_report, kappa


def test_binary_report_and_auc_are_exact_on_separable_labels():
    report = binary_report([True, True, False, False], [True, True, False, False])
    assert report == {
        "n": 4,
        "tp": 2,
        "tn": 2,
        "fp": 0,
        "fn": 0,
        "accuracy": 1.0,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
    }
    assert auroc([0.9, 0.8, 0.2, 0.1], [True, True, False, False]) == 1.0


def test_kappa_accounts_for_chance_agreement():
    assert kappa(["yes", "yes", "no", "no"], ["yes", "yes", "no", "no"]) == 1.0
    assert kappa(["yes", "yes", "no", "no"], ["yes", "no", "yes", "no"]) == 0.0


def test_auc_ties_receive_half_credit():
    assert auroc([0.5, 0.5], [True, False]) == pytest.approx(0.5)
