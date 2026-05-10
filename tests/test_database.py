"""Tests for core.database — vault lifecycle, CRUD, master password change, v1->v2 migration."""

import sqlite3
from datetime import datetime, timezone

import pytest

from core.database import CURRENT_SCHEMA_VERSION, VaultDatabase
from core.encryption import generate_salt, hash_master_password


PASSWORD = "TestM@ster123!"
NEW_PASSWORD = "NewM@ster456!"


class TestVaultLifecycle:
    def test_initialize_creates_vault(self, vault_path):
        import os
        db = VaultDatabase(vault_path)
        db.initialize_vault(PASSWORD)
        assert db.encryption_key is not None
        assert os.path.exists(vault_path)
        db.lock()

    def test_vault_exists_false_when_no_file(self, tmp_path):
        db = VaultDatabase(str(tmp_path / "nope.db"))
        assert db.vault_exists() is False

    def test_vault_exists_true_for_initialized_vault(self, vault, vault_path):
        # vault fixture has already initialized vault_path
        vault.lock()
        probe = VaultDatabase(vault_path)
        try:
            assert probe.vault_exists() is True
        finally:
            probe.lock()

    def test_double_initialize_is_rejected(self, vault):
        with pytest.raises(ValueError):
            vault.initialize_vault(PASSWORD)

    def test_unlock_with_correct_password(self, vault, vault_path):
        vault.lock()
        db2 = VaultDatabase(vault_path)
        assert db2.unlock(PASSWORD) is True
        db2.lock()

    def test_unlock_with_wrong_password_returns_false(self, vault, vault_path):
        vault.lock()
        db2 = VaultDatabase(vault_path)
        assert db2.unlock("wrong_password") is False
        db2.lock()

    def test_lock_clears_key_in_memory(self, vault):
        vault.lock()
        assert vault.encryption_key is None

    def test_operations_fail_when_locked(self, vault):
        vault.lock()
        with pytest.raises(PermissionError):
            vault.add_entry("X", "u", "p")


class TestEntryCRUD:
    def test_add_and_retrieve(self, vault):
        eid = vault.add_entry("GitHub", "sammy", "secret", url="https://github.com")
        entry = vault.get_entry(eid)
        assert entry["site_name"] == "GitHub"
        assert entry["username"] == "sammy"
        assert entry["password"] == "secret"
        assert entry["url"] == "https://github.com"

    def test_get_missing_returns_none(self, vault):
        assert vault.get_entry(999_999) is None

    def test_get_all_returns_all_entries(self, vault):
        vault.add_entry("A", "u1", "p1")
        vault.add_entry("B", "u2", "p2")
        vault.add_entry("C", "u3", "p3")
        assert vault.get_entry_count() == 3
        assert {e["site_name"] for e in vault.get_all_entries()} == {"A", "B", "C"}

    def test_update_only_changes_provided_fields(self, vault):
        eid = vault.add_entry("GitHub", "sammy", "old", notes="keep")
        vault.update_entry(eid, password="new")
        entry = vault.get_entry(eid)
        assert entry["password"] == "new"
        assert entry["username"] == "sammy"
        assert entry["notes"] == "keep"

    def test_update_with_no_fields_returns_false(self, vault):
        eid = vault.add_entry("X", "u", "p")
        assert vault.update_entry(eid) is False

    def test_delete_entry(self, vault):
        eid = vault.add_entry("Trash", "u", "p")
        assert vault.delete_entry(eid) is True
        assert vault.get_entry(eid) is None

    def test_delete_missing_returns_false(self, vault):
        assert vault.delete_entry(999_999) is False

    def test_search_is_case_insensitive(self, vault):
        vault.add_entry("GitHub", "u", "p")
        vault.add_entry("Gitlab", "u", "p")
        vault.add_entry("Other", "u", "p")
        results = vault.search_entries("git")
        assert {e["site_name"] for e in results} == {"GitHub", "Gitlab"}


class TestEncryptionAtRest:
    def test_password_is_not_plaintext_in_db(self, vault, vault_path):
        secret = "totally_unique_marker_string_xyz123"
        vault.add_entry("X", "u", secret)
        # Read raw bytes from the SQLite file - encrypted token must not contain the secret
        with open(vault_path, "rb") as f:
            raw = f.read()
        assert secret.encode("utf-8") not in raw


