"""Tests for core.encryption — KDF, dual derivation, AEAD round-trip, verification."""

import pytest
from cryptography.fernet import InvalidToken

from core.encryption import (
    SALT_LENGTH,
    PBKDF2_ITERATIONS,
    decrypt,
    derive_key,
    derive_keys,
    encrypt,
    generate_salt,
    hash_master_password,
    verify_master_password,
    verify_token_constant_time,
)


PASSWORD = "MyS3cur3M@sterP@ss!"
WRONG = "wrong_password"
PLAINTEXT = "github_password:hunter2_but_actually_secure"


class TestSalt:
    def test_length_matches_constant(self):
        assert len(generate_salt()) == SALT_LENGTH

    def test_each_call_returns_new_random_bytes(self):
        salts = {generate_salt() for _ in range(50)}
        assert len(salts) == 50, "salts must be unique with overwhelming probability"


class TestDeriveKey:
    def test_iterations_constant_meets_owasp_minimum(self):
        # README claims 600k as the OWASP 2023 floor for PBKDF2-SHA256
        assert PBKDF2_ITERATIONS >= 600_000

    def test_derivation_is_deterministic(self):
        salt = generate_salt()
        assert derive_key(PASSWORD, salt) == derive_key(PASSWORD, salt)

    def test_different_password_gives_different_key(self):
        salt = generate_salt()
        assert derive_key(PASSWORD, salt) != derive_key(WRONG, salt)

    def test_different_salt_gives_different_key(self):
        assert derive_key(PASSWORD, generate_salt()) != derive_key(PASSWORD, generate_salt())


class TestEncryptDecrypt:
    def test_round_trip(self):
        salt = generate_salt()
        key = derive_key(PASSWORD, salt)
        token = encrypt(PLAINTEXT, key)
        assert decrypt(token, key) == PLAINTEXT

    def test_token_does_not_contain_plaintext(self):
        salt = generate_salt()
        key = derive_key(PASSWORD, salt)
        token = encrypt(PLAINTEXT, key)
        assert PLAINTEXT.encode("utf-8") not in token

    def test_two_encryptions_differ_due_to_random_iv(self):
        salt = generate_salt()
        key = derive_key(PASSWORD, salt)
        assert encrypt(PLAINTEXT, key) != encrypt(PLAINTEXT, key)

    def test_wrong_key_raises_invalid_token(self):
        salt = generate_salt()
        right = derive_key(PASSWORD, salt)
        wrong = derive_key(WRONG, salt)
        token = encrypt(PLAINTEXT, right)
        with pytest.raises(InvalidToken):
            decrypt(token, wrong)

    def test_tampered_ciphertext_raises_invalid_token(self):
        salt = generate_salt()
        key = derive_key(PASSWORD, salt)
        token = bytearray(encrypt(PLAINTEXT, key))
        token[-1] ^= 0x01
        with pytest.raises(InvalidToken):
            decrypt(bytes(token), key)


class TestLegacyHash:
    """The pre-v2 SHA-512 verification path. Kept for migration of older vaults."""

    def test_hash_matches_for_correct_password(self):
        salt = generate_salt()
        h = hash_master_password(PASSWORD, salt)
        assert verify_master_password(PASSWORD, salt, h) is True

    def test_hash_rejects_wrong_password(self):
        salt = generate_salt()
        h = hash_master_password(PASSWORD, salt)
        assert verify_master_password(WRONG, salt, h) is False

    def test_hash_is_hex_and_128_chars_for_sha512(self):
        salt = generate_salt()
        h = hash_master_password(PASSWORD, salt)
        assert len(h) == 128
        int(h, 16)  # raises if not hex


class TestDeriveKeys:
    """The v2 dual-output path: one PBKDF2 pass, HKDF-expanded into two keys."""

    def test_returns_two_distinct_outputs(self):
        salt = generate_salt()
        fernet_key, verify_token = derive_keys(PASSWORD, salt)
        assert fernet_key != verify_token

    def test_is_deterministic(self):
        salt = generate_salt()
        a = derive_keys(PASSWORD, salt)
        b = derive_keys(PASSWORD, salt)
        assert a == b

    def test_wrong_password_changes_both_outputs(self):
        salt = generate_salt()
        right_fk, right_vt = derive_keys(PASSWORD, salt)
        wrong_fk, wrong_vt = derive_keys(WRONG, salt)
        assert right_fk != wrong_fk
        assert right_vt != wrong_vt

    def test_fernet_key_is_usable_for_round_trip(self):
        salt = generate_salt()
        fernet_key, _ = derive_keys(PASSWORD, salt)
        token = encrypt(PLAINTEXT, fernet_key)
        assert decrypt(token, fernet_key) == PLAINTEXT

    def test_verification_token_is_32_bytes(self):
        salt = generate_salt()
        _, verify_token = derive_keys(PASSWORD, salt)
        assert len(verify_token) == 32

    def test_verify_token_is_independent_from_encryption_path(self):
        """The verification token must NOT equal anything used to encrypt."""
        salt = generate_salt()
        fernet_key, verify_token = derive_keys(PASSWORD, salt)
        # Decoded base64 of fernet_key must not equal verify_token
        import base64
        raw_enc_key = base64.urlsafe_b64decode(fernet_key)
        assert raw_enc_key != verify_token


class TestVerifyTokenConstantTime:
    def test_accepts_matching_token(self):
        salt = generate_salt()
        _, vt = derive_keys(PASSWORD, salt)
        assert verify_token_constant_time(vt, vt.hex()) is True

    def test_rejects_mismatched_token(self):
        salt = generate_salt()
        _, vt_right = derive_keys(PASSWORD, salt)
        _, vt_wrong = derive_keys(WRONG, salt)
        assert verify_token_constant_time(vt_wrong, vt_right.hex()) is False

    def test_rejects_garbage_hex_string(self):
        salt = generate_salt()
        _, vt = derive_keys(PASSWORD, salt)
        assert verify_token_constant_time(vt, "this-is-not-hex") is False

    def test_rejects_empty_string(self):
        salt = generate_salt()
        _, vt = derive_keys(PASSWORD, salt)
        assert verify_token_constant_time(vt, "") is False
