"""
main_window.py - The main vault interface.

This is where users spend most of their time. It shows:
- A search bar at the top
- A scrollable list of saved credentials
- Add/Edit/Delete functionality
- One-click copy to clipboard
- Password generator integration
- Lock vault button

Layout:
┌──────────────────────────────┐
│  🔒 Vault    [+ Add] [Lock] │
│  [🔍 Search...             ] │
├──────────────────────────────┤
│  ┌────────────────────────┐  │
│  │ GitHub        ✎  🗑   │  │
│  │ sammy@email   [Copy]   │  │
│  ├────────────────────────┤  │
│  │ Gmail         ✎  🗑   │  │
│  │ sammy@gmail   [Copy]   │  │
│  └────────────────────────┘  │
│                              │
│  3 entries in vault          │
└──────────────────────────────┘
"""

import customtkinter as ctk
from typing import Callable, Optional

from core.database import VaultDatabase
from core.password_gen import estimate_strength
from gui.generator import PasswordGeneratorDialog

# Same color palette
COLORS = {
    "bg_dark": "#1a1a2e",
    "bg_card": "#16213e",
    "bg_input": "#0f3460",
    "bg_entry_hover": "#1a2744",
    "accent": "#e94560",
    "accent_hover": "#c73652",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0b8",
    "text_muted": "#6c6c80",
    "success": "#4ecca3",
    "error": "#e94560",
    "warning": "#f0c808",
    "border": "#2a2a4a",
    "copy_btn": "#4ecca3",
    "copy_btn_hover": "#3db890",
    "edit_btn": "#f0c808",
    "edit_btn_hover": "#d4b107",
    "delete_btn": "#e94560",
    "delete_btn_hover": "#c73652",
}

STRENGTH_COLORS = {
    "Very Weak": COLORS["error"],
    "Weak": "#ff6b35",
    "Moderate": COLORS["warning"],
    "Strong": COLORS["success"],
    "Very Strong": "#00b894",
}


