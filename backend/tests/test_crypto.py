from app.crypto import decrypt_dict, encrypt_dict


def test_encrypt_decrypt_round_trip():
    original = {"api_key": "sk-super-secret", "nested": {"a": 1}}
    token = encrypt_dict(original)
    assert isinstance(token, bytes)
    assert decrypt_dict(token) == original


def test_encrypt_produces_different_ciphertext_each_time():
    data = {"same": "value"}
    a = encrypt_dict(data)
    b = encrypt_dict(data)
    # Fernet includes a random IV/timestamp, so two encryptions of the same
    # plaintext should not be byte-identical, even though both decrypt fine.
    assert a != b
    assert decrypt_dict(a) == decrypt_dict(b) == data
