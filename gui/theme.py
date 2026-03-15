"""
theme.py - Centralized theme system with dark/light mode support.

All colors, fonts, and styling constants live here.
"""

_current_mode = "dark"

DARK = {
    # Backgrounds — deep, rich, high contrast
    "bg_primary":   "#07090f",
    "bg_secondary": "#0d1117",
    "bg_card":      "#0d1117",
    "bg_input":     "#161b27",
    "bg_sidebar":   "#050709",
    "bg_hover":     "#1a2236",

    # Accent — vivid blue
    "accent":       "#3b82f6",
    "accent_hover": "#2563eb",
    "accent_muted": "#1e3058",

    # Status
    "success": "#22c55e",
    "error":   "#ef4444",
    "warning": "#f59e0b",

    # Text
    "text_primary":   "#f1f5f9",
    "text_secondary": "#94a3b8",
    "text_muted":     "#475569",

    # Borders
    "border":        "#1e293b",
    "border_subtle": "#111827",

    # Strength meter
    "strength_very_weak":   "#ef4444",
    "strength_weak":        "#f97316",
    "strength_moderate":    "#f59e0b",
    "strength_strong":      "#22c55e",
    "strength_very_strong": "#4ade80",

    # Special
    "sidebar_active":  "#172554",
    "avatar_colors":   ["#3b82f6", "#f97316", "#a855f7", "#22c55e", "#ef4444", "#f59e0b", "#4ade80", "#38bdf8"],
    "copy_btn":        "#166534",
    "copy_btn_hover":  "#15803d",
    "delete_btn":      "#dc2626",
    "delete_btn_hover": "#ef4444",
}

LIGHT = {
    "bg_primary":   "#ffffff",
    "bg_secondary": "#f8fafc",
    "bg_card":      "#ffffff",
    "bg_input":     "#f1f5f9",
    "bg_sidebar":   "#f0f4f8",
    "bg_hover":     "#e2e8f0",

    "accent":       "#2563eb",
    "accent_hover": "#1d4ed8",
    "accent_muted": "#dbeafe",

    "success": "#16a34a",
    "error":   "#dc2626",
    "warning": "#d97706",

    "text_primary":   "#0f172a",
    "text_secondary": "#475569",
    "text_muted":     "#94a3b8",

    "border":        "#e2e8f0",
    "border_subtle": "#f1f5f9",

    "strength_very_weak":   "#dc2626",
    "strength_weak":        "#ea580c",
    "strength_moderate":    "#d97706",
    "strength_strong":      "#16a34a",
    "strength_very_strong": "#15803d",

    "sidebar_active":  "#dbeafe",
    "avatar_colors":   ["#2563eb", "#ea580c", "#9333ea", "#16a34a", "#dc2626", "#d97706", "#15803d", "#0284c7"],
    "copy_btn":        "#16a34a",
    "copy_btn_hover":  "#15803d",
    "delete_btn":      "#dc2626",
    "delete_btn_hover": "#b91c1c",
}

# Per-category accent colors — used for card borders and avatars
CATEGORY_COLORS = {
    "General":   "#475569",  # slate
    "Social":    "#e879f9",  # fuchsia
    "Work":      "#fbbf24",  # amber
    "Finance":   "#4ade80",  # green
    "Shopping":  "#fb923c",  # orange
    "Education": "#a78bfa",  # violet
    "Other":     "#38bdf8",  # sky
}


def get_colors() -> dict:
    return DARK if _current_mode == "dark" else LIGHT


def get_mode() -> str:
    return _current_mode


def set_mode(mode: str):
    global _current_mode
    _current_mode = mode


def toggle_mode() -> str:
    global _current_mode
    _current_mode = "light" if _current_mode == "dark" else "dark"
    return _current_mode


def get_strength_color(strength_label: str) -> str:
    colors = get_colors()
    mapping = {
        "Very Weak":   colors["strength_very_weak"],
        "Weak":        colors["strength_weak"],
        "Moderate":    colors["strength_moderate"],
        "Strong":      colors["strength_strong"],
        "Very Strong": colors["strength_very_strong"],
    }
    return mapping.get(strength_label, colors["text_muted"])


def get_category_color(category: str) -> str:
    """Get the accent color for a category."""
    return CATEGORY_COLORS.get(category, CATEGORY_COLORS["General"])


def get_avatar_color(name: str) -> str:
    colors = get_colors()
    avatar_colors = colors["avatar_colors"]
    index = sum(ord(c) for c in name) % len(avatar_colors)
    return avatar_colors[index]


SITE_ICONS = {
    "github":    "⌨",
    "google":    "🔍",
    "gmail":     "✉",
    "facebook":  "👥",
    "twitter":   "🐦",
    "instagram": "📷",
    "netflix":   "🎬",
    "spotify":   "🎵",
    "amazon":    "📦",
    "discord":   "💬",
    "reddit":    "🗨",
    "youtube":   "▶",
    "linkedin":  "💼",
    "steam":     "🎮",
    "apple":     "🍎",
    "microsoft": "🪟",
    "slack":     "💬",
    "twitch":    "🟣",
    "paypal":    "💳",
    "bank":      "🏦",
}

CATEGORY_ICONS = {
    "General":   "🔑",
    "Social":    "👥",
    "Work":      "💼",
    "Finance":   "💳",
    "Shopping":  "🛒",
    "Education": "📚",
    "Other":     "📌",
}


def get_site_icon(site_name: str, category: str = "General") -> str:
    lower = site_name.lower()
    for key, icon in SITE_ICONS.items():
        if key in lower:
            return icon
    return CATEGORY_ICONS.get(category, "🔑")