class MainWindow(ctk.CTkFrame):
    """
    Main vault view showing all saved credentials.
    
    Args:
        parent: Parent widget (main app window)
        db: Unlocked VaultDatabase instance
        on_lock: Callback when user locks the vault
    """

    def __init__(self, parent: ctk.CTk, db: VaultDatabase, on_lock: Callable):
        super().__init__(parent, fg_color=COLORS["bg_dark"])
        self.db = db
        self.on_lock = on_lock
        self.clipboard_clear_job = None

        self._build_ui()
        self._refresh_entries()
        self._bind_shortcuts()

    def _bind_shortcuts(self):
        """Set up keyboard shortcuts for power users."""
        # Get the top-level window for global bindings
        top = self.winfo_toplevel()
        top.bind("<Control-n>", lambda e: self._show_add_form())
        top.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        top.bind("<Control-l>", lambda e: self._lock_vault())
        top.bind("<Escape>", lambda e: self._clear_search())

    def _build_ui(self):
        """Build the main vault interface."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Entry list gets all extra space

        # --- Top Bar ---
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        top_bar.grid_columnconfigure(1, weight=1)

        # Title
        title_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            title_frame,
            text="🔐",
            font=ctk.CTkFont(size=24),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            title_frame,
            text="Vault",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        # Action buttons
        btn_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_frame.grid(row=0, column=2, sticky="e")

        self.add_btn = ctk.CTkButton(
            btn_frame,
            text="+ Add",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=80,
            height=36,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._show_add_form,
        )
        self.add_btn.pack(side="left", padx=(0, 6))

        self.settings_btn = ctk.CTkButton(
            btn_frame,
            text="⚙",
            font=ctk.CTkFont(size=16),
            width=36,
            height=36,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            command=self._show_settings,
        )
        self.settings_btn.pack(side="left", padx=(0, 6))

        self.lock_btn = ctk.CTkButton(
            btn_frame,
            text="🔒 Lock",
            font=ctk.CTkFont(size=13),
            width=80,
            height=36,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            command=self._lock_vault,
        )
        self.lock_btn.pack(side="left")

        # --- Search Bar ---
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍  Search entries...",
            font=ctk.CTkFont(size=13),
            height=38,
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            placeholder_text_color=COLORS["text_muted"],
        )
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<KeyRelease>", self._on_search)

        # --- Entry List (scrollable) ---
        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["text_muted"],
        )
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 8))
        self.list_frame.grid_columnconfigure(0, weight=1)

        # --- Status Bar ---
        self.status_bar = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.status_bar.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 12))

    # ------------------------------------------------------------------
    # Entry List
    # ------------------------------------------------------------------

    def _refresh_entries(self, search_query: str = ""):
        """Reload and display entries from the database."""
        # Clear existing entries
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        # Fetch entries
        if search_query:
            entries = self.db.search_entries(search_query)
        else:
            entries = self.db.get_all_entries()

        if not entries:
            self._show_empty_state(search_query)
            self.status_bar.configure(text="No entries found" if search_query else "Vault is empty")
            return

        # Render each entry as a card
        for i, entry in enumerate(entries):
            self._create_entry_card(entry, i)

        # Update status
        total = self.db.get_entry_count()
        if search_query:
            self.status_bar.configure(text=f"Showing {len(entries)} of {total} entries")
        else:
            self.status_bar.configure(text=f"{total} {'entry' if total == 1 else 'entries'} in vault")

    def _show_empty_state(self, search_query: str):
        """Show a friendly message when there are no entries."""
        empty_frame = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        empty_frame.grid(row=0, column=0, sticky="ew", pady=40)
        empty_frame.grid_columnconfigure(0, weight=1)

        if search_query:
            icon = "🔍"
            message = f'No entries matching "{search_query}"'
        else:
            icon = "🔐"
            message = "Your vault is empty.\nClick '+ Add' to store your first password."

        ctk.CTkLabel(
            empty_frame,
            text=icon,
            font=ctk.CTkFont(size=40),
        ).grid(row=0, column=0, pady=(0, 8))

        ctk.CTkLabel(
            empty_frame,
            text=message,
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"],
            justify="center",
        ).grid(row=1, column=0)

    def _create_entry_card(self, entry: dict, index: int):
        """Create a single entry card in the list."""
        card = ctk.CTkFrame(
            self.list_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.grid(row=index, column=0, sticky="ew", pady=(0, 6))
        card.grid_columnconfigure(1, weight=1)

        # Left section: site info
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(12, 0))
        info_frame.grid_columnconfigure(0, weight=1)

        # Site name + category badge
        name_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        name_row.pack(fill="x")

        ctk.CTkLabel(
            name_row,
            text=entry["site_name"],
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(side="left")

        if entry.get("category") and entry["category"] != "General":
            ctk.CTkLabel(
                name_row,
                text=entry["category"],
                font=ctk.CTkFont(size=10),
                text_color=COLORS["text_muted"],
                fg_color=COLORS["bg_input"],
                corner_radius=4,
                padx=6,
                pady=1,
            ).pack(side="left", padx=(8, 0))

        # Username
        ctk.CTkLabel(
            info_frame,
            text=entry["username"],
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).pack(fill="x")

        # URL (if present)
        if entry.get("url"):
            ctk.CTkLabel(
                info_frame,
                text=entry["url"],
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_muted"],
                anchor="w",
            ).pack(fill="x")

        # Action buttons row
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(8, 12))

        # Copy password button
        copy_btn = ctk.CTkButton(
            btn_row,
            text="📋 Copy Password",
            font=ctk.CTkFont(size=11),
            width=120,
            height=30,
            fg_color=COLORS["copy_btn"],
            hover_color=COLORS["copy_btn_hover"],
            text_color=COLORS["bg_dark"],
            command=lambda e=entry: self._copy_password(e, copy_btn),
        )
        copy_btn.pack(side="left", padx=(0, 6))

        # Copy username button
        copy_user_btn = ctk.CTkButton(
            btn_row,
            text="👤 Copy User",
            font=ctk.CTkFont(size=11),
            width=100,
            height=30,
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            command=lambda e=entry: self._copy_username(e, copy_user_btn),
        )
        copy_user_btn.pack(side="left", padx=(0, 6))

        # Spacer
        spacer = ctk.CTkFrame(btn_row, fg_color="transparent")
        spacer.pack(side="left", fill="x", expand=True)

        # Edit button
        edit_btn = ctk.CTkButton(
            btn_row,
            text="✎",
            font=ctk.CTkFont(size=14),
            width=32,
            height=30,
            fg_color="transparent",
            hover_color=COLORS["border"],
            text_color=COLORS["edit_btn"],
            command=lambda e=entry: self._show_edit_form(e),
        )
        edit_btn.pack(side="left", padx=(0, 2))

        # Delete button
        del_btn = ctk.CTkButton(
            btn_row,
            text="🗑",
            font=ctk.CTkFont(size=14),
            width=32,
            height=30,
            fg_color="transparent",
            hover_color=COLORS["border"],
            text_color=COLORS["delete_btn"],
            command=lambda e=entry: self._confirm_delete(e),
        )
        del_btn.pack(side="left")

    # ------------------------------------------------------------------
    # Clipboard Operations
    # ------------------------------------------------------------------

    def _copy_password(self, entry: dict, btn: ctk.CTkButton):
        """Copy password to clipboard with auto-clear after 15 seconds."""
        self._copy_to_clipboard(entry["password"])

        # Visual feedback
        original_text = btn.cget("text")
        btn.configure(text="✓ Copied!", fg_color=COLORS["success"])
        btn.after(1500, lambda: btn.configure(text=original_text, fg_color=COLORS["copy_btn"]))

        self.status_bar.configure(
            text="Password copied! Clipboard will clear in 15 seconds.",
            text_color=COLORS["success"],
        )

        # Auto-clear clipboard after 15 seconds
        if self.clipboard_clear_job:
            self.after_cancel(self.clipboard_clear_job)
        self.clipboard_clear_job = self.after(15000, self._clear_clipboard)

    def _copy_username(self, entry: dict, btn: ctk.CTkButton):
        """Copy username to clipboard."""
        self._copy_to_clipboard(entry["username"])

        original_text = btn.cget("text")
        btn.configure(text="✓ Copied!")
        btn.after(1500, lambda: btn.configure(text=original_text))

        self.status_bar.configure(
            text="Username copied to clipboard.",
            text_color=COLORS["text_muted"],
        )

    def _copy_to_clipboard(self, text: str):
        """Copy text to system clipboard using tkinter's built-in method."""
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()  # Required for clipboard to actually update

    def _clear_clipboard(self):
        """Clear the clipboard for security."""
        try:
            self.clipboard_clear()
            self.clipboard_append("")
            self.update()
            self.status_bar.configure(
                text="Clipboard cleared.",
                text_color=COLORS["text_muted"],
            )
        except Exception:
            pass  # Window might be closed
        self.clipboard_clear_job = None

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _on_search(self, event=None):
        """Filter entries as user types in search box."""
        query = self.search_entry.get().strip()
        self._refresh_entries(search_query=query)

    # ------------------------------------------------------------------
    # Add Entry Form
    # ------------------------------------------------------------------

    def _show_add_form(self):
        """Show the add entry dialog."""
        EntryFormDialog(
            parent=self,
            title="Add New Entry",
            on_save=self._save_new_entry,
        )

    def _save_new_entry(self, data: dict):
        """Save a new entry to the vault."""
        try:
            self.db.add_entry(
                site_name=data["site_name"],
                username=data["username"],
                password=data["password"],
                url=data.get("url", ""),
                notes=data.get("notes", ""),
                category=data.get("category", "General"),
            )
            self._refresh_entries()
            self.status_bar.configure(
                text=f"Added '{data['site_name']}' to vault.",
                text_color=COLORS["success"],
            )
        except Exception as e:
            self.status_bar.configure(
                text=f"Error saving entry: {e}",
                text_color=COLORS["error"],
            )

    # ------------------------------------------------------------------
    # Edit Entry Form
    # ------------------------------------------------------------------

    def _show_edit_form(self, entry: dict):
        """Show the edit entry dialog."""
        EntryFormDialog(
            parent=self,
            title="Edit Entry",
            on_save=lambda data: self._save_edited_entry(entry["id"], data),
            existing=entry,
        )

    def _save_edited_entry(self, entry_id: int, data: dict):
        """Save changes to an existing entry."""
        try:
            self.db.update_entry(
                entry_id=entry_id,
                site_name=data["site_name"],
                username=data["username"],
                password=data["password"],
                url=data.get("url", ""),
                notes=data.get("notes", ""),
                category=data.get("category", "General"),
            )
            self._refresh_entries()
            self.status_bar.configure(
                text=f"Updated '{data['site_name']}'.",
                text_color=COLORS["success"],
            )
        except Exception as e:
            self.status_bar.configure(
                text=f"Error updating entry: {e}",
                text_color=COLORS["error"],
            )

    # ------------------------------------------------------------------
    # Delete Entry
    # ------------------------------------------------------------------

    def _confirm_delete(self, entry: dict):
        """Show delete confirmation dialog."""
        DeleteConfirmDialog(
            parent=self,
            entry_name=entry["site_name"],
            on_confirm=lambda: self._delete_entry(entry),
        )

    def _delete_entry(self, entry: dict):
        """Delete an entry from the vault."""
        try:
            self.db.delete_entry(entry["id"])
            self._refresh_entries()
            self.status_bar.configure(
                text=f"Deleted '{entry['site_name']}'.",
                text_color=COLORS["warning"],
            )
        except Exception as e:
            self.status_bar.configure(
                text=f"Error deleting entry: {e}",
                text_color=COLORS["error"],
            )

    # ------------------------------------------------------------------
    # Search Helpers
    # ------------------------------------------------------------------

    def _clear_search(self):
        """Clear search box and show all entries."""
        self.search_entry.delete(0, "end")
        self._refresh_entries()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _show_settings(self):
        """Open the settings dialog."""
        SettingsDialog(parent=self, db=self.db)

    # ------------------------------------------------------------------
    # Lock
    # ------------------------------------------------------------------

    def _lock_vault(self):
        """Lock the vault and return to login screen."""
        # Clear clipboard if we had something copied
        if self.clipboard_clear_job:
            self.after_cancel(self.clipboard_clear_job)
            self._clear_clipboard()

        # Unbind shortcuts so they don't fire on the login screen
        top = self.winfo_toplevel()
        for shortcut in ("<Control-n>", "<Control-f>", "<Control-l>", "<Escape>"):
            top.unbind(shortcut)

        self.db.lock()
        self.on_lock()


