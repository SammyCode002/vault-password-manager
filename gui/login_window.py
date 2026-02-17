"""
login_window.py - Master password entry and first-time vault setup.

This is the first screen users see. It handles two scenarios:
1. First launch: User creates a master password (with confirmation + strength meter)
2. Returning user: User enters their master password to unlock the vault

Design decisions:
- Password visibility toggle (eye icon) so users can verify what they typed
- Strength meter on setup so users pick a good master password
- Failed attempt counter to discourage guessing (UI only — real brute-force
  protection comes from PBKDF2's slowness in the encryption module)
- Clean, minimal layout — this screen should feel trustworthy and secure
"""

import customtkinter as ctk
from typing import Callable, Optional

from core.database import VaultDatabase
from core.password_gen import estimate_strength


# Color constants
COLORS = {
    "bg_dark": "#1a1a2e",
    "bg_card": "#16213e",
    "bg_input": "#0f3460",
    "accent": "#e94560",
    "accent_hover": "#c73652",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0b8",
    "text_muted": "#6c6c80",
    "success": "#4ecca3",
    "error": "#e94560",
    "border": "#2a2a4a",
    # Strength meter colors
    "strength_very_weak": "#e94560",
    "strength_weak": "#ff6b35",
    "strength_moderate": "#f0c808",
    "strength_strong": "#4ecca3",
    "strength_very_strong": "#00b894",
}

# Strength color mapping
STRENGTH_COLORS = {
    "Very Weak": COLORS["strength_very_weak"],
    "Weak": COLORS["strength_weak"],
    "Moderate": COLORS["strength_moderate"],
    "Strong": COLORS["strength_strong"],
    "Very Strong": COLORS["strength_very_strong"],
}


