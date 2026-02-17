"""
database.py - SQLite vault storage for the password manager.

How this works:
1. On first run, we create a SQLite database with two tables:
   - master_config: Stores the salt and verification hash (NOT the password)
   - entries: Stores encrypted credentials (site, username, password, notes)
2. All sensitive fields are encrypted BEFORE they hit the database
3. The database file itself is just a regular SQLite file, but every
   password and note inside it is Fernet-encrypted gibberish without the key

Why SQLite?
- Zero setup (no server needed, it's just a file)
- Built into Python's standard library
- Easy to back up (copy one file)
- Perfect for local-first storage with optional cloud sync later
"""

import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from core.encryption import (
    generate_salt,
    derive_key,
    encrypt,
    decrypt,
    hash_master_password,
    verify_master_password,
)


# Default vault location — sits right next to the app
DEFAULT_VAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vault.db")


class VaultDatabase:
    """
    Manages all database operations for the password vault.
    
    Usage flow:
        1. Create instance: db = VaultDatabase()
        2. First time: db.initialize_vault(master_password)
        3. Returning user: db.unlock(master_password)
        4. Then: db.add_entry(...), db.get_all_entries(), etc.
        5. When done: db.lock()
    """

    def __init__(self, db_path: str = DEFAULT_VAULT_PATH):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.encryption_key: Optional[bytes] = None
        self._salt: Optional[bytes] = None

    # ------------------------------------------------------------------
    # Setup & Connection
    # ------------------------------------------------------------------

    def _connect(self):
        """Open a connection to the SQLite database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self._create_tables()

    def _create_tables(self):
        """Create the vault tables if they don't exist yet."""
        cursor = self.conn.cursor()

        # Master config table — stores salt and password verification hash
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS master_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                salt BLOB NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Entries table — the actual password vault
        # All sensitive fields (username, password, notes) are stored encrypted
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
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
        """)

        self.conn.commit()

    def vault_exists(self) -> bool:
        """Check if the vault database file already exists with a master password set."""
        if not os.path.exists(self.db_path):
            return False
        self._connect()
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM master_config")
        count = cursor.fetchone()[0]
        return count > 0

    # ------------------------------------------------------------------
    # Vault Initialization & Unlocking
    # ------------------------------------------------------------------

    def initialize_vault(self, master_password: str):
        """
        First-time setup: create the vault with a master password.
        
        This generates a salt, creates the verification hash, and
        derives the encryption key. After this, the vault is unlocked
        and ready to store entries.
        
        Args:
            master_password: The master password chosen by the user
            
        Raises:
            ValueError: If the vault is already initialized
        """
        self._connect()

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM master_config")
        if cursor.fetchone()[0] > 0:
            raise ValueError("Vault is already initialized. Use unlock() instead.")

        # Generate salt and derive everything from the master password
        self._salt = generate_salt()
        self.encryption_key = derive_key(master_password, self._salt)
        pw_hash = hash_master_password(master_password, self._salt)

        # Store the salt and hash (never the password itself)
        cursor.execute(
            "INSERT INTO master_config (id, salt, password_hash, created_at) VALUES (1, ?, ?, ?)",
            (self._salt, pw_hash, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def unlock(self, master_password: str) -> bool:
        """
        Unlock an existing vault with the master password.
        
        Loads the salt, verifies the password against the stored hash,
        and if correct, derives the encryption key for this session.
        
        Args:
            master_password: The master password to try
            
        Returns:
            True if the password is correct and vault is unlocked,
            False if the password is wrong
        """
        self._connect()

        cursor = self.conn.cursor()
        cursor.execute("SELECT salt, password_hash FROM master_config WHERE id = 1")
        row = cursor.fetchone()

        if row is None:
            raise ValueError("Vault is not initialized. Use initialize_vault() first.")

        self._salt = row["salt"]
        stored_hash = row["password_hash"]

        # Verify the password
        if not verify_master_password(master_password, self._salt, stored_hash):
            return False

        # Password is correct — derive the encryption key
        self.encryption_key = derive_key(master_password, self._salt)
        return True

    def lock(self):
        """
        Lock the vault: wipe the encryption key from memory and close the DB.
        
        This is important — when the user "locks" the app, we don't want
        the key sitting in memory any longer than necessary.
        """
        self.encryption_key = None
        self._salt = None
        if self.conn:
            self.conn.close()
            self.conn = None

    def _require_unlocked(self):
        """Helper to make sure the vault is unlocked before any operation."""
        if self.encryption_key is None:
            raise PermissionError("Vault is locked. Call unlock() or initialize_vault() first.")

    # ------------------------------------------------------------------
    # CRUD Operations (Create, Read, Update, Delete)
    # ------------------------------------------------------------------

    def add_entry(
        self,
        site_name: str,
        username: str,
        password: str,
        url: str = "",
        notes: str = "",
        category: str = "General",
    ) -> int:
        """
        Add a new credential entry to the vault.
        
        The username, password, and notes are encrypted before storage.
        The site_name, url, and category are stored in plaintext so we
        can search/filter without decrypting everything.
        
        Args:
            site_name: Name of the service (e.g., "GitHub")
            username: Login username/email
            password: The password to store
            url: Optional URL for the service
            notes: Optional notes
            category: Category for organization (default: "General")
            
        Returns:
            The ID of the newly created entry
        """
        self._require_unlocked()

        now = datetime.now(timezone.utc).isoformat()

        # Encrypt the sensitive fields
        username_enc = encrypt(username, self.encryption_key)
        password_enc = encrypt(password, self.encryption_key)
        notes_enc = encrypt(notes, self.encryption_key) if notes else None

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO entries 
                (site_name, url, username_encrypted, password_encrypted, 
                 notes_encrypted, category, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (site_name, url, username_enc, password_enc, notes_enc, category, now, now),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all_entries(self) -> list[dict]:
        """
        Retrieve and decrypt all entries from the vault.
        
        Returns:
            List of dicts with decrypted entry data
        """
        self._require_unlocked()

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM entries ORDER BY site_name COLLATE NOCASE"
        )
        rows = cursor.fetchall()
        return [self._decrypt_row(row) for row in rows]

    def get_entry(self, entry_id: int) -> Optional[dict]:
        """
        Retrieve and decrypt a single entry by ID.
        
        Args:
            entry_id: The database ID of the entry
            
        Returns:
            Dict with decrypted entry data, or None if not found
        """
        self._require_unlocked()

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        return self._decrypt_row(row) if row else None

    def update_entry(
        self,
        entry_id: int,
        site_name: str = None,
        username: str = None,
        password: str = None,
        url: str = None,
        notes: str = None,
        category: str = None,
    ) -> bool:
        """
        Update an existing entry. Only provided fields are updated.
        
        Args:
            entry_id: The database ID of the entry to update
            **fields: Only the fields you want to change
            
        Returns:
            True if the entry was found and updated, False otherwise
        """
        self._require_unlocked()

        # Build the update dynamically based on what was provided
        updates = []
        params = []

        if site_name is not None:
            updates.append("site_name = ?")
            params.append(site_name)
        if url is not None:
            updates.append("url = ?")
            params.append(url)
        if username is not None:
            updates.append("username_encrypted = ?")
            params.append(encrypt(username, self.encryption_key))
        if password is not None:
            updates.append("password_encrypted = ?")
            params.append(encrypt(password, self.encryption_key))
        if notes is not None:
            updates.append("notes_encrypted = ?")
            params.append(encrypt(notes, self.encryption_key))
        if category is not None:
            updates.append("category = ?")
            params.append(category)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(entry_id)

        cursor = self.conn.cursor()
        cursor.execute(
            f"UPDATE entries SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_entry(self, entry_id: int) -> bool:
        """
        Delete an entry from the vault.
        
        Args:
            entry_id: The database ID of the entry to delete
            
        Returns:
            True if the entry was found and deleted, False otherwise
        """
        self._require_unlocked()

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def search_entries(self, query: str) -> list[dict]:
        """
        Search entries by site name (case-insensitive).
        
        Since site_name is stored in plaintext, we can search without
        decrypting every entry. This is a deliberate tradeoff: site names
        aren't secret (an attacker who gets your vault file already knows
        you probably have a GitHub account), and it makes the UX way better.
        
        Args:
            query: Search term to match against site names
            
        Returns:
            List of matching decrypted entries
        """
        self._require_unlocked()

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM entries WHERE site_name LIKE ? ORDER BY site_name COLLATE NOCASE",
            (f"%{query}%",),
        )
        rows = cursor.fetchall()
        return [self._decrypt_row(row) for row in rows]

    def get_entry_count(self) -> int:
        """Return the total number of entries in the vault."""
        self._require_unlocked()
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entries")
        return cursor.fetchone()[0]

    # ------------------------------------------------------------------
    # Master Password Management
    # ------------------------------------------------------------------

    def change_master_password(self, old_password: str, new_password: str) -> bool:
        """
        Change the master password.
        
        This is the most complex operation because we need to:
        1. Verify the old password
        2. Decrypt ALL entries with the old key
        3. Generate a new salt and derive a new key
        4. Re-encrypt ALL entries with the new key
        5. Update the stored salt and verification hash
        
        All done in a transaction so if anything fails, nothing changes.
        
        Args:
            old_password: Current master password
            new_password: New master password
            
        Returns:
            True if the password was changed, False if old password was wrong
        """
        self._require_unlocked()

        # Verify old password first
        cursor = self.conn.cursor()
        cursor.execute("SELECT salt, password_hash FROM master_config WHERE id = 1")
        row = cursor.fetchone()

        if not verify_master_password(old_password, row["salt"], row["password_hash"]):
            return False

        # Decrypt all entries with the old key
        all_entries = self.get_all_entries()

        # Generate new salt and key
        new_salt = generate_salt()
        new_key = derive_key(new_password, new_salt)
        new_hash = hash_master_password(new_password, new_salt)

        try:
            # Re-encrypt everything in a transaction
            cursor.execute("BEGIN")

            # Update master config
            cursor.execute(
                "UPDATE master_config SET salt = ?, password_hash = ? WHERE id = 1",
                (new_salt, new_hash),
            )

            # Re-encrypt each entry
            for entry in all_entries:
                username_enc = encrypt(entry["username"], new_key)
                password_enc = encrypt(entry["password"], new_key)
                notes_enc = encrypt(entry["notes"], new_key) if entry["notes"] else None

                cursor.execute(
                    """
                    UPDATE entries 
                    SET username_encrypted = ?, password_encrypted = ?, notes_encrypted = ?
                    WHERE id = ?
                    """,
                    (username_enc, password_enc, notes_enc, entry["id"]),
                )

            self.conn.commit()

            # Update internal state to use the new key
            self._salt = new_salt
            self.encryption_key = new_key
            return True

        except Exception:
            self.conn.rollback()
            raise

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _decrypt_row(self, row: sqlite3.Row) -> dict:
        """Decrypt a database row into a clean dictionary."""
        return {
            "id": row["id"],
            "site_name": row["site_name"],
            "url": row["url"] or "",
            "username": decrypt(row["username_encrypted"], self.encryption_key),
            "password": decrypt(row["password_encrypted"], self.encryption_key),
            "notes": decrypt(row["notes_encrypted"], self.encryption_key)
            if row["notes_encrypted"]
            else "",
            "category": row["category"] or "General",
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


# --- Self-test ---
if __name__ == "__main__":
    import tempfile

    print("=" * 50)
    print("Database Module Self-Test")
    print("=" * 50)

    # Use a temp file so we don't clutter anything
    test_db_path = os.path.join(tempfile.gettempdir(), "test_vault.db")

    # Clean up from any previous test
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    db = VaultDatabase(test_db_path)
    master_pw = "TestM@ster123!"

    # Test 1: Initialize vault
    print("\n1. Initializing vault...")
    db.initialize_vault(master_pw)
    print("   Vault created ✓")

    # Test 2: Add entries
    print("\n2. Adding entries...")
    id1 = db.add_entry("GitHub", "sammy@example.com", "gh_sup3r_s3cur3", url="https://github.com")
    id2 = db.add_entry("Gmail", "sammy@gmail.com", "gm@il_p@ss!", notes="Personal email")
    id3 = db.add_entry("School Portal", "sammy_student", "sch00l_p@ss", category="Education")
    print(f"   Added 3 entries (IDs: {id1}, {id2}, {id3}) ✓")

    # Test 3: Retrieve all entries
    print("\n3. Retrieving all entries...")
    entries = db.get_all_entries()
    for e in entries:
        print(f"   - {e['site_name']}: {e['username']} / {e['password'][:10]}...")
    print(f"   Total entries: {db.get_entry_count()} ✓")

    # Test 4: Search
    print("\n4. Searching for 'git'...")
    results = db.search_entries("git")
    print(f"   Found {len(results)} result(s): {results[0]['site_name']} ✓")

    # Test 5: Update entry
    print("\n5. Updating GitHub password...")
    db.update_entry(id1, password="new_gh_p@ssw0rd!")
    updated = db.get_entry(id1)
    print(f"   New password: {updated['password']} ✓")

    # Test 6: Delete entry
    print("\n6. Deleting School Portal entry...")
    db.delete_entry(id3)
    print(f"   Remaining entries: {db.get_entry_count()} ✓")

    # Test 7: Lock and re-unlock
    print("\n7. Locking vault...")
    db.lock()
    print("   Vault locked ✓")

    print("   Re-opening with correct password...")
    db2 = VaultDatabase(test_db_path)
    assert db2.unlock(master_pw) is True
    print("   Unlocked ✓")

    print("   Trying wrong password...")
    db3 = VaultDatabase(test_db_path)
    assert db3.unlock("wrong_password") is False
    print("   Correctly rejected ✓")

    # Test 8: Change master password
    print("\n8. Changing master password...")
    new_pw = "NewM@ster456!"
    assert db2.change_master_password(master_pw, new_pw) is True
    db2.lock()
    print("   Password changed ✓")

    print("   Verifying new password works...")
    db4 = VaultDatabase(test_db_path)
    assert db4.unlock(new_pw) is True
    entries = db4.get_all_entries()
    print(f"   Entries still readable: {len(entries)} entries ✓")
    print(f"   Data intact: {entries[0]['site_name']} - {entries[0]['username']} ✓")
    db4.lock()

    # Cleanup
    os.remove(test_db_path)

    print("\n" + "=" * 50)
    print("All tests passed!")
    print("=" * 50)
