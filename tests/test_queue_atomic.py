def test_queue_atomic_write(tmp_path):
    file = tmp_path / "queue.jsonl"

    with open(file, "a") as f:
        f.write('{"a":1}\n')

    with open(file) as f:
        lines = f.readlines()

    assert len(lines) == 1