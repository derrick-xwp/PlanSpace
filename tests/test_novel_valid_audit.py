import json

from scripts.build_novel_valid_audit import build_packet


def write_report(path, model_id, samples):
    path.write_text(
        json.dumps(
            {
                "model_id": model_id,
                "model_revision": "rev",
                "tasks": [
                    {
                        "source_path": "task/problem0.bddl",
                        "source_sha256": "abc",
                        "reference_plan": ["a"],
                        "reference_plan_dags": [{"goals": [["g"]]}],
                        "samples": samples,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_build_packet_keeps_only_valid_outside_family_and_deduplicates(tmp_path):
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    novel = {
        "sample_index": 0,
        "seed": 1,
        "parsed_plan": ["a", "b"],
        "execution": {"valid": True},
        "partial_order_match": False,
    }
    write_report(
        first,
        "model-a",
        [novel, {**novel, "sample_index": 1, "partial_order_match": True}],
    )
    write_report(second, "model-b", [{**novel, "seed": 2}])
    packet = build_packet([first, second])
    assert packet["total_occurrence_count"] == 2
    assert packet["unique_case_count"] == 1
    assert len(packet["cases"][0]["occurrences"]) == 2
    assert packet["cases"][0]["review"]["classification"] is None
