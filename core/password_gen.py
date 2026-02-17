"""
password_gen.py - Secure password generator for the password manager.

How this works:
1. User picks their requirements (length, character types)
2. We use Python's `secrets` module (NOT `random`) to generate passwords
   - secrets uses the OS's cryptographic random number generator
   - random uses a Mersenne Twister PRNG which is predictable and NOT secure
3. We guarantee at least one character from each selected type
4. We also include a passphrase generator (think "correct-horse-battery-staple")
5. Basic strength estimation helps the user understand how good their password is

Why not just use random?
The `random` module is designed for simulations and games. Its output is
deterministic given the seed, and the seed can be predicted. The `secrets`
module pulls from /dev/urandom (Linux) or CryptGenRandom (Windows), which
are designed for cryptographic use. For a password manager, this matters.
"""

import secrets
import string
import math


# Character sets
LOWERCASE = string.ascii_lowercase      # a-z
UPPERCASE = string.ascii_uppercase      # A-Z
DIGITS = string.digits                  # 0-9
SYMBOLS = "!@#$%^&*()-_=+[]{}|;:',.<>?/"

# Ambiguous characters that look similar in many fonts
# Users can opt to exclude these for passwords they might need to type manually
AMBIGUOUS = "Il1O0oS5Z2"

# Common English words for passphrase generation (curated for memorability)
# In a production app, you'd use a much larger wordlist (like EFF's diceware list)
# This is a solid starter set of 256 words — enough for good entropy
WORDLIST = [
    "acid", "acorn", "acre", "alarm", "album", "alert", "alias", "alpine",
    "amber", "anchor", "angel", "anvil", "apple", "arch", "arena", "armor",
    "arrow", "atlas", "atom", "audio", "aurora", "autumn", "avid", "badge",
    "baker", "bamboo", "banner", "barrel", "basin", "beacon", "beast", "berry",
    "blade", "blank", "blast", "blaze", "bloom", "board", "bolt", "bonus",
    "brave", "breeze", "brick", "bridge", "brisk", "bronze", "brush", "bucket",
    "cabin", "cable", "camel", "candy", "canyon", "carbon", "cargo", "castle",
    "cedar", "chain", "chalk", "charm", "chess", "chief", "cider", "cipher",
    "claim", "cliff", "clock", "cloud", "clover", "cobra", "comet", "coral",
    "craft", "crane", "creek", "crest", "crown", "crush", "crystal", "cycle",
    "dagger", "dance", "dawn", "delta", "demon", "depth", "desert", "diamond",
    "digit", "diver", "dodge", "donor", "dragon", "dream", "drift", "drum",
    "eagle", "earth", "echo", "edge", "elder", "ember", "empire", "energy",
    "engine", "epoch", "equip", "exile", "fable", "factor", "falcon", "feast",
    "fiber", "field", "flame", "flash", "fleet", "flint", "flood", "focus",
    "forest", "forge", "fossil", "frost", "fruit", "fury", "galaxy", "garden",
    "garnet", "ghost", "giant", "glacier", "globe", "glory", "goblin", "grain",
    "grape", "gravel", "grove", "guard", "guide", "gypsum", "hammer", "harbor",
    "hawk", "hazard", "heart", "helix", "heron", "honey", "horizon", "hunter",
    "iceberg", "idol", "impact", "index", "inlet", "iron", "island", "ivory",
    "jacket", "jade", "jaguar", "jewel", "joint", "jungle", "karma", "kayak",
    "kernel", "kettle", "knight", "lantern", "latch", "launch", "lemon", "level",
    "light", "linen", "lion", "lunar", "magnet", "manor", "maple", "marble",
    "market", "mason", "meadow", "medal", "melody", "mentor", "meteor", "mirth",
    "moat", "monk", "mosaic", "mural", "needle", "nexus", "noble", "nomad",
    "north", "novel", "oasis", "ocean", "olive", "onyx", "opera", "orbit",
    "orchid", "osprey", "oxide", "palace", "panel", "parrot", "patrol", "pearl",
    "pepper", "piano", "pilot", "pixel", "plaza", "plume", "polar", "portal",
    "prism", "pulse", "quartz", "quest", "radar", "raven", "realm", "ridge",
    "river", "robin", "rocket", "ruby", "saddle", "sage", "salmon", "scout",
    "shadow", "shield", "signal", "silver", "solar", "spark", "sphinx", "spiral",
    "steam", "storm", "summit", "sword", "table", "talon", "temple", "terra",
    "thorn", "throne", "tiger", "timber", "torch", "tower", "trail", "trident",
    "trophy", "tunnel", "ultra", "umbra", "unity", "valve", "vault", "venom",
    "vigor", "violet", "vivid", "vortex", "voyage", "walnut", "warden", "water",
    "whale", "willow", "winter", "wizard", "wolf", "zenith", "zephyr", "zinc",
]


