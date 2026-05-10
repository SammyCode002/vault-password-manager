"""Shared fixtures for the vault test suite."""

import pytest

from core.database import VaultDatabase


@pytest.fixture
def vault_path(tmp_path):
    """Return a fresh per-test SQLite path; pytest cleans tmp_path automatically."""
    return str(tmp_path / "test_vault.db")


@pytest.fixture
def vault(vault_path):
    """An initialized, unlocked vault. Always locked (and connection closed) on teardown."""
    db = VaultDatabase(vault_path)
    db.initialize_vault("TestM@ster123!")
    yield db
    db.lock()
