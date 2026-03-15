"""
main_window.py - Vault main window with sidebar navigation and modern card layout.

Features:
- Sidebar with category filters and live entry counts
- Entry cards with reveal-password toggle and open-URL button
- Password age display on each card
- Auto-lock after configurable inactivity timeout
- Export to CSV / Import from CSV in Settings
- Dark/light mode toggle
- Keyboard shortcuts
- Change master password
"""

import time
import webbrowser
from datetime import datetime, timezone
from tkinter import filedialog
from typing import Callable, Optional

import customtkinter as ctk

from core.database import VaultDatabase
from core.password_gen import estimate_strength
from gui.generator import PasswordGeneratorDialog
from gui.theme import (
    get_colors, get_strength_color, get_avatar_color,
    get_site_icon, get_mode, toggle_mode, CATEGORY_ICONS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_age(iso_string: str) -> str:
    """Convert an ISO timestamp to a human-readable relative time string."""
    try:
        dt = datetime.fromisoformat(iso_string)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        s = int((datetime.now(timezone.utc) - dt).total_seconds())
        if s < 60:
            return "just now"
        if s < 3600:
            return f"{s // 60}m ago"
        if s < 86_400:
            return f"{s // 3600}h ago"
        if s < 30 * 86_400:
            return f"{s // 86_400}d ago"
        if s < 365 * 86_400:
            return f"{s // (30 * 86_400)}mo ago"
        return f"{s // (365 * 86_400)}yr ago"
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(ctk.CTkFrame):
    """Main vault view with sidebar navigation."""

    def __init__(
        self,
        parent: ctk.CTk,
        db: VaultDatabase,
        on_lock: Callable,
        on_theme_change: Callable = None,
    ):
        C = get_colors()
        super().__init__(parent, fg_color=C["bg_primary"])
        self.db = db
        self.on_lock = on_lock
        self.on_theme_change = on_theme_change
        self.clipboard_clear_job = None
        self.active_category = "All"

        # Auto-lock state
        self._auto_lock_minutes = 0
        self._last_activity = time.monotonic()
        self._auto_lock_job = None

        self._build_ui()
        self._refresh_entries()
        self._bind_shortcuts()
        self._setup_auto_lock()

    # ------------------------------------------------------------------
    # Shortcuts
    # ------------------------------------------------------------------

    def _bind_shortcuts(self):
        top = self.winfo_toplevel()
        top.bind("<Control-n>", lambda e: self._show_add_form())
        top.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        top.bind("<Control-l>", lambda e: self._lock_vault())
        top.bind("<Escape>", lambda e: self._clear_search())

    # ------------------------------------------------------------------
    # Auto-lock
    # ------------------------------------------------------------------

    def _setup_auto_lock(self):
        top = self.winfo_toplevel()
        for event in ("<Motion>", "<KeyPress>", "<Button>"):
            top.bind(event, self._reset_inactivity, add="+")
        self._schedule_inactivity_check()

    def _reset_inactivity(self, event=None):
        self._last_activity = time.monotonic()

    def _schedule_inactivity_check(self):
        self._auto_lock_job = self.after(30_000, self._check_inactivity)

    def _check_inactivity(self):
        if self._auto_lock_minutes > 0:
            idle = time.monotonic() - self._last_activity
            if idle >= self._auto_lock_minutes * 60:
                self._lock_vault()
                return
        self._schedule_inactivity_check()

    def set_auto_lock(self, minutes: int):
        self._auto_lock_minutes = minutes
        self._last_activity = time.monotonic()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        C = get_colors()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ==========================================
        # SIDEBAR
        # ==========================================
        self.sidebar = ctk.CTkFrame(
            self, width=220, fg_color=C["bg_sidebar"],
            corner_radius=0, border_width=0,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(4, weight=1)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(20, 24))

        ctk.CTkLabel(
            logo_frame, text="🛡", font=ctk.CTkFont(size=22),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            logo_frame, text="Vault",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=C["text_primary"],
        ).pack(side="left")

        # Add Button
        self.add_btn = ctk.CTkButton(
            self.sidebar, text="＋  New Entry",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40, fg_color=C["accent"],
            hover_color=C["accent_hover"],
            corner_radius=10,
            command=self._show_add_form,
        )
        self.add_btn.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 20))

        # Category Filters
        filter_label = ctk.CTkLabel(
            self.sidebar, text="CATEGORIES",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=C["text_muted"], anchor="w",
        )
        filter_label.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 6))

        self.category_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.category_frame.grid(row=3, column=0, sticky="new", padx=8)

        self.category_buttons = {}
        categories = ["All", "General", "Social", "Work", "Finance", "Shopping", "Education", "Other"]
        cat_icons = {"All": "📋", **CATEGORY_ICONS}

        for cat in categories:
            icon = cat_icons.get(cat, "📌")
            btn = ctk.CTkButton(
                self.category_frame,
                text=f"  {icon}  {cat}",
                font=ctk.CTkFont(size=12),
                height=34,
                fg_color=C["sidebar_active"] if cat == "All" else "transparent",
                hover_color=C["bg_hover"],
                text_color=C["text_primary"] if cat == "All" else C["text_secondary"],
                anchor="w",
                corner_radius=8,
                command=lambda c=cat: self._filter_category(c),
            )
            btn.pack(fill="x", pady=1)
            self.category_buttons[cat] = btn

        # Bottom controls
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.grid(row=5, column=0, sticky="sew", padx=16, pady=(8, 16))

        self.theme_btn = ctk.CTkButton(
            bottom_frame,
            text="☀  Light Mode" if get_mode() == "dark" else "🌙  Dark Mode",
            font=ctk.CTkFont(size=12), height=34,
            fg_color="transparent", hover_color=C["bg_hover"],
            text_color=C["text_secondary"], anchor="w", corner_radius=8,
            command=self._toggle_theme,
        )
        self.theme_btn.pack(fill="x", pady=(0, 2))

        self.settings_btn = ctk.CTkButton(
            bottom_frame, text="⚙  Settings",
            font=ctk.CTkFont(size=12), height=34,
            fg_color="transparent", hover_color=C["bg_hover"],
            text_color=C["text_secondary"], anchor="w", corner_radius=8,
            command=self._show_settings,
        )
        self.settings_btn.pack(fill="x", pady=(0, 2))

        self.lock_btn = ctk.CTkButton(
            bottom_frame, text="🔒  Lock Vault",
            font=ctk.CTkFont(size=12), height=34,
            fg_color="transparent", hover_color=C["bg_hover"],
            text_color=C["text_secondary"], anchor="w", corner_radius=8,
            command=self._lock_vault,
        )
        self.lock_btn.pack(fill="x")

        # ==========================================
        # MAIN CONTENT AREA
        # ==========================================
        content = ctk.CTkFrame(self, fg_color=C["bg_primary"], corner_radius=0)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(2, weight=1)

        # Header
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(20, 4))

        self.header_title = ctk.CTkLabel(
            header, text="All Entries",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=C["text_primary"],
        )
        self.header_title.pack(anchor="w")

        self.header_subtitle = ctk.CTkLabel(
            header, text="",
            font=ctk.CTkFont(size=12),
            text_color=C["text_muted"],
        )
        self.header_subtitle.pack(anchor="w")

        # Search Bar
        search_frame = ctk.CTkFrame(content, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=28, pady=(12, 8))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search entries...",
            font=ctk.CTkFont(size=13), height=42,
            fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], placeholder_text_color=C["text_muted"],
            corner_radius=10,
        )
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<KeyRelease>", self._on_search)

        # Entry List
        self.list_frame = ctk.CTkScrollableFrame(
            content, fg_color="transparent",
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["text_muted"],
        )
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=28, pady=(4, 12))
        self.list_frame.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # Category Filtering
    # ------------------------------------------------------------------

    def _filter_category(self, category: str):
        C = get_colors()
        self.active_category = category

        for cat, btn in self.category_buttons.items():
            if cat == category:
                btn.configure(fg_color=C["sidebar_active"], text_color=C["text_primary"])
            else:
                btn.configure(fg_color="transparent", text_color=C["text_secondary"])

        if category == "All":
            self.header_title.configure(text="All Entries")
        else:
            icon = CATEGORY_ICONS.get(category, "📌")
            self.header_title.configure(text=f"{icon}  {category}")

        self._refresh_entries()

    def _update_category_counts(self, all_entries: list):
        """Update sidebar category button labels with live entry counts."""
        counts: dict[str, int] = {}
        for e in all_entries:
            cat = e.get("category", "General")
            counts[cat] = counts.get(cat, 0) + 1

        total = len(all_entries)
        cat_icons = {"All": "📋", **CATEGORY_ICONS}

        for cat, btn in self.category_buttons.items():
            icon = cat_icons.get(cat, "📌")
            if cat == "All":
                suffix = f" ({total})" if total > 0 else ""
                btn.configure(text=f"  {icon}  All{suffix}")
            else:
                n = counts.get(cat, 0)
                suffix = f" ({n})" if n > 0 else ""
                btn.configure(text=f"  {icon}  {cat}{suffix}")

    # ------------------------------------------------------------------
    # Entry List
    # ------------------------------------------------------------------

    def _refresh_entries(self, search_query: str = ""):
        C = get_colors()

        for widget in self.list_frame.winfo_children():
            widget.destroy()

        all_entries = self.db.get_all_entries()
        self._update_category_counts(all_entries)

        if search_query:
            entries = self.db.search_entries(search_query)
        else:
            entries = all_entries

        if self.active_category != "All":
            entries = [e for e in entries if e.get("category", "General") == self.active_category]

        if not entries:
            self._show_empty_state(search_query)
            self.header_subtitle.configure(text="No entries found" if search_query else "")
            return

        total = len(all_entries)
        self.header_subtitle.configure(
            text=f"{len(entries)} {'entry' if len(entries) == 1 else 'entries'}"
            + (f" of {total}" if len(entries) != total else "")
        )

        for i, entry in enumerate(entries):
            self._create_entry_card(entry, i)

    def _show_empty_state(self, search_query: str):
        C = get_colors()
        empty = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        empty.grid(row=0, column=0, sticky="ew", pady=60)
        empty.grid_columnconfigure(0, weight=1)

        icon, msg = ("🔍", f'No results for "{search_query}"') if search_query else ("🛡", "No entries yet.\nClick '＋ New Entry' to get started.")

        ctk.CTkLabel(empty, text=icon, font=ctk.CTkFont(size=44)).grid(row=0, column=0, pady=(0, 10))
        ctk.CTkLabel(empty, text=msg, font=ctk.CTkFont(size=14), text_color=C["text_secondary"], justify="center").grid(row=1, column=0)

    def _create_entry_card(self, entry: dict, index: int):
        C = get_colors()

        card = ctk.CTkFrame(
            self.list_frame, fg_color=C["bg_card"],
            corner_radius=12, border_width=1,
            border_color=C["border_subtle"],
        )
        card.grid(row=index, column=0, sticky="ew", pady=(0, 6))
        card.grid_columnconfigure(1, weight=1)

        # -- Site Avatar --
        avatar_color = get_avatar_color(entry["site_name"])
        site_icon = get_site_icon(entry["site_name"], entry.get("category", "General"))

        avatar = ctk.CTkFrame(card, width=44, height=44, corner_radius=10, fg_color=avatar_color)
        avatar.grid(row=0, column=0, padx=(14, 10), pady=14)
        avatar.grid_propagate(False)
        ctk.CTkLabel(avatar, text=site_icon, font=ctk.CTkFont(size=18)).place(relx=0.5, rely=0.5, anchor="center")

        # -- Info Column (packed vertically) --
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=1, sticky="nsew", pady=10)

        # Site name + category badge
        name_row = ctk.CTkFrame(info, fg_color="transparent")
        name_row.pack(fill="x")

        ctk.CTkLabel(
            name_row, text=entry["site_name"],
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C["text_primary"], anchor="w",
        ).pack(side="left")

        if entry.get("category") and entry["category"] != "General":
            ctk.CTkLabel(
                name_row, text=entry["category"],
                font=ctk.CTkFont(size=10),
                text_color=C["text_muted"],
                fg_color=C["bg_input"],
                corner_radius=4, padx=6, pady=1,
            ).pack(side="left", padx=(8, 0))

        # Username
        ctk.CTkLabel(
            info, text=entry["username"],
            font=ctk.CTkFont(size=12),
            text_color=C["text_secondary"], anchor="w",
        ).pack(fill="x")

        # Password reveal row (hidden by default)
        pw_visible = [False]
        pw_row = ctk.CTkFrame(info, fg_color="transparent")
        ctk.CTkLabel(
            pw_row, text=entry["password"],
            font=ctk.CTkFont(family="Courier", size=11),
            text_color=C["text_muted"], anchor="w",
        ).pack(side="left")

        # Age
        age = _format_age(entry.get("updated_at", ""))
        if age:
            ctk.CTkLabel(
                info, text=f"Updated {age}",
                font=ctk.CTkFont(size=10),
                text_color=C["text_muted"], anchor="w",
            ).pack(fill="x")

        # -- Action Buttons --
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=(8, 14), pady=14)

        copy_btn = ctk.CTkButton(
            btn_frame, text="Copy",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=64, height=30,
            fg_color=C["copy_btn"], hover_color=C["copy_btn_hover"],
            text_color="#ffffff", corner_radius=8,
            command=lambda e=entry: self._copy_password(e, copy_btn),
        )
        copy_btn.pack(pady=(0, 4))

        mini_frame = ctk.CTkFrame(btn_frame, fg_color="transparent")
        mini_frame.pack()

        # Reveal password toggle
        eye_btn = ctk.CTkButton(
            mini_frame, text="👁", width=28, height=28,
            font=ctk.CTkFont(size=12),
            fg_color="transparent", hover_color=C["bg_hover"],
            text_color=C["text_secondary"], corner_radius=6,
        )
        eye_btn.configure(command=lambda: self._toggle_pw_reveal(pw_visible, pw_row, eye_btn))
        eye_btn.pack(side="left", padx=(0, 2))

        # Edit
        ctk.CTkButton(
            mini_frame, text="✎", width=28, height=28,
            font=ctk.CTkFont(size=13),
            fg_color="transparent", hover_color=C["bg_hover"],
            text_color=C["text_secondary"], corner_radius=6,
            command=lambda e=entry: self._show_edit_form(e),
        ).pack(side="left", padx=(0, 2))

        # Delete
        ctk.CTkButton(
            mini_frame, text="🗑", width=28, height=28,
            font=ctk.CTkFont(size=13),
            fg_color="transparent", hover_color=C["bg_hover"],
            text_color=C["delete_btn"], corner_radius=6,
            command=lambda e=entry: self._confirm_delete(e),
        ).pack(side="left", padx=(0, 2))

        # Open URL (only if URL is set)
        if entry.get("url"):
            ctk.CTkButton(
                mini_frame, text="↗", width=28, height=28,
                font=ctk.CTkFont(size=13),
                fg_color="transparent", hover_color=C["bg_hover"],
                text_color=C["text_secondary"], corner_radius=6,
                command=lambda url=entry["url"]: webbrowser.open(url),
            ).pack(side="left")

    def _toggle_pw_reveal(self, pw_visible: list, pw_row: ctk.CTkFrame, btn: ctk.CTkButton):
        pw_visible[0] = not pw_visible[0]
        if pw_visible[0]:
            pw_row.pack(fill="x")
            btn.configure(text="🙈")
        else:
            pw_row.pack_forget()
            btn.configure(text="👁")

    # ------------------------------------------------------------------
    # Clipboard
    # ------------------------------------------------------------------

    def _copy_password(self, entry: dict, btn: ctk.CTkButton):
        C = get_colors()
        self.clipboard_clear()
        self.clipboard_append(entry["password"])
        self.update()

        btn.configure(text="✓", fg_color=C["success"])
        btn.after(1500, lambda: btn.configure(text="Copy", fg_color=C["copy_btn"]))

        if self.clipboard_clear_job:
            self.after_cancel(self.clipboard_clear_job)
        self.clipboard_clear_job = self.after(15000, self._clear_clipboard)

    def _clear_clipboard(self):
        try:
            self.clipboard_clear()
            self.clipboard_append("")
            self.update()
        except Exception:
            pass
        self.clipboard_clear_job = None

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _on_search(self, event=None):
        query = self.search_entry.get().strip()
        self._refresh_entries(search_query=query)

    def _clear_search(self):
        self.search_entry.delete(0, "end")
        self._refresh_entries()

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------

    def _show_add_form(self):
        EntryFormDialog(parent=self, title="New Entry", on_save=self._save_new_entry)

    def _save_new_entry(self, data: dict):
        self.db.add_entry(
            site_name=data["site_name"], username=data["username"],
            password=data["password"], url=data.get("url", ""),
            notes=data.get("notes", ""), category=data.get("category", "General"),
        )
        self._refresh_entries()

    def _show_edit_form(self, entry: dict):
        EntryFormDialog(
            parent=self, title="Edit Entry",
            on_save=lambda data: self._save_edit(entry["id"], data),
            existing=entry,
        )

    def _save_edit(self, entry_id: int, data: dict):
        self.db.update_entry(
            entry_id=entry_id, site_name=data["site_name"],
            username=data["username"], password=data["password"],
            url=data.get("url", ""), notes=data.get("notes", ""),
            category=data.get("category", "General"),
        )
        self._refresh_entries()

    def _confirm_delete(self, entry: dict):
        DeleteConfirmDialog(
            parent=self, entry_name=entry["site_name"],
            on_confirm=lambda: self._delete_entry(entry),
        )

    def _delete_entry(self, entry: dict):
        self.db.delete_entry(entry["id"])
        self._refresh_entries()

    # ------------------------------------------------------------------
    # Theme Toggle
    # ------------------------------------------------------------------

    def _toggle_theme(self):
        new_mode = toggle_mode()
        ctk.set_appearance_mode(new_mode)
        if self.on_theme_change:
            self.on_theme_change()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _show_settings(self):
        SettingsDialog(
            parent=self,
            db=self.db,
            auto_lock_minutes=self._auto_lock_minutes,
            on_auto_lock_change=self.set_auto_lock,
        )

    # ------------------------------------------------------------------
    # Lock
    # ------------------------------------------------------------------

    def _lock_vault(self):
        if self._auto_lock_job:
            self.after_cancel(self._auto_lock_job)
            self._auto_lock_job = None

        if self.clipboard_clear_job:
            self.after_cancel(self.clipboard_clear_job)
            self._clear_clipboard()

        top = self.winfo_toplevel()
        for shortcut in ("<Control-n>", "<Control-f>", "<Control-l>", "<Escape>"):
            top.unbind(shortcut)

        self.db.lock()
        self.on_lock()


