import json

from scripts.run_local_model_queue import write_checkpoint


def test_checkpoint_writes_complete_json_and_removes_temporary_files(tmp_path):
    output = tmp_path / "checkpoint.json"
    table = tmp_path / "checkpoint.md"
    write_checkpoint(output, table, {"protocol_version": "test"}, [])
    assert json.loads(output.read_text(encoding="utf-8"))["tasks"] == []
    assert table.read_text(encoding="utf-8").startswith("# Frozen 0-task")
    assert not list(tmp_path.glob(".*.tmp"))