# ======================================================================
# Entry Form Dialog (used for both Add and Edit)
# ======================================================================

class EntryFormDialog(ctk.CTkToplevel):
    """
    Dialog for adding or editing a vault entry.
    
    Args:
        parent: Parent widget
        title: Dialog title
        on_save: Callback with entry data dict
        existing: Existing entry data for edit mode (None for add)
    """

    def __init__(
        self,
        parent,
        title: str,
        on_save: Callable[[dict], None],
        existing: Optional[dict] = None,
    ):
        super().__init__(parent)
        self.on_save = on_save
        self.existing = existing
        self.password_visible = False

        self.title(title)
        self.geometry("440x540")
        self.minsize(380, 480)
        self.configure(fg_color=COLORS["bg_dark"])
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._build_ui()

        # If editing, populate fields
        if existing:
            self._populate(existing)

    def _build_ui(self):
        """Build the entry form."""
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=20)

        # --- Site Name ---
        ctk.CTkLabel(
            container,
            text="Site / Service Name *",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 4))

        self.site_entry = ctk.CTkEntry(
            container,
            placeholder_text="e.g. GitHub, Gmail, Netflix",
            font=ctk.CTkFont(size=13),
            height=38,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.site_entry.pack(fill="x", pady=(0, 12))

        # --- URL ---
        ctk.CTkLabel(
            container,
            text="URL",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 4))

        self.url_entry = ctk.CTkEntry(
            container,
            placeholder_text="https://github.com",
            font=ctk.CTkFont(size=13),
            height=38,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.url_entry.pack(fill="x", pady=(0, 12))

        # --- Username ---
        ctk.CTkLabel(
            container,
            text="Username / Email *",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 4))

        self.username_entry = ctk.CTkEntry(
            container,
            placeholder_text="your@email.com",
            font=ctk.CTkFont(size=13),
            height=38,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.username_entry.pack(fill="x", pady=(0, 12))

        # --- Password ---
        ctk.CTkLabel(
            container,
            text="Password *",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 4))

        pw_frame = ctk.CTkFrame(container, fg_color="transparent")
        pw_frame.pack(fill="x", pady=(0, 4))

        self.password_entry = ctk.CTkEntry(
            pw_frame,
            placeholder_text="Enter or generate a password",
            show="•",
            font=ctk.CTkFont(size=13),
            height=38,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.password_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        # Toggle visibility
        self.toggle_btn = ctk.CTkButton(
            pw_frame,
            text="👁",
            width=38,
            height=38,
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border"],
            command=self._toggle_password,
            font=ctk.CTkFont(size=14),
        )
        self.toggle_btn.pack(side="left", padx=(0, 6))

        # Generate button
        gen_btn = ctk.CTkButton(
            pw_frame,
            text="⚡",
            width=38,
            height=38,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._open_generator,
            font=ctk.CTkFont(size=14),
        )
        gen_btn.pack(side="left")

        # Password strength indicator
        self.pw_strength_label = ctk.CTkLabel(
            container,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.pw_strength_label.pack(fill="x", pady=(0, 8))
        self.password_entry.bind("<KeyRelease>", self._update_pw_strength)

        # --- Category ---
        ctk.CTkLabel(
            container,
            text="Category",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 4))

        self.category_menu = ctk.CTkOptionMenu(
            container,
            values=["General", "Social", "Work", "Finance", "Shopping", "Education", "Other"],
            font=ctk.CTkFont(size=12),
            height=34,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["border"],
            button_hover_color=COLORS["text_muted"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
        )
        self.category_menu.set("General")
        self.category_menu.pack(fill="x", pady=(0, 12))

        # --- Notes ---
        ctk.CTkLabel(
            container,
            text="Notes",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 4))

        self.notes_entry = ctk.CTkTextbox(
            container,
            font=ctk.CTkFont(size=12),
            height=60,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            border_width=1,
            corner_radius=6,
        )
        self.notes_entry.pack(fill="x", pady=(0, 16))

        # --- Error label ---
        self.error_label = ctk.CTkLabel(
            container,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["error"],
        )
        self.error_label.pack(fill="x", pady=(0, 4))

        # --- Save / Cancel buttons ---
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            font=ctk.CTkFont(size=13),
            height=40,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            command=self.destroy,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            btn_frame,
            text="Save",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._save,
        ).pack(side="right", fill="x", expand=True)

        # Focus site name
        self.site_entry.focus_set()

    def _populate(self, entry: dict):
        """Fill form fields with existing entry data."""
        self.site_entry.insert(0, entry.get("site_name", ""))
        self.url_entry.insert(0, entry.get("url", ""))
        self.username_entry.insert(0, entry.get("username", ""))
        self.password_entry.insert(0, entry.get("password", ""))
        self.category_menu.set(entry.get("category", "General"))
        if entry.get("notes"):
            self.notes_entry.insert("1.0", entry["notes"])
        self._update_pw_strength()

    def _toggle_password(self):
        """Toggle password visibility."""
        self.password_visible = not self.password_visible
        self.password_entry.configure(show="" if self.password_visible else "•")
        self.toggle_btn.configure(text="🙈" if self.password_visible else "👁")

    def _update_pw_strength(self, event=None):
        """Update password strength label."""
        pw = self.password_entry.get()
        if not pw:
            self.pw_strength_label.configure(text="", text_color=COLORS["text_muted"])
            return
        result = estimate_strength(pw)
        color = STRENGTH_COLORS.get(result["strength"], COLORS["text_muted"])
        self.pw_strength_label.configure(
            text=f"{result['strength']}  •  {result['entropy_bits']} bits",
            text_color=color,
        )

    def _open_generator(self):
        """Open the password generator dialog."""
        PasswordGeneratorDialog(
            parent=self,
            on_accept=self._use_generated_password,
        )

    def _use_generated_password(self, password: str):
        """Insert the generated password into the password field."""
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, password)
        self._update_pw_strength()

    def _save(self):
        """Validate and save the entry."""
        site = self.site_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        url = self.url_entry.get().strip()
        notes = self.notes_entry.get("1.0", "end-1c").strip()
        category = self.category_menu.get()

        # Validation
        if not site:
            self.error_label.configure(text="Site name is required.")
            self.site_entry.focus_set()
            return
        if not username:
            self.error_label.configure(text="Username is required.")
            self.username_entry.focus_set()
            return
        if not password:
            self.error_label.configure(text="Password is required.")
            self.password_entry.focus_set()
            return

        self.on_save({
            "site_name": site,
            "username": username,
            "password": password,
            "url": url,
            "notes": notes,
            "category": category,
        })
        self.destroy()


