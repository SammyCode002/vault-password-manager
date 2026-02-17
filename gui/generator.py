"""
generator.py - Password generator dialog.

A popup window that lets users generate random passwords or passphrases
with configurable options. Used from the "Add Entry" and "Edit Entry" forms
in the main vault window.
"""

import customtkinter as ctk
from typing import Callable, Optional

from core.password_gen import generate_password, generate_passphrase, estimate_strength

# Reuse the same color palette
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
    "strength_very_weak": "#e94560",
    "strength_weak": "#ff6b35",
    "strength_moderate": "#f0c808",
    "strength_strong": "#4ecca3",
    "strength_very_strong": "#00b894",
}

STRENGTH_COLORS = {
    "Very Weak": COLORS["strength_very_weak"],
    "Weak": COLORS["strength_weak"],
    "Moderate": COLORS["strength_moderate"],
    "Strong": COLORS["strength_strong"],
    "Very Strong": COLORS["strength_very_strong"],
}


class PasswordGeneratorDialog(ctk.CTkToplevel):
    """
    Popup dialog for generating passwords.
    
    Args:
        parent: Parent widget
        on_accept: Callback with the generated password when user clicks "Use This"
    """

    def __init__(self, parent, on_accept: Callable[[str], None]):
        super().__init__(parent)
        self.on_accept = on_accept
        self.generated_password = ""

        # Window setup
        self.title("Generate Password")
        self.geometry("460x560")
        self.minsize(400, 500)
        self.configure(fg_color=COLORS["bg_dark"])
        self.resizable(False, False)

        # Make it modal (blocks interaction with parent)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._generate()  # Generate one immediately

    def _build_ui(self):
        """Build the generator interface."""
        # Scrollable container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # --- Title ---
        title = ctk.CTkLabel(
            container,
            text="Password Generator",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        title.pack(pady=(0, 16))

        # --- Generated Password Display ---
        output_frame = ctk.CTkFrame(
            container,
            fg_color=COLORS["bg_card"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )
        output_frame.pack(fill="x", pady=(0, 8))

        self.output_label = ctk.CTkLabel(
            output_frame,
            text="",
            font=ctk.CTkFont(family="Courier", size=14),
            text_color=COLORS["success"],
            wraplength=380,
        )
        self.output_label.pack(padx=16, pady=16)

        # Strength indicator
        self.strength_bar = ctk.CTkProgressBar(
            container,
            height=6,
            corner_radius=3,
            fg_color=COLORS["border"],
            progress_color=COLORS["text_muted"],
        )
        self.strength_bar.pack(fill="x", pady=(0, 2))
        self.strength_bar.set(0)

        self.strength_label = ctk.CTkLabel(
            container,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.strength_label.pack(fill="x", pady=(0, 12))

        # --- Mode Toggle ---
        mode_frame = ctk.CTkFrame(container, fg_color="transparent")
        mode_frame.pack(fill="x", pady=(0, 12))

        self.mode_var = ctk.StringVar(value="password")

        self.pw_radio = ctk.CTkRadioButton(
            mode_frame,
            text="Random Password",
            variable=self.mode_var,
            value="password",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_primary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._on_mode_change,
        )
        self.pw_radio.pack(side="left", padx=(0, 20))

        self.pp_radio = ctk.CTkRadioButton(
            mode_frame,
            text="Passphrase",
            variable=self.mode_var,
            value="passphrase",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_primary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._on_mode_change,
        )
        self.pp_radio.pack(side="left")

        # --- Options Card ---
        self.options_card = ctk.CTkFrame(
            container,
            fg_color=COLORS["bg_card"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.options_card.pack(fill="x", pady=(0, 16))

        options_inner = ctk.CTkFrame(self.options_card, fg_color="transparent")
        options_inner.pack(padx=16, pady=16, fill="x")

        # -- Password options --
        self.pw_options_frame = ctk.CTkFrame(options_inner, fg_color="transparent")

        # Length slider
        length_row = ctk.CTkFrame(self.pw_options_frame, fg_color="transparent")
        length_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            length_row,
            text="Length",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        ).pack(side="left")

        self.length_value_label = ctk.CTkLabel(
            length_row,
            text="16",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        self.length_value_label.pack(side="right")

        self.length_slider = ctk.CTkSlider(
            self.pw_options_frame,
            from_=6,
            to=64,
            number_of_steps=58,
            fg_color=COLORS["border"],
            progress_color=COLORS["accent"],
            button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"],
            command=self._on_length_change,
        )
        self.length_slider.set(16)
        self.length_slider.pack(fill="x", pady=(0, 12))

        # Checkboxes
        self.use_upper = ctk.CTkCheckBox(
            self.pw_options_frame,
            text="Uppercase (A-Z)",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._generate,
        )
        self.use_upper.select()
        self.use_upper.pack(anchor="w", pady=2)

        self.use_lower = ctk.CTkCheckBox(
            self.pw_options_frame,
            text="Lowercase (a-z)",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._generate,
        )
        self.use_lower.select()
        self.use_lower.pack(anchor="w", pady=2)

        self.use_digits = ctk.CTkCheckBox(
            self.pw_options_frame,
            text="Digits (0-9)",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._generate,
        )
        self.use_digits.select()
        self.use_digits.pack(anchor="w", pady=2)

        self.use_symbols = ctk.CTkCheckBox(
            self.pw_options_frame,
            text="Symbols (!@#$%...)",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._generate,
        )
        self.use_symbols.select()
        self.use_symbols.pack(anchor="w", pady=2)

        self.exclude_ambiguous = ctk.CTkCheckBox(
            self.pw_options_frame,
            text="Exclude ambiguous (I, l, 1, O, 0)",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._generate,
        )
        self.exclude_ambiguous.pack(anchor="w", pady=2)

        self.pw_options_frame.pack(fill="x")

        # -- Passphrase options (hidden by default) --
        self.pp_options_frame = ctk.CTkFrame(options_inner, fg_color="transparent")

        # Word count slider
        wc_row = ctk.CTkFrame(self.pp_options_frame, fg_color="transparent")
        wc_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            wc_row,
            text="Words",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        ).pack(side="left")

        self.word_count_label = ctk.CTkLabel(
            wc_row,
            text="4",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        self.word_count_label.pack(side="right")

        self.word_slider = ctk.CTkSlider(
            self.pp_options_frame,
            from_=3,
            to=8,
            number_of_steps=5,
            fg_color=COLORS["border"],
            progress_color=COLORS["accent"],
            button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"],
            command=self._on_word_count_change,
        )
        self.word_slider.set(4)
        self.word_slider.pack(fill="x", pady=(0, 12))

        # Separator
        sep_row = ctk.CTkFrame(self.pp_options_frame, fg_color="transparent")
        sep_row.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            sep_row,
            text="Separator",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        ).pack(side="left")

        self.separator_var = ctk.StringVar(value="-")
        self.separator_menu = ctk.CTkSegmentedButton(
            sep_row,
            values=["-", ".", "_", " "],
            variable=self.separator_var,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["bg_input"],
            command=lambda v: self._generate(),
        )
        self.separator_menu.pack(side="right")

        self.pp_capitalize = ctk.CTkCheckBox(
            self.pp_options_frame,
            text="Capitalize words",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._generate,
        )
        self.pp_capitalize.select()
        self.pp_capitalize.pack(anchor="w", pady=2)

        self.pp_include_num = ctk.CTkCheckBox(
            self.pp_options_frame,
            text="Include a number",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._generate,
        )
        self.pp_include_num.select()
        self.pp_include_num.pack(anchor="w", pady=2)

        # --- Action Buttons ---
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 0))

        self.regenerate_btn = ctk.CTkButton(
            btn_frame,
            text="🔄 Regenerate",
            font=ctk.CTkFont(size=13),
            height=40,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            command=self._generate,
        )
        self.regenerate_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.accept_btn = ctk.CTkButton(
            btn_frame,
            text="✓ Use This",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._accept,
        )
        self.accept_btn.pack(side="right", fill="x", expand=True)

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    def _on_mode_change(self):
        """Switch between password and passphrase options."""
        if self.mode_var.get() == "password":
            self.pp_options_frame.pack_forget()
            self.pw_options_frame.pack(fill="x")
        else:
            self.pw_options_frame.pack_forget()
            self.pp_options_frame.pack(fill="x")
        self._generate()

    def _on_length_change(self, value):
        """Update length label and regenerate."""
        length = int(value)
        self.length_value_label.configure(text=str(length))
        self._generate()

    def _on_word_count_change(self, value):
        """Update word count label and regenerate."""
        count = int(value)
        self.word_count_label.configure(text=str(count))
        self._generate()

    def _generate(self, *args):
        """Generate a new password/passphrase with current settings."""
        try:
            if self.mode_var.get() == "password":
                self.generated_password = generate_password(
                    length=int(self.length_slider.get()),
                    use_lowercase=self.use_lower.get(),
                    use_uppercase=self.use_upper.get(),
                    use_digits=self.use_digits.get(),
                    use_symbols=self.use_symbols.get(),
                    exclude_ambiguous=self.exclude_ambiguous.get(),
                )
            else:
                self.generated_password = generate_passphrase(
                    word_count=int(self.word_slider.get()),
                    separator=self.separator_var.get(),
                    capitalize=self.pp_capitalize.get(),
                    include_number=self.pp_include_num.get(),
                )

            # Update display
            self.output_label.configure(text=self.generated_password)

            # Update strength
            result = estimate_strength(self.generated_password)
            progress = min(result["entropy_bits"] / 100.0, 1.0)
            self.strength_bar.set(progress)
            color = STRENGTH_COLORS.get(result["strength"], COLORS["text_muted"])
            self.strength_bar.configure(progress_color=color)
            self.strength_label.configure(
                text=f"{result['strength']}  •  {result['entropy_bits']} bits",
                text_color=color,
            )

        except ValueError as e:
            self.output_label.configure(text=str(e))
            self.strength_bar.set(0)
            self.strength_label.configure(text="", text_color=COLORS["text_muted"])

    def _accept(self):
        """Send the generated password back and close."""
        if self.generated_password:
            self.on_accept(self.generated_password)
        self.destroy()
