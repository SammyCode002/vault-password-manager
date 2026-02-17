"""
main.py - Application entry point for the password manager.
"""

import sys
import customtkinter as ctk

from core.database import VaultDatabase
from gui.login_window import LoginWindow
from gui.main_window import MainWindow
from gui.theme import get_colors, get_mode

APP_VERSION = "2.0.0"


class PasswordManagerApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        C = get_colors()
        self.title("Vault - Password Manager")
        self.geometry("820x620")
        self.minsize(760, 560)
        self.configure(fg_color=C["bg_primary"])

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.db = VaultDatabase()
        self.current_frame = None
        self._show_login()

    def _show_login(self):
        if self.current_frame:
            self.current_frame.destroy()
        self.db = VaultDatabase()

        C = get_colors()
        self.configure(fg_color=C["bg_primary"])

        self.current_frame = LoginWindow(
            parent=self, db=self.db,
            on_login_success=self._show_vault,
        )
        self.current_frame.pack(fill="both", expand=True)

    def _show_vault(self):
        if self.current_frame:
            self.current_frame.destroy()

        C = get_colors()
        self.configure(fg_color=C["bg_primary"])

        self.current_frame = MainWindow(
            parent=self, db=self.db,
            on_lock=self._show_login,
            on_theme_change=self._rebuild_vault,
        )
        self.current_frame.pack(fill="both", expand=True)

    def _rebuild_vault(self):
        """Rebuild the vault view after a theme change."""
        self._show_vault()

    def _on_close(self):
        try:
            self.db.lock()
        except Exception:
            pass
        self.destroy()


def main():
    ctk.set_appearance_mode("dark")

    try:
        app = PasswordManagerApp()
        app.mainloop()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
