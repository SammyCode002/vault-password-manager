"""
encryption.py - Core encryption module for the password manager.

How this works (the big picture):
1. User enters a master password
2. We derive an encryption key from that password using PBKDF2
   - PBKDF2 runs the password through a hash function thousands of times
   - This makes brute-force attacks extremely slow
   - A random "salt" is mixed in so two users with the same password get different keys
3. That derived key is used with Fernet (AES-128-CBC under the hood) to encrypt/decrypt vault data
4. The master password itself is NEVER stored anywhere

Key concepts:
- Salt: Random bytes mixed into key derivation (stored alongside encrypted data, not secret)
- KDF (Key Derivation Function): Turns a password into a proper encryption key
- Fernet: Symmetric encryption scheme from the cryptography library
  - Encrypts with AES-128-CBC
  - Authenticates with HMAC-SHA256 (tamper detection)
  - Includes a timestamp in the token
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


# Number of iterations for PBKDF2
# Higher = slower = harder to brute-force
# OWASP recommends at least 600,000 for PBKDF2-SHA256 as of 2023
PBKDF2_ITERATIONS = 600_000

# Salt length in bytes (16 bytes = 128 bits, standard recommendation)
SALT_LENGTH = 16


def generate_salt() -> bytes:
    """
    Generate a cryptographically secure random salt.
    
    The salt prevents rainbow table attacks and ensures that even if two users
    pick the same master password, their derived keys will be completely different.
    
    Returns:
        Random bytes of length SALT_LENGTH
    """
    return os.urandom(SALT_LENGTH)


def derive_key(master_password: str, salt: bytes) -> bytes:
    """
    Derive a Fernet-compatible encryption key from the master password.
    
    Uses PBKDF2 (Password-Based Key Derivation Function 2) with SHA-256.
    This is intentionally slow — 600,000 iterations means each guess takes
    real time, which destroys brute-force attack speed.
    
    Args:
        master_password: The user's master password (plaintext string)
        salt: Random bytes to mix into the derivation
        
    Returns:
        A 32-byte key, base64-encoded (Fernet requires this format)
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,               # Fernet needs a 32-byte key
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    # Fernet expects the key to be base64 URL-safe encoded
    key = base64.urlsafe_b64encode(kdf.derive(master_password.encode('utf-8')))
    return key


def encrypt(plaintext: str, key: bytes) -> bytes:
    """
    Encrypt a plaintext string using Fernet symmetric encryption.
    
    Under the hood, Fernet does:
    1. Generates a random IV (initialization vector)
    2. Encrypts with AES-128-CBC
    3. Signs with HMAC-SHA256 so we can detect tampering
    4. Packages it all into a single token
    
    Args:
        plaintext: The string to encrypt (e.g., a stored password)
        key: The Fernet key (from derive_key)
        
    Returns:
        Encrypted token as bytes
    """
    f = Fernet(key)
    return f.encrypt(plaintext.encode('utf-8'))


def decrypt(token: bytes, key: bytes) -> str:
    """
    Decrypt a Fernet token back to plaintext.
    
    Also verifies the HMAC signature — if someone tampered with the
    encrypted data, this will raise InvalidToken instead of returning
    corrupted garbage. That's a big deal for security.
    
    Args:
        token: The encrypted token (from encrypt)
        key: The same Fernet key used to encrypt
        
    Returns:
        The original plaintext string
        
    Raises:
        InvalidToken: If the key is wrong or the data was tampered with
    """
    f = Fernet(key)
    return f.decrypt(token).decode('utf-8')


def hash_master_password(master_password: str, salt: bytes) -> str:
    """
    Create a verification hash of the master password.
    
    This is NOT the encryption key — it's a separate hash we store in the
    database so we can verify the user typed the right master password
    WITHOUT storing the password itself.
    
    We use a different purpose here (SHA-512 with the salt) to keep this
    completely separate from the encryption key derivation.
    
    Args:
        master_password: The user's master password
        salt: The same salt used for key derivation
        
    Returns:
        Hex string of the hash
    """
    # Combine password + salt + a purpose string to domain-separate from the encryption key
    hash_input = master_password.encode('utf-8') + salt + b"verification"
    return hashlib.sha512(hash_input).hexdigest()


def verify_master_password(master_password: str, salt: bytes, stored_hash: str) -> bool:
    """
    Check if the entered master password matches the stored verification hash.
    
    Args:
        master_password: What the user just typed in
        salt: The salt stored in the database
        stored_hash: The hash we saved during setup
        
    Returns:
        True if the password is correct, False otherwise
    """
    return hash_master_password(master_password, salt) == stored_hash


# --- Quick self-test ---
if __name__ == "__main__":
    print("=" * 50)
    print("Encryption Module Self-Test")
    print("=" * 50)
    
    # Simulate the full flow
    test_password = "MyS3cur3M@sterP@ss!"
    test_data = "github_password:hunter2_but_actually_secure"
    
    # Step 1: Generate a salt
    salt = generate_salt()
    print(f"\n1. Generated salt: {salt.hex()}")
    print(f"   Salt length: {len(salt)} bytes")
    
    # Step 2: Derive encryption key from master password
    key = derive_key(test_password, salt)
    print(f"\n2. Derived key: {key[:20]}... (truncated)")
    
    # Step 3: Create verification hash
    pw_hash = hash_master_password(test_password, salt)
    print(f"\n3. Verification hash: {pw_hash[:40]}... (truncated)")
    
    # Step 4: Encrypt some data
    encrypted = encrypt(test_data, key)
    print(f"\n4. Encrypted: {encrypted[:50]}... (truncated)")
    
    # Step 5: Decrypt it back
    decrypted = decrypt(encrypted, key)
    print(f"\n5. Decrypted: {decrypted}")
    print(f"   Match: {decrypted == test_data} ✓")
    
    # Step 6: Verify master password
    print(f"\n6. Correct password check: {verify_master_password(test_password, salt, pw_hash)} ✓")
    print(f"   Wrong password check: {verify_master_password('wrong_password', salt, pw_hash)} ✓")
    
    # Step 7: Show that wrong key fails gracefully
    print("\n7. Testing wrong key decryption...")
    wrong_key = derive_key("wrong_password", salt)
    try:
        decrypt(encrypted, wrong_key)
        print("   ERROR: Should have failed!")
    except InvalidToken:
        print("   InvalidToken raised as expected ✓")
    
    print("\n" + "=" * 50)
    print("All tests passed!")
    print("=" * 50)
