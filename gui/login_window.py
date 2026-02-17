"""
login_window.py - Redesigned login screen with branding and modern styling.

Features:
- Animated logo/branding area
- Smooth strength meter
- Password visibility toggle
- First-time setup vs returning user detection
- Light/dark mode support
"""

import customtkinter as ctk
from typing import Callable

from core.database import VaultDatabase
from core.password_gen import estimate_strength
from gui.theme import get_colors, get_strength_color, get_mode


class LoginWindow(ctk.CTkFrame):
    """Login/setup frame for the password manager."""

    def __init__(self, parent: ctk.CTk, db: VaultDatabase, on_login_success: Callable):
        C = get_colors()
        super().__init__(parent, fg_color=C["bg_primary"])
        self.db = db
        self.on_login_success = on_login_success
        self.failed_attempts = 0
        self.password_visible = False
        self.confirm_visible = False
        self.is_setup_mode = not db.vault_exists()

        self._build_ui()

    def _build_ui(self):
        C = get_colors()

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Main card
        card = ctk.CTkFrame(
            self, fg_color=C["bg_card"], corner_radius=20,
            border_width=1, border_color=C["border"],
        )
        card.grid(row=1, column=0, padx=40, pady=20)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=48, pady=44)

        # --- Logo / Brand ---
        logo_frame = ctk.CTkFrame(inner, fg_color="transparent")
        logo_frame.pack(pady=(0, 6))

        # Shield icon circle
        shield_bg = ctk.CTkFrame(
            logo_frame, width=72, height=72, corner_radius=36,
            fg_color=C["accent_muted"],
        )
        shield_bg.pack()
        shield_bg.pack_propagate(False)

        ctk.CTkLabel(
            shield_bg, text="🛡", font=ctk.CTkFont(size=32),
            text_color=C["accent"],
        ).place(relx=0.5, rely=0.5, anchor="center")

        # App name
        ctk.CTkLabel(
            inner, text="Vault",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=C["text_primary"],
        ).pack(pady=(12, 2))

        ctk.CTkLabel(
            inner, text="Password Manager",
            font=ctk.CTkFont(size=13),
            text_color=C["text_secondary"],
        ).pack(pady=(0, 4))

        # --- Title ---
        title_text = "Create your vault" if self.is_setup_mode else "Welcome back"
        subtitle_text = (
            "Choose a strong master password to protect your credentials."
            if self.is_setup_mode else
            "Enter your master password to unlock."
        )

        ctk.CTkLabel(
            inner, text=title_text,
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=C["text_primary"],
        ).pack(pady=(20, 2))

        ctk.CTkLabel(
            inner, text=subtitle_text,
            font=ctk.CTkFont(size=12),
            text_color=C["text_secondary"],
            wraplength=320, justify="center",
        ).pack(pady=(0, 20))

        # --- Master Password ---
        ctk.CTkLabel(
            inner, text="Master Password",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["text_secondary"], anchor="w",
        ).pack(fill="x", pady=(0, 4))

        pw_frame = ctk.CTkFrame(inner, fg_color="transparent")
        pw_frame.pack(fill="x", pady=(0, 4))

        self.password_entry = ctk.CTkEntry(
            pw_frame, placeholder_text="Enter master password", show="•",
            font=ctk.CTkFont(size=14), height=44,
            fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"],
            placeholder_text_color=C["text_muted"],
            corner_radius=10,
        )
        self.password_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.toggle_pw_btn = ctk.CTkButton(
            pw_frame, text="👁", width=44, height=44,
            fg_color=C["bg_input"], hover_color=C["bg_hover"],
            corner_radius=10, font=ctk.CTkFont(size=15),
            command=self._toggle_password_visibility,
        )
        self.toggle_pw_btn.pack(side="right")

        # --- Strength Meter (setup mode) ---
        if self.is_setup_mode:
            self.strength_frame = ctk.CTkFrame(inner, fg_color="transparent")
            self.strength_frame.pack(fill="x", pady=(4, 4))

            # Multi-segment strength bar
            self.segments_frame = ctk.CTkFrame(self.strength_frame, fg_color="transparent", height=6)
            self.segments_frame.pack(fill="x", pady=(0, 4))

            self.segments = []
            for i in range(5):
                seg = ctk.CTkFrame(
                    self.segments_frame, height=4, corner_radius=2,
                    fg_color=C["border"],
                )
                seg.pack(side="left", fill="x", expand=True, padx=(0, 3 if i < 4 else 0))
                self.segments.append(seg)

            self.strength_label = ctk.CTkLabel(
                self.strength_frame, text="",
                font=ctk.CTkFont(size=11),
                text_color=C["text_muted"], anchor="w",
            )
            self.strength_label.pack(fill="x")

            self.password_entry.bind("<KeyRelease>", self._update_strength)

        # --- Confirm Password (setup mode) ---
        if self.is_setup_mode:
            ctk.CTkLabel(
                inner, text="Confirm Password",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=C["text_secondary"], anchor="w",
            ).pack(fill="x", pady=(12, 4))

            confirm_frame = ctk.CTkFrame(inner, fg_color="transparent")
            confirm_frame.pack(fill="x", pady=(0, 4))

            self.confirm_entry = ctk.CTkEntry(
                confirm_frame, placeholder_text="Confirm master password", show="•",
                font=ctk.CTkFont(size=14), height=44,
                fg_color=C["bg_input"], border_color=C["border"],
                text_color=C["text_primary"],
                placeholder_text_color=C["text_muted"],
                corner_radius=10,
            )
            self.confirm_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

            self.toggle_confirm_btn = ctk.CTkButton(
                confirm_frame, text="👁", width=44, height=44,
                fg_color=C["bg_input"], hover_color=C["bg_hover"],
                corner_radius=10, font=ctk.CTkFont(size=15),
                command=self._toggle_confirm_visibility,
            )
            self.toggle_confirm_btn.pack(side="right")

            self.confirm_entry.bind("<Return>", lambda e: self._submit())

        # --- Status ---
        self.status_label = ctk.CTkLabel(
            inner, text="", font=ctk.CTkFont(size=12),
            text_color=C["error"], wraplength=320,
        )
        self.status_label.pack(fill="x", pady=(8, 0))

        # --- Submit Button ---
        btn_text = "Create Vault" if self.is_setup_mode else "Unlock"
        self.submit_btn = ctk.CTkButton(
            inner, text=btn_text,
            font=ctk.CTkFont(size=15, weight="bold"),
            height=46, fg_color=C["accent"],
            hover_color=C["accent_hover"],
            corner_radius=12,
            command=self._submit,
        )
        self.submit_btn.pack(fill="x", pady=(16, 0))

        self.password_entry.bind("<Return>", lambda e: self._submit())
        self.password_entry.focus_set()

    # -- Visibility Toggles --

    def _toggle_password_visibility(self):
        self.password_visible = not self.password_visible
        self.password_entry.configure(show="" if self.password_visible else "•")
        self.toggle_pw_btn.configure(text="🙈" if self.password_visible else "👁")

    def _toggle_confirm_visibility(self):
        self.confirm_visible = not self.confirm_visible
        self.confirm_entry.configure(show="" if self.confirm_visible else "•")
        self.toggle_confirm_btn.configure(text="🙈" if self.confirm_visible else "👁")

    # -- Strength Meter --

    def _update_strength(self, event=None):
        C = get_colors()
        password = self.password_entry.get()

        if not password:
            for seg in self.segments:
                seg.configure(fg_color=C["border"])
            self.strength_label.configure(text="", text_color=C["text_muted"])
            return

        result = estimate_strength(password)
        entropy = result["entropy_bits"]
        color = get_strength_color(result["strength"])

        # Map strength to number of lit segments (1-5)
        if entropy < 28:
            lit = 1
        elif entropy < 36:
            lit = 2
        elif entropy < 60:
            lit = 3
        elif entropy < 80:
            lit = 4
        else:
            lit = 5

        for i, seg in enumerate(self.segments):
            seg.configure(fg_color=color if i < lit else C["border"])

        self.strength_label.configure(
            text=f"{result['strength']}  ·  {result['entropy_bits']} bits",
            text_color=color,
        )

    # -- Form Submission --

    def _submit(self):
        password = self.password_entry.get().strip()
        if not password:
            self._show_error("Please enter a master password.")
            return
        if self.is_setup_mode:
            self._handle_setup(password)
        else:
            self._handle_login(password)

    def _handle_setup(self, password: str):
        C = get_colors()
        confirm = self.confirm_entry.get().strip()

        strength = estimate_strength(password)
        if strength["entropy_bits"] < 36:
            self._show_error("Password is too weak. Try making it longer or more complex.")
            return
        if password != confirm:
            self._show_error("Passwords don't match.")
            self.confirm_entry.delete(0, "end")
            self.confirm_entry.focus_set()
            return
        if len(password) < 8:
            self._show_error("Must be at least 8 characters.")
            return

        try:
            self.submit_btn.configure(state="disabled", text="Creating vault...")
            self.update_idletasks()
            self.db.initialize_vault(password)
            self.on_login_success()
        except Exception as e:
            self.submit_btn.configure(state="normal", text="Create Vault")
            self._show_error(f"Failed to create vault: {e}")

    def _handle_login(self, password: str):
        C = get_colors()
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
                        "There is no way to recover a forgotten master password."
                    )
                else:
                    self._show_error("Incorrect master password.")
                self.password_entry.delete(0, "end")
                self.password_entry.focus_set()
        except Exception as e:
            self.submit_btn.configure(state="normal", text="Unlock")
            self._show_error(f"Error: {e}")

    def _show_error(self, message: str):
        C = get_colors()
        self.status_label.configure(text=message, text_color=C["error"])
