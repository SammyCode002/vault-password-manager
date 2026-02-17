# 🔐 Vault — Local Password Manager

A desktop password manager built from scratch in Python. Encrypts all credentials locally using AES-128-CBC (via Fernet), derives keys with PBKDF2-SHA256 at 600,000 iterations, and never stores or transmits your master password.

Built as a cybersecurity-focused project to demonstrate real-world encryption, secure key derivation, and safe credential storage.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

---

## Features

- **AES-128-CBC encryption** with HMAC-SHA256 tamper detection (Fernet)
- **PBKDF2 key derivation** at 600,000 iterations (OWASP recommended minimum)
- **Password generator** with configurable length, character types, and passphrase mode
- **Entropy-based strength meter** with real-time feedback
- **One-click copy** with automatic clipboard clearing after 15 seconds
- **Search and filter** entries by name
- **Category organization** (General, Social, Work, Finance, etc.)
- **Change master password** with full re-encryption of all entries
- **Keyboard shortcuts** for power users
- **Dark themed UI** built with CustomTkinter

## Quick Start

```bash
# Clone the repo
git clone https://github.com/yourusername/vault-password-manager.git
cd vault-password-manager

# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
```

**Requirements:** Python 3.10+ and tkinter (usually included with Python).

On first launch, you'll create a master password. This is the only password you need to remember. There is no recovery mechanism — that's a security feature, not a bug.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + N` | Add new entry |
| `Ctrl + F` | Focus search bar |
| `Ctrl + L` | Lock vault |
| `Escape` | Clear search |

## Project Structure

```
vault-password-manager/
├── main.py                  # App entry point
├── requirements.txt         # Dependencies
├── core/
│   ├── encryption.py        # Key derivation, AES encrypt/decrypt
│   ├── database.py          # SQLite vault operations
│   └── password_gen.py      # Password & passphrase generator
├── gui/
│   ├── login_window.py      # Master password / setup screen
│   ├── main_window.py       # Vault view, settings, CRUD operations
│   └── generator.py         # Password generator dialog
└── .gitignore               # Excludes vault.db from version control
```

## Security Architecture

### How Your Data is Protected

```
Master Password
      │
      ▼
  PBKDF2-SHA256 (600,000 iterations + random salt)
      │
      ├──► Encryption Key (Fernet / AES-128-CBC + HMAC-SHA256)
      │         │
      │         ▼
      │    Encrypts: usernames, passwords, notes
      │
      └──► Verification Hash (SHA-512, domain-separated)
                │
                ▼
           Stored in DB (for login verification only)
```

### Key Design Decisions

**Master password is never stored.** A random 16-byte salt is generated on setup. The master password is run through PBKDF2-SHA256 at 600,000 iterations to derive the encryption key. A separate SHA-512 hash (domain-separated from the key derivation) is stored solely for verifying login attempts.

**PBKDF2 at 600,000 iterations** follows OWASP's 2023 recommendation. Each brute-force guess takes real computational time, making offline attacks impractical against a reasonable master password.

**Fernet encryption** (from Python's `cryptography` library) provides AES-128-CBC encryption plus HMAC-SHA256 authentication. If someone tampers with the encrypted data, decryption fails rather than returning corrupted plaintext.

**Site names are stored in plaintext.** This is a deliberate tradeoff. It allows instant search without decrypting every entry. An attacker with access to the vault file could see which services you use, but not your credentials. KeePass and Bitwarden make the same tradeoff.

**Clipboard auto-clears after 15 seconds.** Copied passwords don't sit in your clipboard indefinitely.

**On lock, the encryption key is wiped from memory.** The `lock()` method sets the key to `None`. (Note: Python's garbage collector and string immutability mean truly secure memory erasure would require lower-level techniques. This is a known limitation of any Python-based credential manager.)

### What This Doesn't Do (Honest Limitations)

- **No cloud sync** — data lives in a local SQLite file (`vault.db`). Back it up manually.
- **No browser extension** — you copy passwords manually.
- **No secure memory pinning** — Python doesn't give us direct control over memory pages. Production tools like KeePass use C/C++ for this reason.
- **No multi-device support** — single machine only.
- **Basic entropy estimation** — the strength meter uses `length × log2(pool_size)`, not pattern-aware analysis like zxcvbn.

These are intentional scope boundaries for a portfolio project, not oversights.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| GUI | CustomTkinter |
| Encryption | cryptography (Fernet / AES-128-CBC) |
| Key Derivation | PBKDF2-SHA256, 600K iterations |
| Storage | SQLite3 (standard library) |
| RNG | `secrets` module (cryptographic PRNG) |

## Running Tests

Each core module includes a self-test. Run them individually:

```bash
# Encryption module
python -m core.encryption

# Database module
python -m core.database

# Password generator
python -m core.password_gen
```

## License

MIT License. See [LICENSE](LICENSE) for details.

---

*Built as a Computer Science / Cybersecurity portfolio project.*
