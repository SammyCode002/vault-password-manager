"""
main.py - Application entry point for the password manager.

This is the orchestrator. It:
1. Creates the main application window
2. Shows the login screen
3. On successful auth, swaps to the vault view
4. On lock, swaps back to login
5. Handles clean shutdown (wiping keys from memory)
"""

import sys
import customtkinter as ctk

from core.database import VaultDatabase
from gui.login_window import LoginWindow
from gui.main_window import MainWindow


COLORS = {
    "bg_dark": "#1a1a2e",
}

APP_VERSION = "1.0.0"


class PasswordManagerApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Window setup
        self.title("Vault - Password Manager")
        self.geometry("560x680")
        self.minsize(480, 580)
        self.configure(fg_color=COLORS["bg_dark"])

        # Handle window close (make sure we wipe the key from memory)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Initialize database
        self.db = VaultDatabase()

        # Track current view
        self.current_frame = None

        # Start with login
        self._show_login()

    def _show_login(self):
        """Show the login/setup screen."""
        if self.current_frame:
            self.current_frame.destroy()

        # Re-initialize DB connection for fresh login
        self.db = VaultDatabase()

        self.current_frame = LoginWindow(
            parent=self,
            db=self.db,
            on_login_success=self._show_vault,
        )
        self.current_frame.pack(fill="both", expand=True)

    def _show_vault(self):
        """Show the main vault view (called after successful login)."""
        if self.current_frame:
            self.current_frame.destroy()

        self.current_frame = MainWindow(
            parent=self,
            db=self.db,
            on_lock=self._show_login,
        )
        self.current_frame.pack(fill="both", expand=True)

    def _on_close(self):
        """Clean shutdown: lock the vault and destroy the window."""
        try:
            self.db.lock()
        except Exception:
            pass  # DB might already be closed
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
