# 🔐 Vault — Local Password Manager

A desktop password manager I built from scratch in Python. Everything stays on your machine — no accounts, no sync, no cloud. Credentials are encrypted with AES-128-CBC (via Fernet), keys are derived with PBKDF2-SHA256 at 600,000 iterations, and your master password is never stored anywhere.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

---

## Features

**Security**
- AES-128-CBC encryption with HMAC-SHA256 tamper detection (Fernet)
- PBKDF2-SHA256 key derivation at 600,000 iterations (OWASP 2023 minimum)
- Master password never stored — only a domain-separated SHA-512 verification hash
- Clipboard auto-clears 15 seconds after copying a password
- Encryption key wiped from memory on vault lock

**Vault**
- Add, edit, delete entries with site name, username, password, URL, and notes
- Category organization — General, Social, Work, Finance, Shopping, Education
- Live entry counts per category in the sidebar
- Search by site name (plaintext, no full decryption needed)
- Reveal password in-place with the eye button
- One-click URL open in browser
- Password age shown on each card ("Updated 3d ago")
- Export all entries to CSV / Import from CSV
- Change master password with full re-encryption of every entry
- Auto-lock after configurable inactivity (5 min, 10 min, 30 min, 1 hour)

**Password Generator**
- Random passwords — configurable length (6–64), character types, exclude ambiguous chars
- Passphrase mode — word count, separator, capitalize, append number
- Entropy-based strength meter with real-time feedback
- Copy directly from the generator without closing the dialog

**UI**
- Dark and light mode with full theme switching
- Category-colored card accents so entries are visually organized at a glance
- Keyboard shortcuts for everything you do often

---

## Quick Start

```bash
git clone https://github.com/SammyCode002/vault-password-manager.git
cd vault-password-manager
pip install -r requirements.txt
python main.py
```

Python 3.10+ required. tkinter is included with most Python installs.

On first launch you'll create a master password. That's the only one you need to remember. There's no recovery option — that's intentional.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + N` | New entry |
| `Ctrl + F` | Focus search |
| `Ctrl + L` | Lock vault |
| `Escape` | Clear search |

---

## Project Structure

```
vault-password-manager/
├── main.py                  # Entry point
├── requirements.txt
├── core/
│   ├── encryption.py        # PBKDF2 key derivation, Fernet encrypt/decrypt
│   ├── database.py          # SQLite vault — CRUD, export/import, master password change
│   └── password_gen.py      # Password & passphrase generator, strength estimation
└── gui/
    ├── login_window.py      # Setup / unlock screen
    ├── main_window.py       # Main vault view, settings, dialogs
    ├── generator.py         # Password generator dialog
    └── theme.py             # Color system, dark/light palettes, category colors
```

---

## How the Security Works

```
Master Password
      │
      ▼
  PBKDF2-SHA256 (600,000 iterations + random 16-byte salt)
      │
      ├──► Encryption Key  →  Fernet (AES-128-CBC + HMAC-SHA256)
      │                            │
      │                            ▼
      │                    Encrypts: username, password, notes
      │
      └──► Verification Hash  →  SHA-512 (domain-separated)
                                       │
                                       ▼
                               Stored in DB (login check only)
```

**Why 600,000 PBKDF2 iterations?** Each login attempt takes real CPU time — fast enough that you barely notice it (~0.5s), slow enough that offline brute-force is painful. OWASP's 2023 recommendation for PBKDF2-SHA256 is 600,000.

**Why are site names in plaintext?** So search works without decrypting every row. An attacker with your vault file can see which services you use but not your actual credentials. KeePass and Bitwarden make the same call.

**Why does Fernet include HMAC?** If someone modifies the encrypted bytes directly, decryption throws `InvalidToken` instead of silently returning garbage. Tamper detection matters.

---

## Honest Limitations

- **No cloud sync** — `vault.db` is a local file. Back it up yourself.
- **No browser extension** — passwords are copied manually.
- **No secure memory pinning** — Python can't prevent the OS from swapping memory pages. A real production tool would use C/C++ for this (KeePass does). This is a known tradeoff for any Python credential manager.
- **Basic entropy estimation** — strength uses `length × log₂(pool_size)`. It doesn't detect dictionary words or patterns the way zxcvbn does.
- **Single device** — no multi-device support.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| GUI | CustomTkinter |
| Encryption | `cryptography` — Fernet / AES-128-CBC |
| Key Derivation | PBKDF2-SHA256, 600K iterations |
| Storage | SQLite3 (stdlib) |
| RNG | `secrets` module (OS CSPRNG) |

---

## Self-Tests

Each core module has a built-in self-test:

```bash
python -m core.encryption    # key derivation, encrypt/decrypt, tamper detection
python -m core.database      # full CRUD + master password change cycle
python -m core.password_gen  # generation, entropy estimation, edge cases
```

---

## License

MIT. See [LICENSE](LICENSE).

---

*CS / Cybersecurity portfolio project — built to actually work, not just look good on a resume.*