class TestMasterPasswordChange:
    def test_change_with_wrong_old_password_returns_false(self, vault):
        assert vault.change_master_password("wrong", NEW_PASSWORD) is False

    def test_change_re_encrypts_and_unlocks_with_new_password(self, vault, vault_path):
        vault.add_entry("GitHub", "sammy", "gh_secret")
        vault.add_entry("Gmail", "sammy@x.com", "gm_secret", notes="personal")

        assert vault.change_master_password(PASSWORD, NEW_PASSWORD) is True
        vault.lock()

        # Old password no longer works
        db_old = VaultDatabase(vault_path)
        assert db_old.unlock(PASSWORD) is False
        db_old.lock()

        # New password works and entries are intact
        db_new = VaultDatabase(vault_path)
        assert db_new.unlock(NEW_PASSWORD) is True
        entries = {e["site_name"]: e for e in db_new.get_all_entries()}
        assert entries["GitHub"]["password"] == "gh_secret"
        assert entries["Gmail"]["notes"] == "personal"
        db_new.lock()


class TestCSVRoundTrip:
    def test_export_and_import_round_trip(self, vault, tmp_path):
        vault.add_entry("GitHub", "sammy", "gh_secret", url="https://gh", notes="n1")
        vault.add_entry("Gmail", "sammy@x.com", "gm_secret", category="Social")
        csv_path = str(tmp_path / "out.csv")

        exported = vault.export_to_csv(csv_path)
        assert exported == 2

        # Wipe and re-import into a fresh vault
        fresh = VaultDatabase(str(tmp_path / "fresh.db"))
        fresh.initialize_vault("Fresh@Master1")
        imported, skipped = fresh.import_from_csv(csv_path)
        assert imported == 2
        assert skipped == 0

        names = {e["site_name"] for e in fresh.get_all_entries()}
        assert names == {"GitHub", "Gmail"}
        fresh.lock()

    def test_import_skips_rows_missing_required_fields(self, vault, tmp_path):
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text(
            "site_name,username,password\n"
            "Real,u,p\n"
            ",missing_site,p\n"
            "OnlySite,,\n",
            encoding="utf-8",
        )
        imported, skipped = vault.import_from_csv(str(csv_path))
        assert imported == 1
        assert skipped == 2


class TestSchemaMigration:
    """The v1 SHA-512 verification hash must transparently upgrade to v2 on unlock."""

    def _build_v1_vault(self, path: str, password: str) -> str:
        """Hand-build a v1-format vault.db using the legacy SHA-512 hash. Returns the legacy hash."""
        conn = sqlite3.connect(path)
        conn.execute(
            """
            CREATE TABLE master_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                salt BLOB NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_name TEXT NOT NULL,
                url TEXT,
                username_encrypted BLOB NOT NULL,
                password_encrypted BLOB NOT NULL,
                notes_encrypted BLOB,
                category TEXT DEFAULT 'General',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        salt = generate_salt()
        legacy_hash = hash_master_password(password, salt)
        conn.execute(
            "INSERT INTO master_config (id, salt, password_hash, created_at, version) VALUES (1, ?, ?, ?, 1)",
            (salt, legacy_hash, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()
        return legacy_hash

    def test_v1_vault_unlocks_with_correct_password(self, tmp_path):
        path = str(tmp_path / "legacy.db")
        legacy_pw = "Legacy@Vault123"
        self._build_v1_vault(path, legacy_pw)

        db = VaultDatabase(path)
        assert db.unlock(legacy_pw) is True
        db.lock()

    def test_v1_vault_rejects_wrong_password(self, tmp_path):
        path = str(tmp_path / "legacy.db")
        self._build_v1_vault(path, "Legacy@Vault123")

        db = VaultDatabase(path)
        assert db.unlock("wrong") is False
        db.lock()

    def test_v1_unlock_migrates_hash_and_bumps_version(self, tmp_path):
        path = str(tmp_path / "legacy.db")
        legacy_pw = "Legacy@Vault123"
        legacy_hash = self._build_v1_vault(path, legacy_pw)

        db = VaultDatabase(path)
        assert db.unlock(legacy_pw) is True

        cur = db.conn.cursor()
        cur.execute("SELECT password_hash, version FROM master_config WHERE id = 1")
        row = cur.fetchone()
        assert row["version"] == CURRENT_SCHEMA_VERSION
        assert row["password_hash"] != legacy_hash
        db.lock()

    def test_migrated_vault_unlocks_on_v2_path(self, tmp_path):
        path = str(tmp_path / "legacy.db")
        legacy_pw = "Legacy@Vault123"
        self._build_v1_vault(path, legacy_pw)

        # First unlock triggers migration
        first = VaultDatabase(path)
        first.unlock(legacy_pw)
        first.lock()

        # Subsequent unlock must succeed via the v2 path - no legacy hash left
        db2 = VaultDatabase(path)
        assert db2.unlock(legacy_pw) is True
        db2.lock()
