def test_idempotent_event():
    processed_ids = set()

    event_id = "abc123"
    processed_ids.add(event_id)

    assert event_id in processed_ids