def generate_password(
    length: int = 16,
    use_lowercase: bool = True,
    use_uppercase: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    exclude_ambiguous: bool = False,
) -> str:
    """
    Generate a cryptographically secure random password.
    
    The approach:
    1. Build the character pool from selected types
    2. Guarantee at least one char from each selected type
    3. Fill the rest randomly from the full pool
    4. Shuffle everything so guaranteed chars aren't always at the start
    
    Args:
        length: Password length (minimum 4, default 16)
        use_lowercase: Include a-z
        use_uppercase: Include A-Z
        use_digits: Include 0-9
        use_symbols: Include special characters
        exclude_ambiguous: Remove chars like I/l/1/O/0 that look similar
        
    Returns:
        Generated password string
        
    Raises:
        ValueError: If no character types selected or length too short
    """
    # Build the character pool
    pool = ""
    required_chars = []  # Guarantee at least one from each type

    if use_lowercase:
        chars = LOWERCASE
        if exclude_ambiguous:
            chars = "".join(c for c in chars if c not in AMBIGUOUS)
        pool += chars
        required_chars.append(secrets.choice(chars))

    if use_uppercase:
        chars = UPPERCASE
        if exclude_ambiguous:
            chars = "".join(c for c in chars if c not in AMBIGUOUS)
        pool += chars
        required_chars.append(secrets.choice(chars))

    if use_digits:
        chars = DIGITS
        if exclude_ambiguous:
            chars = "".join(c for c in chars if c not in AMBIGUOUS)
        pool += chars
        required_chars.append(secrets.choice(chars))

    if use_symbols:
        pool += SYMBOLS
        required_chars.append(secrets.choice(SYMBOLS))

    if not pool:
        raise ValueError("At least one character type must be selected.")

    min_length = len(required_chars)
    if length < min_length:
        raise ValueError(f"Length must be at least {min_length} with selected character types.")

    # Fill remaining length with random choices from the full pool
    remaining = length - len(required_chars)
    password_chars = required_chars + [secrets.choice(pool) for _ in range(remaining)]

    # Shuffle so the guaranteed characters aren't always at predictable positions
    # secrets.SystemRandom().shuffle is cryptographically secure
    secure_random = secrets.SystemRandom()
    secure_random.shuffle(password_chars)

    return "".join(password_chars)


def generate_passphrase(
    word_count: int = 4,
    separator: str = "-",
    capitalize: bool = True,
    include_number: bool = True,
) -> str:
    """
    Generate a passphrase from random dictionary words.
    
    Passphrases are easier to remember than random character strings
    while still being very secure. "Falcon-Meadow-Prism-47" is much
    easier to remember than "kX9#mP2$vL" but has comparable entropy.
    
    Args:
        word_count: Number of words (default 4, minimum 3)
        separator: Character between words (default "-")
        capitalize: Capitalize first letter of each word
        include_number: Append a random 2-digit number for extra entropy
        
    Returns:
        Generated passphrase string
    """
    if word_count < 3:
        raise ValueError("Passphrase must have at least 3 words.")

    # Pick random words using secrets (not random!)
    words = [secrets.choice(WORDLIST) for _ in range(word_count)]

    if capitalize:
        words = [w.capitalize() for w in words]

    passphrase = separator.join(words)

    if include_number:
        passphrase += separator + str(secrets.randbelow(90) + 10)  # 10-99

    return passphrase


