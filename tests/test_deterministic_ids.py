import hashlib

def generate_id(data: str):
    return hashlib.sha256(data.encode()).hexdigest()

def test_deterministic_id():
    a = generate_id("test")
    b = generate_id("test")

    assert a == b