# ======================================================================
# Entry Form Dialog
# ======================================================================

class EntryFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, on_save: Callable[[dict], None], existing: Optional[dict] = None):
        super().__init__(parent)
        C = get_colors()
        self.on_save = on_save
        self.existing = existing
        self.password_visible = False

        self.title(title)
        self.geometry("460x680")
        self.minsize(400, 620)
        self.configure(fg_color=C["bg_primary"])
        self.resizable(False, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        if existing:
            self._populate(existing)

    def _build_ui(self):
        C = get_colors()

        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=20)

        # Site Name
        self._add_label(container, "Site / Service *")
        self.site_entry = self._add_entry(container, "e.g. GitHub, Gmail, Netflix")

        # URL
        self._add_label(container, "URL")
        self.url_entry = self._add_entry(container, "https://example.com")

        # Username
        self._add_label(container, "Username / Email *")
        self.username_entry = self._add_entry(container, "your@email.com")

        # Password
        self._add_label(container, "Password *")
        pw_frame = ctk.CTkFrame(container, fg_color="transparent")
        pw_frame.pack(fill="x", pady=(0, 4))

        self.password_entry = ctk.CTkEntry(
            pw_frame, placeholder_text="Enter or generate", show="•",
            font=ctk.CTkFont(size=13), height=40,
            fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], corner_radius=10,
        )
        self.password_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.toggle_btn = ctk.CTkButton(
            pw_frame, text="👁", width=40, height=40,
            fg_color=C["bg_input"], hover_color=C["bg_hover"],
            corner_radius=10, command=self._toggle_password,
        )
        self.toggle_btn.pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            pw_frame, text="⚡", width=40, height=40,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            corner_radius=10, command=self._open_generator,
        ).pack(side="left")

        # Strength
        self.pw_strength = ctk.CTkLabel(
            container, text="", font=ctk.CTkFont(size=11),
            text_color=C["text_muted"], anchor="w",
        )
        self.pw_strength.pack(fill="x", pady=(0, 8))
        self.password_entry.bind("<KeyRelease>", self._update_strength)

        # Category
        self._add_label(container, "Category")
        self.category_menu = ctk.CTkOptionMenu(
            container,
            values=["General", "Social", "Work", "Finance", "Shopping", "Education", "Other"],
            font=ctk.CTkFont(size=12), height=38,
            fg_color=C["bg_input"], button_color=C["border"],
            button_hover_color=C["text_muted"],
            dropdown_fg_color=C["bg_card"],
            dropdown_hover_color=C["bg_hover"],
            text_color=C["text_primary"],
            corner_radius=10,
        )
        self.category_menu.set("General")
        self.category_menu.pack(fill="x", pady=(0, 12))

        # Notes
        self._add_label(container, "Notes")
        self.notes_entry = ctk.CTkTextbox(
            container, font=ctk.CTkFont(size=12), height=60,
            fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], border_width=1,
            corner_radius=10,
        )
        self.notes_entry.pack(fill="x", pady=(0, 12))

        # Error
        self.error_label = ctk.CTkLabel(
            container, text="", font=ctk.CTkFont(size=12),
            text_color=C["error"],
        )
        self.error_label.pack(fill="x", pady=(0, 4))

        # Buttons
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame, text="Cancel", font=ctk.CTkFont(size=13),
            height=42, fg_color=C["bg_secondary"],
            hover_color=C["bg_hover"],
            border_width=1, border_color=C["border"],
            text_color=C["text_primary"], corner_radius=10,
            command=self.destroy,
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            btn_frame, text="Save", font=ctk.CTkFont(size=13, weight="bold"),
            height=42, fg_color=C["accent"],
            hover_color=C["accent_hover"], corner_radius=10,
            command=self._save,
        ).pack(side="right", fill="x", expand=True)

        self.site_entry.focus_set()

    def _add_label(self, parent, text):
        C = get_colors()
        ctk.CTkLabel(
            parent, text=text, font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["text_secondary"],
        ).pack(anchor="w", pady=(0, 4))

    def _add_entry(self, parent, placeholder):
        C = get_colors()
        entry = ctk.CTkEntry(
            parent, placeholder_text=placeholder,
            font=ctk.CTkFont(size=13), height=40,
            fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], corner_radius=10,
        )
        entry.pack(fill="x", pady=(0, 12))
        return entry

    def _populate(self, entry):
        self.site_entry.insert(0, entry.get("site_name", ""))
        self.url_entry.insert(0, entry.get("url", ""))
        self.username_entry.insert(0, entry.get("username", ""))
        self.password_entry.insert(0, entry.get("password", ""))
        self.category_menu.set(entry.get("category", "General"))
        if entry.get("notes"):
            self.notes_entry.insert("1.0", entry["notes"])
        self._update_strength()

    def _toggle_password(self):
        self.password_visible = not self.password_visible
        self.password_entry.configure(show="" if self.password_visible else "•")
        self.toggle_btn.configure(text="🙈" if self.password_visible else "👁")

    def _update_strength(self, event=None):
        C = get_colors()
        pw = self.password_entry.get()
        if not pw:
            self.pw_strength.configure(text="", text_color=C["text_muted"])
            return
        result = estimate_strength(pw)
        color = get_strength_color(result["strength"])
        self.pw_strength.configure(
            text=f"{result['strength']}  ·  {result['entropy_bits']} bits",
            text_color=color,
        )

    def _open_generator(self):
        PasswordGeneratorDialog(parent=self, on_accept=self._use_generated)

    def _use_generated(self, password):
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, password)
        self._update_strength()

    def _save(self):
        site = self.site_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not site:
            self.error_label.configure(text="Site name is required.")
            return
        if not username:
            self.error_label.configure(text="Username is required.")
            return
        if not password:
            self.error_label.configure(text="Password is required.")
            return

        self.on_save({
            "site_name": site,
            "username": username,
            "password": password,
            "url": self.url_entry.get().strip(),
            "notes": self.notes_entry.get("1.0", "end-1c").strip(),
            "category": self.category_menu.get(),
        })
        self.destroy()