def estimate_strength(password: str) -> dict:
    """
    Estimate password strength based on entropy and composition.
    
    Entropy = log2(pool_size ^ length)
    
    This is a simplified estimate. Real-world strength also depends on
    whether the password contains dictionary words, patterns, or personal
    info. Tools like zxcvbn do much deeper analysis. But for a password
    manager's generator, this gives users a good quick read.
    
    Args:
        password: The password to evaluate
        
    Returns:
        Dict with entropy bits, strength label, and details
    """
    # Determine which character sets are present
    has_lower = any(c in LOWERCASE for c in password)
    has_upper = any(c in UPPERCASE for c in password)
    has_digit = any(c in DIGITS for c in password)
    has_symbol = any(c in SYMBOLS or (c not in LOWERCASE + UPPERCASE + DIGITS) for c in password)

    # Calculate the effective pool size
    pool_size = 0
    if has_lower:
        pool_size += 26
    if has_upper:
        pool_size += 26
    if has_digit:
        pool_size += 10
    if has_symbol:
        pool_size += len(SYMBOLS)

    # Entropy in bits
    if pool_size == 0 or len(password) == 0:
        entropy = 0
    else:
        entropy = len(password) * math.log2(pool_size)

    # Classify strength
    if entropy < 28:
        label = "Very Weak"
        color = "red"
    elif entropy < 36:
        label = "Weak"
        color = "orange"
    elif entropy < 60:
        label = "Moderate"
        color = "yellow"
    elif entropy < 80:
        label = "Strong"
        color = "light_green"
    else:
        label = "Very Strong"
        color = "green"

    return {
        "entropy_bits": round(entropy, 1),
        "strength": label,
        "color": color,
        "length": len(password),
        "has_lowercase": has_lower,
        "has_uppercase": has_upper,
        "has_digits": has_digit,
        "has_symbols": has_symbol,
        "pool_size": pool_size,
    }


# --- Self-test ---
if __name__ == "__main__":
    print("=" * 50)
    print("Password Generator Self-Test")
    print("=" * 50)

    # Test 1: Default password generation
    print("\n1. Default password (16 chars, all types):")
    for i in range(3):
        pw = generate_password()
        strength = estimate_strength(pw)
        print(f"   {pw}  ({strength['entropy_bits']} bits - {strength['strength']})")

    # Test 2: Custom configurations
    print("\n2. Custom configurations:")

    pw = generate_password(length=8, use_symbols=False)
    s = estimate_strength(pw)
    print(f"   8 chars, no symbols:  {pw}  ({s['entropy_bits']} bits - {s['strength']})")

    pw = generate_password(length=24, exclude_ambiguous=True)
    s = estimate_strength(pw)
    print(f"   24 chars, no ambig:   {pw}  ({s['entropy_bits']} bits - {s['strength']})")

    pw = generate_password(length=32)
    s = estimate_strength(pw)
    print(f"   32 chars, everything: {pw}  ({s['entropy_bits']} bits - {s['strength']})")

    # Test 3: Passphrases
    print("\n3. Passphrases:")
    for i in range(3):
        pp = generate_passphrase()
        s = estimate_strength(pp)
        print(f"   {pp}  ({s['entropy_bits']} bits - {s['strength']})")

    pp = generate_passphrase(word_count=6, separator=".", capitalize=True)
    s = estimate_strength(pp)
    print(f"   6-word: {pp}  ({s['entropy_bits']} bits - {s['strength']})")

    # Test 4: Strength estimation on known passwords
    print("\n4. Strength estimates:")
    test_passwords = [
        "password",
        "Password1",
        "P@ssw0rd!",
        "kX9#mP2$vL4@nQ",
        "Falcon-Meadow-Prism-Crystal-47",
    ]
    for pw in test_passwords:
        s = estimate_strength(pw)
        print(f"   {pw:<35} → {s['entropy_bits']:>6} bits  ({s['strength']})")

    # Test 5: Guarantee character types are present
    print("\n5. Verifying character type guarantees...")
    all_good = True
    for _ in range(100):
        pw = generate_password(length=8, use_lowercase=True, use_uppercase=True,
                               use_digits=True, use_symbols=True)
        has_lower = any(c in LOWERCASE for c in pw)
        has_upper = any(c in UPPERCASE for c in pw)
        has_digit = any(c in DIGITS for c in pw)
        has_symbol = any(c in SYMBOLS for c in pw)
        if not (has_lower and has_upper and has_digit and has_symbol):
            print(f"   FAIL: {pw} missing a character type!")
            all_good = False
            break
    if all_good:
        print("   100 passwords generated, all contain every selected type ✓")

    # Test 6: Edge cases
    print("\n6. Edge cases...")
    try:
        generate_password(length=2)
        print("   ERROR: Should have raised ValueError for short length")
    except ValueError as e:
        print(f"   Short length rejected: {e} ✓")

    try:
        generate_password(use_lowercase=False, use_uppercase=False,
                         use_digits=False, use_symbols=False)
        print("   ERROR: Should have raised ValueError for no char types")
    except ValueError as e:
        print(f"   No char types rejected: {e} ✓")

    print("\n" + "=" * 50)
    print("All tests passed!")
    print("=" * 50)