class LoginWindow(ctk.CTkFrame):
    """
    Login/setup frame for the password manager.
    
    This is a frame (not a standalone window) so the main app can swap
    between login and vault views without opening/closing windows.
    
    Args:
        parent: The parent widget (main app window)
        db: VaultDatabase instance
        on_login_success: Callback when authentication succeeds
    """

    def __init__(
        self,
        parent: ctk.CTk,
        db: VaultDatabase,
        on_login_success: Callable,
    ):
        super().__init__(parent, fg_color=COLORS["bg_dark"])
        self.db = db
        self.on_login_success = on_login_success
        self.failed_attempts = 0
        self.password_visible = False
        self.confirm_visible = False
        self.is_setup_mode = not db.vault_exists()

        self._build_ui()

    def _build_ui(self):
        """Build the login interface."""
        # Center everything vertically
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Main card container
        card = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.grid(row=1, column=0, padx=40, pady=20)

        # Inner padding frame
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=40, pady=40)

        # --- Lock icon (text-based, no image dependencies) ---
        lock_label = ctk.CTkLabel(
            inner,
            text="🔒",
            font=ctk.CTkFont(size=48),
            text_color=COLORS["accent"],
        )
        lock_label.pack(pady=(0, 8))

        # --- Title ---
        title_text = "Create Your Vault" if self.is_setup_mode else "Unlock Vault"
        title = ctk.CTkLabel(
            inner,
            text=title_text,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        title.pack(pady=(0, 4))

        # --- Subtitle ---
        if self.is_setup_mode:
            subtitle_text = "Choose a strong master password.\nThis is the only password you'll need to remember."
        else:
            subtitle_text = "Enter your master password to continue."
        subtitle = ctk.CTkLabel(
            inner,
            text=subtitle_text,
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
            justify="center",
        )
        subtitle.pack(pady=(0, 24))

        # --- Master Password Field ---
        pw_label = ctk.CTkLabel(
            inner,
            text="Master Password",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
            anchor="w",
        )
        pw_label.pack(fill="x", pady=(0, 4))

        pw_frame = ctk.CTkFrame(inner, fg_color="transparent")
        pw_frame.pack(fill="x", pady=(0, 4))

        self.password_entry = ctk.CTkEntry(
            pw_frame,
            placeholder_text="Enter master password",
            show="•",
            font=ctk.CTkFont(size=14),
            height=42,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            placeholder_text_color=COLORS["text_muted"],
        )
        self.password_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.toggle_pw_btn = ctk.CTkButton(
            pw_frame,
            text="👁",
            width=42,
            height=42,
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border"],
            command=self._toggle_password_visibility,
            font=ctk.CTkFont(size=16),
        )
        self.toggle_pw_btn.pack(side="right")

        # --- Strength meter (setup mode only) ---
        if self.is_setup_mode:
            self.strength_frame = ctk.CTkFrame(inner, fg_color="transparent")
            self.strength_frame.pack(fill="x", pady=(0, 8))

            self.strength_bar = ctk.CTkProgressBar(
                self.strength_frame,
                height=6,
                corner_radius=3,
                fg_color=COLORS["border"],
                progress_color=COLORS["text_muted"],
            )
            self.strength_bar.pack(fill="x", pady=(4, 2))
            self.strength_bar.set(0)

            self.strength_label = ctk.CTkLabel(
                self.strength_frame,
                text="",
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_muted"],
                anchor="w",
            )
            self.strength_label.pack(fill="x")

            # Bind keystroke tracking for real-time strength updates
            self.password_entry.bind("<KeyRelease>", self._update_strength)

        # --- Confirm Password Field (setup mode only) ---
        if self.is_setup_mode:
            confirm_label = ctk.CTkLabel(
                inner,
                text="Confirm Password",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["text_secondary"],
                anchor="w",
            )
            confirm_label.pack(fill="x", pady=(12, 4))

            confirm_frame = ctk.CTkFrame(inner, fg_color="transparent")
            confirm_frame.pack(fill="x", pady=(0, 4))

            self.confirm_entry = ctk.CTkEntry(
                confirm_frame,
                placeholder_text="Confirm master password",
                show="•",
                font=ctk.CTkFont(size=14),
                height=42,
                fg_color=COLORS["bg_input"],
                border_color=COLORS["border"],
                text_color=COLORS["text_primary"],
                placeholder_text_color=COLORS["text_muted"],
            )
            self.confirm_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

            self.toggle_confirm_btn = ctk.CTkButton(
                confirm_frame,
                text="👁",
                width=42,
                height=42,
                fg_color=COLORS["bg_input"],
                hover_color=COLORS["border"],
                command=self._toggle_confirm_visibility,
                font=ctk.CTkFont(size=16),
            )
            self.toggle_confirm_btn.pack(side="right")

            # Bind Enter key on confirm field
            self.confirm_entry.bind("<Return>", lambda e: self._submit())

        # --- Status message area ---
        self.status_label = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["error"],
            wraplength=300,
        )
        self.status_label.pack(fill="x", pady=(8, 0))

        # --- Submit button ---
        btn_text = "Create Vault" if self.is_setup_mode else "Unlock"
        self.submit_btn = ctk.CTkButton(
            inner,
            text=btn_text,
            font=ctk.CTkFont(size=15, weight="bold"),
            height=44,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=10,
            command=self._submit,
        )
        self.submit_btn.pack(fill="x", pady=(16, 0))

        # Bind Enter key on password field
        self.password_entry.bind("<Return>", lambda e: self._submit())

        # Focus the password entry
        self.password_entry.focus_set()

    # ------------------------------------------------------------------
    # Password Visibility Toggles
    # ------------------------------------------------------------------

    def _toggle_password_visibility(self):
        """Toggle master password field between hidden and visible."""
        self.password_visible = not self.password_visible
        self.password_entry.configure(show="" if self.password_visible else "•")
        self.toggle_pw_btn.configure(text="🙈" if self.password_visible else "👁")

    def _toggle_confirm_visibility(self):
        """Toggle confirm password field between hidden and visible."""
        self.confirm_visible = not self.confirm_visible
        self.confirm_entry.configure(show="" if self.confirm_visible else "•")
        self.toggle_confirm_btn.configure(text="🙈" if self.confirm_visible else "👁")

    # ------------------------------------------------------------------
    # Strength Meter (setup mode)
    # ------------------------------------------------------------------

    def _update_strength(self, event=None):
        """Update the strength meter as the user types."""
        password = self.password_entry.get()

        if not password:
            self.strength_bar.set(0)
            self.strength_bar.configure(progress_color=COLORS["text_muted"])
            self.strength_label.configure(text="", text_color=COLORS["text_muted"])
            return

        result = estimate_strength(password)
        entropy = result["entropy_bits"]

        # Map entropy to progress bar (0-100+ bits mapped to 0.0-1.0)
        progress = min(entropy / 100.0, 1.0)
        self.strength_bar.set(progress)

        # Update colors and label
        color = STRENGTH_COLORS.get(result["strength"], COLORS["text_muted"])
        self.strength_bar.configure(progress_color=color)
        self.strength_label.configure(
            text=f"{result['strength']}  •  {result['entropy_bits']} bits of entropy",
            text_color=color,
        )

    # ------------------------------------------------------------------
    # Form Submission
    # ------------------------------------------------------------------

    def _submit(self):
        """Handle the login or setup form submission."""
        password = self.password_entry.get().strip()

        if not password:
            self._show_error("Please enter a master password.")
            return

        if self.is_setup_mode:
            self._handle_setup(password)
        else:
            self._handle_login(password)

    def _handle_setup(self, password: str):
        """Handle first-time vault creation."""
        confirm = self.confirm_entry.get().strip()

        # Validate password strength
        strength = estimate_strength(password)
        if strength["entropy_bits"] < 36:
            self._show_error(
                "That password is too weak. Try making it longer "
                "or adding uppercase, numbers, and symbols."
            )
            return

        # Check confirmation matches
        if password != confirm:
            self._show_error("Passwords don't match. Try again.")
            self.confirm_entry.delete(0, "end")
            self.confirm_entry.focus_set()
            return

        # Minimum length check
        if len(password) < 8:
            self._show_error("Master password must be at least 8 characters.")
            return

        try:
            self.submit_btn.configure(state="disabled", text="Creating vault...")
            self.update_idletasks()  # Force UI update

            self.db.initialize_vault(password)
            self.on_login_success()

        except Exception as e:
            self.submit_btn.configure(state="normal", text="Create Vault")
            self._show_error(f"Failed to create vault: {e}")

    def _handle_login(self, password: str):
        """Handle returning user login."""
        try:
            self.submit_btn.configure(state="disabled", text="Unlocking...")
            self.update_idletasks()

            if self.db.unlock(password):
                self.on_login_success()
            else:
                self.failed_attempts += 1
                self.submit_btn.configure(state="normal", text="Unlock")

                if self.failed_attempts >= 3:
                    self._show_error(
                        f"Incorrect password ({self.failed_attempts} attempts). "
                        "Remember, there's no way to recover a forgotten master password."
                    )
                else:
                    self._show_error("Incorrect master password. Try again.")

                self.password_entry.delete(0, "end")
                self.password_entry.focus_set()

        except Exception as e:
            self.submit_btn.configure(state="normal", text="Unlock")
            self._show_error(f"Error: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _show_error(self, message: str):
        """Display an error message below the form."""
        self.status_label.configure(text=message, text_color=COLORS["error"])

    def _show_success(self, message: str):
        """Display a success message below the form."""
        self.status_label.configure(text=message, text_color=COLORS["success"])


# --- Quick visual test ---
if __name__ == "__main__":
    import os
    import tempfile

    # Create a test database in temp
    test_db_path = os.path.join(tempfile.gettempdir(), "test_login_vault.db")
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    db = VaultDatabase(test_db_path)

    def on_success():
        print("Login successful! Vault is unlocked.")
        # In the real app, this switches to the vault view
        app.destroy()

    # Set up the window
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_scaling(1.0)

    app = ctk.CTk()
    app.title("Vault - Password Manager")
    app.geometry("480x620")
    app.minsize(400, 550)
    app.configure(fg_color=COLORS["bg_dark"])

    # Show login window
    login = LoginWindow(app, db, on_login_success=on_success)
    login.pack(fill="both", expand=True)

    print(f"Test mode: {'SETUP' if login.is_setup_mode else 'LOGIN'}")
    print(f"Vault DB: {test_db_path}")
    print("Close the window when done testing.")

    app.mainloop()

    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