# ======================================================================
# Delete Confirmation
# ======================================================================

class DeleteConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, entry_name: str, on_confirm: Callable):
        super().__init__(parent)
        C = get_colors()
        self.on_confirm = on_confirm

        self.title("Confirm Delete")
        self.geometry("380x200")
        self.configure(fg_color=C["bg_primary"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(
            container, text="Delete Entry?",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=C["text_primary"],
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            container,
            text=f'Are you sure you want to delete "{entry_name}"?\nThis cannot be undone.',
            font=ctk.CTkFont(size=12),
            text_color=C["text_secondary"], justify="center",
        ).pack(pady=(0, 16))

        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame, text="Cancel", font=ctk.CTkFont(size=13),
            height=38, fg_color=C["bg_secondary"],
            hover_color=C["bg_hover"],
            border_width=1, border_color=C["border"],
            text_color=C["text_primary"], corner_radius=10,
            command=self.destroy,
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            btn_frame, text="Delete", font=ctk.CTkFont(size=13, weight="bold"),
            height=38, fg_color=C["delete_btn"],
            hover_color=C["delete_btn_hover"],
            corner_radius=10,
            command=lambda: (self.on_confirm(), self.destroy()),
        ).pack(side="right", fill="x", expand=True)


# ======================================================================
# Settings Dialog
# ======================================================================

class SettingsDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        db: VaultDatabase,
        auto_lock_minutes: int = 0,
        on_auto_lock_change: Callable = None,
    ):
        super().__init__(parent)
        C = get_colors()
        self.parent_ref = parent
        self.db = db
        self._on_auto_lock_change = on_auto_lock_change
        self._auto_lock_minutes = auto_lock_minutes

        self.title("Settings")
        self.geometry("460x560")
        self.configure(fg_color=C["bg_primary"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        C = get_colors()
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(
            container, text="Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=C["text_primary"],
        ).pack(anchor="w", pady=(0, 16))

        # -- Vault info --
        info_card = ctk.CTkFrame(
            container, fg_color=C["bg_card"], corner_radius=12,
            border_width=1, border_color=C["border"],
        )
        info_card.pack(fill="x", pady=(0, 12))
        info_inner = ctk.CTkFrame(info_card, fg_color="transparent")
        info_inner.pack(padx=16, pady=14, fill="x")

        try:
            count = self.db.get_entry_count()
        except Exception:
            count = "?"

        ctk.CTkLabel(
            info_inner,
            text=f"Vault contains {count} {'entry' if count == 1 else 'entries'}",
            font=ctk.CTkFont(size=13), text_color=C["text_secondary"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            info_inner, text="Stored locally in vault.db (encrypted)",
            font=ctk.CTkFont(size=11), text_color=C["text_muted"],
        ).pack(anchor="w", pady=(2, 0))

        # -- Change password --
        ctk.CTkButton(
            container, text="🔑  Change Master Password",
            font=ctk.CTkFont(size=13), height=42,
            fg_color=C["bg_card"], hover_color=C["bg_hover"],
            border_width=1, border_color=C["border"],
            text_color=C["text_primary"], anchor="w",
            corner_radius=10,
            command=self._change_password,
        ).pack(fill="x", pady=(0, 12))

        # -- Auto-lock --
        lock_card = ctk.CTkFrame(
            container, fg_color=C["bg_card"], corner_radius=12,
            border_width=1, border_color=C["border"],
        )
        lock_card.pack(fill="x", pady=(0, 12))
        lock_inner = ctk.CTkFrame(lock_card, fg_color="transparent")
        lock_inner.pack(padx=16, pady=12, fill="x")

        ctk.CTkLabel(
            lock_inner, text="🔒  Auto-lock after inactivity",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["text_secondary"],
        ).pack(anchor="w", pady=(0, 8))

        minutes_map = {"Off": 0, "5 min": 5, "10 min": 10, "30 min": 30, "1 hour": 60}
        reverse_map = {v: k for k, v in minutes_map.items()}
        current_label = reverse_map.get(self._auto_lock_minutes, "Off")

        self.lock_menu = ctk.CTkOptionMenu(
            lock_inner,
            values=list(minutes_map.keys()),
            font=ctk.CTkFont(size=12), height=34,
            fg_color=C["bg_input"], button_color=C["border"],
            button_hover_color=C["text_muted"],
            dropdown_fg_color=C["bg_card"],
            dropdown_hover_color=C["bg_hover"],
            text_color=C["text_primary"],
            corner_radius=8,
            command=lambda val: self._apply_auto_lock(val, minutes_map),
        )
        self.lock_menu.set(current_label)
        self.lock_menu.pack(fill="x")

        # -- Export / Import --
        data_card = ctk.CTkFrame(
            container, fg_color=C["bg_card"], corner_radius=12,
            border_width=1, border_color=C["border"],
        )
        data_card.pack(fill="x", pady=(0, 12))
        data_inner = ctk.CTkFrame(data_card, fg_color="transparent")
        data_inner.pack(padx=16, pady=12, fill="x")

        ctk.CTkLabel(
            data_inner, text="Data",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["text_secondary"],
        ).pack(anchor="w", pady=(0, 6))

        ctk.CTkLabel(
            data_inner,
            text="CSV export is plaintext — keep the file secure.",
            font=ctk.CTkFont(size=10),
            text_color=C["text_muted"],
        ).pack(anchor="w", pady=(0, 8))

        self.data_status = ctk.CTkLabel(
            data_inner, text="",
            font=ctk.CTkFont(size=11),
            text_color=C["text_muted"],
        )
        self.data_status.pack(anchor="w", pady=(0, 6))

        btn_row = ctk.CTkFrame(data_inner, fg_color="transparent")
        btn_row.pack(fill="x")

        ctk.CTkButton(
            btn_row, text="⬆  Export CSV",
            font=ctk.CTkFont(size=12), height=34,
            fg_color="transparent", hover_color=C["bg_hover"],
            border_width=1, border_color=C["border"],
            text_color=C["text_primary"], corner_radius=8,
            command=self._export_csv,
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="⬇  Import CSV",
            font=ctk.CTkFont(size=12), height=34,
            fg_color="transparent", hover_color=C["bg_hover"],
            border_width=1, border_color=C["border"],
            text_color=C["text_primary"], corner_radius=8,
            command=self._import_csv,
        ).pack(side="right", fill="x", expand=True)

        # -- Shortcuts --
        sc_card = ctk.CTkFrame(
            container, fg_color=C["bg_card"], corner_radius=12,
            border_width=1, border_color=C["border"],
        )
        sc_card.pack(fill="x")
        sc_inner = ctk.CTkFrame(sc_card, fg_color="transparent")
        sc_inner.pack(padx=16, pady=12, fill="x")

        ctk.CTkLabel(
            sc_inner, text="Keyboard Shortcuts",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["text_secondary"],
        ).pack(anchor="w", pady=(0, 6))

        for key, desc in [
            ("Ctrl+N", "New entry"),
            ("Ctrl+F", "Search"),
            ("Ctrl+L", "Lock vault"),
            ("Esc", "Clear search"),
        ]:
            row = ctk.CTkFrame(sc_inner, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(
                row, text=key, font=ctk.CTkFont(family="Courier", size=11),
                text_color=C["accent"], width=70, anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=desc, font=ctk.CTkFont(size=11),
                text_color=C["text_muted"],
            ).pack(side="left")

    def _apply_auto_lock(self, label: str, minutes_map: dict):
        minutes = minutes_map.get(label, 0)
        if self._on_auto_lock_change:
            self._on_auto_lock_change(minutes)

    def _export_csv(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Vault to CSV",
            initialfile="vault_export.csv",
        )
        if not filepath:
            return
        try:
            count = self.db.export_to_csv(filepath)
            self.data_status.configure(
                text=f"✓ Exported {count} {'entry' if count == 1 else 'entries'}",
                text_color=get_colors()["success"],
            )
        except Exception as e:
            self.data_status.configure(text=f"Export failed: {e}", text_color=get_colors()["error"])

    def _import_csv(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Import from CSV",
        )
        if not filepath:
            return
        try:
            imported, skipped = self.db.import_from_csv(filepath)
            msg = f"✓ Imported {imported} {'entry' if imported == 1 else 'entries'}"
            if skipped:
                msg += f", {skipped} skipped"
            self.data_status.configure(text=msg, text_color=get_colors()["success"])
            if hasattr(self.parent_ref, "_refresh_entries"):
                self.parent_ref._refresh_entries()
        except Exception as e:
            self.data_status.configure(text=f"Import failed: {e}", text_color=get_colors()["error"])

    def _change_password(self):
        self.destroy()
        ChangePasswordDialog(parent=self.parent_ref, db=self.db)


# ======================================================================
# Change Password Dialog
# ======================================================================

class ChangePasswordDialog(ctk.CTkToplevel):
    def __init__(self, parent, db: VaultDatabase):
        super().__init__(parent)
        C = get_colors()
        self.db = db

        self.title("Change Master Password")
        self.geometry("440x400")
        self.configure(fg_color=C["bg_primary"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        C = get_colors()
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(
            container, text="Change Master Password",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=C["text_primary"],
        ).pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(
            container, text="All entries will be re-encrypted with the new password.",
            font=ctk.CTkFont(size=12), text_color=C["text_secondary"],
        ).pack(anchor="w", pady=(0, 16))

        for label_text, attr_name in [
            ("Current Password", "current_entry"),
            ("New Password", "new_entry"),
            ("Confirm New Password", "confirm_entry"),
        ]:
            ctk.CTkLabel(
                container, text=label_text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=C["text_secondary"],
            ).pack(anchor="w", pady=(0, 4))

            entry = ctk.CTkEntry(
                container, show="•", font=ctk.CTkFont(size=13),
                height=40, fg_color=C["bg_input"],
                border_color=C["border"], text_color=C["text_primary"],
                corner_radius=10,
            )
            entry.pack(fill="x", pady=(0, 12))
            setattr(self, attr_name, entry)

        self.status_label = ctk.CTkLabel(
            container, text="", font=ctk.CTkFont(size=12),
            text_color=C["error"],
        )
        self.status_label.pack(fill="x", pady=(0, 8))

        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame, text="Cancel", font=ctk.CTkFont(size=13),
            height=40, fg_color=C["bg_secondary"],
            hover_color=C["bg_hover"],
            border_width=1, border_color=C["border"],
            text_color=C["text_primary"], corner_radius=10,
            command=self.destroy,
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.save_btn = ctk.CTkButton(
            btn_frame, text="Change Password",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40, fg_color=C["accent"],
            hover_color=C["accent_hover"], corner_radius=10,
            command=self._submit,
        )
        self.save_btn.pack(side="right", fill="x", expand=True)

        self.current_entry.focus_set()

    def _submit(self):
        C = get_colors()
        current = self.current_entry.get().strip()
        new = self.new_entry.get().strip()
        confirm = self.confirm_entry.get().strip()

        if not current or not new or not confirm:
            self.status_label.configure(text="All fields are required.")
            return
        if new != confirm:
            self.status_label.configure(text="New passwords don't match.")
            return
        if len(new) < 8:
            self.status_label.configure(text="Must be at least 8 characters.")
            return
        if current == new:
            self.status_label.configure(text="New password must be different.")
            return

        strength = estimate_strength(new)
        if strength["entropy_bits"] < 36:
            self.status_label.configure(text="New password is too weak.")
            return

        try:
            self.save_btn.configure(state="disabled", text="Changing...")
            self.update_idletasks()

            if self.db.change_master_password(current, new):
                self.status_label.configure(text="Password changed!", text_color=C["success"])
                self.after(1500, self.destroy)
            else:
                self.save_btn.configure(state="normal", text="Change Password")
                self.status_label.configure(text="Current password is incorrect.")
                self.current_entry.delete(0, "end")
                self.current_entry.focus_set()
        except Exception as e:
            self.save_btn.configure(state="normal", text="Change Password")
            self.status_label.configure(text=f"Error: {e}")