# ======================================================================
# Delete Confirmation Dialog
# ======================================================================

class DeleteConfirmDialog(ctk.CTkToplevel):
    """Simple delete confirmation popup."""

    def __init__(self, parent, entry_name: str, on_confirm: Callable):
        super().__init__(parent)
        self.on_confirm = on_confirm

        self.title("Confirm Delete")
        self.geometry("360x180")
        self.configure(fg_color=COLORS["bg_dark"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(
            container,
            text="⚠️  Delete Entry?",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            container,
            text=f'Are you sure you want to delete "{entry_name}"?\nThis cannot be undone.',
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            justify="center",
        ).pack(pady=(0, 16))

        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            font=ctk.CTkFont(size=13),
            height=36,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            command=self.destroy,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            btn_frame,
            text="Delete",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36,
            fg_color=COLORS["delete_btn"],
            hover_color=COLORS["delete_btn_hover"],
            command=self._do_delete,
        ).pack(side="right", fill="x", expand=True)

    def _do_delete(self):
        self.on_confirm()
        self.destroy()


# ======================================================================
# Settings Dialog
# ======================================================================

class SettingsDialog(ctk.CTkToplevel):
    """Settings dialog with vault management options."""

    def __init__(self, parent, db: VaultDatabase):
        super().__init__(parent)
        self.parent_ref = parent
        self.db = db

        self.title("Settings")
        self.geometry("400x340")
        self.configure(fg_color=COLORS["bg_dark"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(
            container,
            text="⚙️  Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 20))

        # --- Vault Info ---
        info_card = ctk.CTkFrame(
            container,
            fg_color=COLORS["bg_card"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )
        info_card.pack(fill="x", pady=(0, 16))

        info_inner = ctk.CTkFrame(info_card, fg_color="transparent")
        info_inner.pack(padx=16, pady=14, fill="x")

        try:
            count = self.db.get_entry_count()
        except Exception:
            count = "?"

        ctk.CTkLabel(
            info_inner,
            text=f"Vault contains {count} {'entry' if count == 1 else 'entries'}",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            info_inner,
            text=f"Database: vault.db (local, encrypted)",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(2, 0))

        # --- Change Master Password ---
        ctk.CTkButton(
            container,
            text="🔑  Change Master Password",
            font=ctk.CTkFont(size=13),
            height=42,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            anchor="w",
            command=self._change_password,
        ).pack(fill="x", pady=(0, 10))

        # --- Keyboard Shortcuts Info ---
        shortcuts_card = ctk.CTkFrame(
            container,
            fg_color=COLORS["bg_card"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )
        shortcuts_card.pack(fill="x", pady=(0, 16))

        sc_inner = ctk.CTkFrame(shortcuts_card, fg_color="transparent")
        sc_inner.pack(padx=16, pady=12, fill="x")

        ctk.CTkLabel(
            sc_inner,
            text="Keyboard Shortcuts",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 6))

        shortcuts = [
            ("Ctrl + N", "Add new entry"),
            ("Ctrl + F", "Focus search"),
            ("Ctrl + L", "Lock vault"),
            ("Escape", "Clear search"),
        ]
        for key, desc in shortcuts:
            row = ctk.CTkFrame(sc_inner, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(
                row,
                text=key,
                font=ctk.CTkFont(family="Courier", size=11),
                text_color=COLORS["accent"],
                width=80,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text=desc,
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_muted"],
                anchor="w",
            ).pack(side="left")

    def _change_password(self):
        """Open the change password dialog."""
        self.destroy()
        ChangePasswordDialog(parent=self.parent_ref, db=self.db)


# ======================================================================
# Change Master Password Dialog
# ======================================================================

class ChangePasswordDialog(ctk.CTkToplevel):
    """Dialog for changing the master password."""

    def __init__(self, parent, db: VaultDatabase):
        super().__init__(parent)
        self.db = db

        self.title("Change Master Password")
        self.geometry("420x360")
        self.configure(fg_color=COLORS["bg_dark"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(
            container,
            text="🔑  Change Master Password",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(
            container,
            text="All entries will be re-encrypted with the new password.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 16))

        # Current password
        ctk.CTkLabel(
            container,
            text="Current Password",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 4))

        self.current_entry = ctk.CTkEntry(
            container,
            show="•",
            font=ctk.CTkFont(size=13),
            height=38,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.current_entry.pack(fill="x", pady=(0, 12))

        # New password
        ctk.CTkLabel(
            container,
            text="New Password",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 4))

        self.new_entry = ctk.CTkEntry(
            container,
            show="•",
            font=ctk.CTkFont(size=13),
            height=38,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.new_entry.pack(fill="x", pady=(0, 12))

        # Confirm new password
        ctk.CTkLabel(
            container,
            text="Confirm New Password",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 4))

        self.confirm_entry = ctk.CTkEntry(
            container,
            show="•",
            font=ctk.CTkFont(size=13),
            height=38,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.confirm_entry.pack(fill="x", pady=(0, 8))

        # Status
        self.status_label = ctk.CTkLabel(
            container,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["error"],
        )
        self.status_label.pack(fill="x", pady=(0, 8))

        # Buttons
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            font=ctk.CTkFont(size=13),
            height=38,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            command=self.destroy,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.save_btn = ctk.CTkButton(
            btn_frame,
            text="Change Password",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._submit,
        )
        self.save_btn.pack(side="right", fill="x", expand=True)

        self.current_entry.focus_set()

    def _submit(self):
        """Validate and change the master password."""
        current = self.current_entry.get().strip()
        new = self.new_entry.get().strip()
        confirm = self.confirm_entry.get().strip()

        if not current or not new or not confirm:
            self.status_label.configure(text="All fields are required.")
            return

        if new != confirm:
            self.status_label.configure(text="New passwords don't match.")
            self.confirm_entry.delete(0, "end")
            self.confirm_entry.focus_set()
            return

        if len(new) < 8:
            self.status_label.configure(text="New password must be at least 8 characters.")
            return

        strength = estimate_strength(new)
        if strength["entropy_bits"] < 36:
            self.status_label.configure(text="New password is too weak. Make it longer or more complex.")
            return

        if current == new:
            self.status_label.configure(text="New password must be different from current.")
            return

        try:
            self.save_btn.configure(state="disabled", text="Changing...")
            self.update_idletasks()

            success = self.db.change_master_password(current, new)
            if success:
                self.status_label.configure(
                    text="Password changed successfully!",
                    text_color=COLORS["success"],
                )
                self.after(1500, self.destroy)
            else:
                self.save_btn.configure(state="normal", text="Change Password")
                self.status_label.configure(text="Current password is incorrect.")
                self.current_entry.delete(0, "end")
                self.current_entry.focus_set()

        except Exception as e:
            self.save_btn.configure(state="normal", text="Change Password")
            self.status_label.configure(text=f"Error: {e}")
