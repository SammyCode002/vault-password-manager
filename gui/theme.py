"""
theme.py - Centralized theme system with dark/light mode support.

All colors, fonts, and styling constants live here so every screen
stays visually consistent. The toggle_theme() function swaps everything
at once.
"""

# Current mode: "dark" or "light"
_current_mode = "dark"

DARK = {
    # Backgrounds
    "bg_primary": "#0f1117",
    "bg_secondary": "#161b22",
    "bg_card": "#1c2333",
    "bg_input": "#232b3e",
    "bg_sidebar": "#0d1117",
    "bg_hover": "#2a3346",

    # Accent
    "accent": "#4f8ff7",
    "accent_hover": "#3a7ae0",
    "accent_muted": "#1e3a5f",

    # Status
    "success": "#3fb950",
    "error": "#f85149",
    "warning": "#d29922",

    # Text
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "text_muted": "#484f58",

    # Borders
    "border": "#30363d",
    "border_subtle": "#21262d",

    # Strength meter
    "strength_very_weak": "#f85149",
    "strength_weak": "#f0883e",
    "strength_moderate": "#d29922",
    "strength_strong": "#3fb950",
    "strength_very_strong": "#56d364",

    # Special
    "sidebar_active": "#1e3a5f",
    "avatar_colors": ["#4f8ff7", "#f0883e", "#a371f7", "#3fb950", "#f85149", "#d29922", "#56d364", "#79c0ff"],
    "copy_btn": "#238636",
    "copy_btn_hover": "#2ea043",
    "delete_btn": "#da3633",
    "delete_btn_hover": "#f85149",
}

LIGHT = {
    # Backgrounds
    "bg_primary": "#ffffff",
    "bg_secondary": "#f6f8fa",
    "bg_card": "#ffffff",
    "bg_input": "#f6f8fa",
    "bg_sidebar": "#f0f2f5",
    "bg_hover": "#eaeef2",

    # Accent
    "accent": "#0969da",
    "accent_hover": "#0550ae",
    "accent_muted": "#ddf4ff",

    # Status
    "success": "#1a7f37",
    "error": "#cf222e",
    "warning": "#9a6700",

    # Text
    "text_primary": "#1f2328",
    "text_secondary": "#656d76",
    "text_muted": "#8c959f",

    # Borders
    "border": "#d0d7de",
    "border_subtle": "#e1e4e8",

    # Strength meter
    "strength_very_weak": "#cf222e",
    "strength_weak": "#bc4c00",
    "strength_moderate": "#9a6700",
    "strength_strong": "#1a7f37",
    "strength_very_strong": "#116329",

    # Special
    "sidebar_active": "#ddf4ff",
    "avatar_colors": ["#0969da", "#bc4c00", "#8250df", "#1a7f37", "#cf222e", "#9a6700", "#116329", "#0550ae"],
    "copy_btn": "#1a7f37",
    "copy_btn_hover": "#116329",
    "delete_btn": "#cf222e",
    "delete_btn_hover": "#a40e26",
}


def get_colors() -> dict:
    """Get the current theme's color palette."""
    return DARK if _current_mode == "dark" else LIGHT


def get_mode() -> str:
    """Get the current theme mode."""
    return _current_mode


def set_mode(mode: str):
    """Set the theme mode ('dark' or 'light')."""
    global _current_mode
    _current_mode = mode


def toggle_mode() -> str:
    """Toggle between dark and light mode. Returns the new mode."""
    global _current_mode
    _current_mode = "light" if _current_mode == "dark" else "dark"
    return _current_mode


def get_strength_color(strength_label: str) -> str:
    """Get the color for a password strength label."""
    colors = get_colors()
    mapping = {
        "Very Weak": colors["strength_very_weak"],
        "Weak": colors["strength_weak"],
        "Moderate": colors["strength_moderate"],
        "Strong": colors["strength_strong"],
        "Very Strong": colors["strength_very_strong"],
    }
    return mapping.get(strength_label, colors["text_muted"])


def get_avatar_color(name: str) -> str:
    """Get a consistent color for a site name's avatar."""
    colors = get_colors()
    avatar_colors = colors["avatar_colors"]
    index = sum(ord(c) for c in name) % len(avatar_colors)
    return avatar_colors[index]


# Site icon mapping — first letter with category-based fallback icons
SITE_ICONS = {
    "github": "⌨",
    "google": "🔍",
    "gmail": "✉",
    "facebook": "👥",
    "twitter": "🐦",
    "instagram": "📷",
    "netflix": "🎬",
    "spotify": "🎵",
    "amazon": "📦",
    "discord": "💬",
    "reddit": "🗨",
    "youtube": "▶",
    "linkedin": "💼",
    "steam": "🎮",
    "apple": "🍎",
    "microsoft": "🪟",
    "slack": "💬",
    "twitch": "🟣",
    "paypal": "💳",
    "bank": "🏦",
}

CATEGORY_ICONS = {
    "General": "🔑",
    "Social": "👥",
    "Work": "💼",
    "Finance": "💳",
    "Shopping": "🛒",
    "Education": "📚",
    "Other": "📌",
}


def get_site_icon(site_name: str, category: str = "General") -> str:
    """Get an icon for a site, falling back to category icon."""
    lower = site_name.lower()
    for key, icon in SITE_ICONS.items():
        if key in lower:
            return icon
    return CATEGORY_ICONS.get(category, "🔑")
