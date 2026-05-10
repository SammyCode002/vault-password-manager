"""Tests for core.password_gen — random password & passphrase generation, strength estimation."""

import pytest

from core.password_gen import (
    DIGITS,
    LOWERCASE,
    SYMBOLS,
    UPPERCASE,
    WORDLIST,
    estimate_strength,
    generate_passphrase,
    generate_password,
)


class TestGeneratePassword:
    def test_default_length_is_16(self):
        assert len(generate_password()) == 16

    @pytest.mark.parametrize("length", [4, 8, 16, 32, 64])
    def test_respects_requested_length(self, length):
        assert len(generate_password(length=length)) == length

    def test_includes_every_selected_type_across_many_runs(self):
        for _ in range(200):
            pw = generate_password(length=8)
            assert any(c in LOWERCASE for c in pw)
            assert any(c in UPPERCASE for c in pw)
            assert any(c in DIGITS for c in pw)
            assert any(c in SYMBOLS for c in pw)

    def test_excluding_a_type_omits_it(self):
        for _ in range(50):
            pw = generate_password(length=20, use_symbols=False)
            assert not any(c in SYMBOLS for c in pw)

    def test_exclude_ambiguous_omits_lookalikes(self):
        ambiguous = set("Il1O0oS5Z2")
        for _ in range(50):
            pw = generate_password(length=32, exclude_ambiguous=True, use_symbols=False)
            assert not (set(pw) & ambiguous)

    def test_no_char_types_raises(self):
        with pytest.raises(ValueError):
            generate_password(
                use_lowercase=False,
                use_uppercase=False,
                use_digits=False,
                use_symbols=False,
            )

    def test_length_below_minimum_raises(self):
        # With all four types selected the minimum length is 4
        with pytest.raises(ValueError):
            generate_password(length=3)

    def test_outputs_are_unique_across_runs(self):
        passwords = {generate_password(length=20) for _ in range(50)}
        assert len(passwords) == 50, "two random 20-char passwords colliding is essentially impossible"


class TestGeneratePassphrase:
    def test_default_word_count_is_four(self):
        # default also appends "-NN" so 4 words + 1 number segment = 5 separator-joined parts
        parts = generate_passphrase().split("-")
        assert len(parts) == 5

    def test_custom_separator(self):
        pp = generate_passphrase(separator=".", include_number=False)
        assert "-" not in pp
        assert pp.count(".") == 3  # 4 words = 3 separators

    def test_capitalize_flag(self):
        pp = generate_passphrase(capitalize=True, include_number=False)
        for word in pp.split("-"):
            assert word[0].isupper()

    def test_words_come_from_wordlist(self):
        wordlist_lower = {w.lower() for w in WORDLIST}
        for _ in range(30):
            pp = generate_passphrase(capitalize=False, include_number=False, separator=" ")
            for word in pp.split(" "):
                assert word in wordlist_lower

    def test_number_appended_when_requested(self):
        for _ in range(20):
            pp = generate_passphrase(include_number=True)
            tail = pp.split("-")[-1]
            assert tail.isdigit()
            assert 10 <= int(tail) <= 99

    def test_too_few_words_raises(self):
        with pytest.raises(ValueError):
            generate_passphrase(word_count=2)


class TestEstimateStrength:
    def test_low_entropy_password_classified_low(self):
        # The estimator is pure entropy and intentionally does NOT detect
        # dictionary words (per its docstring), so we use a short input
        # that yields low bits regardless of pattern.
        result = estimate_strength("abc")
        assert result["strength"] == "Very Weak"

    def test_known_strong_password_classified_high(self):
        result = estimate_strength("kX9#mP2$vL4@nQrT8&hYwBz!")
        assert result["strength"] in {"Strong", "Very Strong"}

    def test_empty_password_has_zero_entropy(self):
        result = estimate_strength("")
        assert result["entropy_bits"] == 0

    def test_detects_each_character_class(self):
        result = estimate_strength("Aa1!")
        assert result["has_lowercase"] is True
        assert result["has_uppercase"] is True
        assert result["has_digits"] is True
        assert result["has_symbols"] is True

    def test_pool_size_matches_selected_classes(self):
        # all-lowercase only -> pool of 26
        assert estimate_strength("abcdef")["pool_size"] == 26
        # lower + digit -> 36
        assert estimate_strength("abc123")["pool_size"] == 36

    def test_longer_password_has_more_entropy(self):
        short = estimate_strength("Aa1!Aa1!")
        long = estimate_strength("Aa1!Aa1!Aa1!Aa1!")
        assert long["entropy_bits"] > short["entropy_bits"]
