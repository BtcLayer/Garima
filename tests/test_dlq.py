def test_dlq_append(tmp_path):
    dlq = tmp_path / "dlq.jsonl"

    with open(dlq, "a") as f:
        f.write('{"error": "failed"}\n')

    with open(dlq) as f:
        lines = f.readlines()

    assert len(lines) == 1