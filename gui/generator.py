"""
generator.py - Redesigned password generator dialog.
"""

import customtkinter as ctk
from typing import Callable

from core.password_gen import generate_password, generate_passphrase, estimate_strength
from gui.theme import get_colors, get_strength_color


class PasswordGeneratorDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_accept: Callable[[str], None]):
        super().__init__(parent)
        C = get_colors()
        self.on_accept = on_accept
        self.generated_password = ""

        self.title("Generate Password")
        self.geometry("460x580")
        self.minsize(420, 520)
        self.configure(fg_color=C["bg_primary"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._generate()

    def _build_ui(self):
        C = get_colors()

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(
            container, text="Password Generator",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=C["text_primary"],
        ).pack(pady=(0, 14))

        # Output display
        output_card = ctk.CTkFrame(
            container, fg_color=C["bg_card"], corner_radius=12,
            border_width=1, border_color=C["border"],
        )
        output_card.pack(fill="x", pady=(0, 6))

        self.output_label = ctk.CTkLabel(
            output_card, text="",
            font=ctk.CTkFont(family="Courier", size=14),
            text_color=C["success"], wraplength=380,
        )
        self.output_label.pack(padx=16, pady=16)

        # Strength segments
        seg_frame = ctk.CTkFrame(container, fg_color="transparent", height=6)
        seg_frame.pack(fill="x", pady=(0, 2))

        self.segments = []
        for i in range(5):
            seg = ctk.CTkFrame(seg_frame, height=4, corner_radius=2, fg_color=C["border"])
            seg.pack(side="left", fill="x", expand=True, padx=(0, 3 if i < 4 else 0))
            self.segments.append(seg)

        self.strength_label = ctk.CTkLabel(
            container, text="", font=ctk.CTkFont(size=11),
            text_color=C["text_muted"], anchor="w",
        )
        self.strength_label.pack(fill="x", pady=(0, 12))

        # Mode toggle
        mode_frame = ctk.CTkFrame(container, fg_color="transparent")
        mode_frame.pack(fill="x", pady=(0, 10))

        self.mode_var = ctk.StringVar(value="password")

        for val, label in [("password", "Random Password"), ("passphrase", "Passphrase")]:
            ctk.CTkRadioButton(
                mode_frame, text=label, variable=self.mode_var, value=val,
                font=ctk.CTkFont(size=13), text_color=C["text_primary"],
                fg_color=C["accent"], hover_color=C["accent_hover"],
                command=self._on_mode_change,
            ).pack(side="left", padx=(0, 16))

        # Options card
        self.options_card = ctk.CTkFrame(
            container, fg_color=C["bg_card"], corner_radius=12,
            border_width=1, border_color=C["border"],
        )
        self.options_card.pack(fill="x", pady=(0, 14))

        opts = ctk.CTkFrame(self.options_card, fg_color="transparent")
        opts.pack(padx=16, pady=14, fill="x")

        # -- Password options --
        self.pw_frame = ctk.CTkFrame(opts, fg_color="transparent")

        len_row = ctk.CTkFrame(self.pw_frame, fg_color="transparent")
        len_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(len_row, text="Length", font=ctk.CTkFont(size=12), text_color=C["text_secondary"]).pack(side="left")
        self.length_label = ctk.CTkLabel(len_row, text="16", font=ctk.CTkFont(size=12, weight="bold"), text_color=C["text_primary"])
        self.length_label.pack(side="right")

        self.length_slider = ctk.CTkSlider(
            self.pw_frame, from_=6, to=64, number_of_steps=58,
            fg_color=C["border"], progress_color=C["accent"],
            button_color=C["accent"], button_hover_color=C["accent_hover"],
            command=self._on_length_change,
        )
        self.length_slider.set(16)
        self.length_slider.pack(fill="x", pady=(0, 10))

        self.checkboxes = {}
        for key, label in [("upper", "Uppercase (A-Z)"), ("lower", "Lowercase (a-z)"), ("digits", "Digits (0-9)"), ("symbols", "Symbols (!@#...)"), ("ambiguous", "Exclude ambiguous (I,l,1,O,0)")]:
            cb = ctk.CTkCheckBox(
                self.pw_frame, text=label, font=ctk.CTkFont(size=12),
                text_color=C["text_secondary"], fg_color=C["accent"],
                hover_color=C["accent_hover"], corner_radius=4,
                command=self._generate,
            )
            if key != "ambiguous":
                cb.select()
            cb.pack(anchor="w", pady=2)
            self.checkboxes[key] = cb

        self.pw_frame.pack(fill="x")

        # -- Passphrase options --
        self.pp_frame = ctk.CTkFrame(opts, fg_color="transparent")

        wc_row = ctk.CTkFrame(self.pp_frame, fg_color="transparent")
        wc_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(wc_row, text="Words", font=ctk.CTkFont(size=12), text_color=C["text_secondary"]).pack(side="left")
        self.word_label = ctk.CTkLabel(wc_row, text="4", font=ctk.CTkFont(size=12, weight="bold"), text_color=C["text_primary"])
        self.word_label.pack(side="right")

        self.word_slider = ctk.CTkSlider(
            self.pp_frame, from_=3, to=8, number_of_steps=5,
            fg_color=C["border"], progress_color=C["accent"],
            button_color=C["accent"], button_hover_color=C["accent_hover"],
            command=self._on_word_change,
        )
        self.word_slider.set(4)
        self.word_slider.pack(fill="x", pady=(0, 10))

        sep_row = ctk.CTkFrame(self.pp_frame, fg_color="transparent")
        sep_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(sep_row, text="Separator", font=ctk.CTkFont(size=12), text_color=C["text_secondary"]).pack(side="left")
        self.sep_var = ctk.StringVar(value="-")
        ctk.CTkSegmentedButton(
            sep_row, values=["-", ".", "_", " "], variable=self.sep_var,
            font=ctk.CTkFont(size=12), fg_color=C["bg_input"],
            selected_color=C["accent"], selected_hover_color=C["accent_hover"],
            unselected_color=C["bg_input"],
            command=lambda v: self._generate(),
        ).pack(side="right")

        self.pp_capitalize = ctk.CTkCheckBox(
            self.pp_frame, text="Capitalize", font=ctk.CTkFont(size=12),
            text_color=C["text_secondary"], fg_color=C["accent"],
            hover_color=C["accent_hover"], command=self._generate,
        )
        self.pp_capitalize.select()
        self.pp_capitalize.pack(anchor="w", pady=2)

        self.pp_number = ctk.CTkCheckBox(
            self.pp_frame, text="Include number", font=ctk.CTkFont(size=12),
            text_color=C["text_secondary"], fg_color=C["accent"],
            hover_color=C["accent_hover"], command=self._generate,
        )
        self.pp_number.select()
        self.pp_number.pack(anchor="w", pady=2)

        # Buttons
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame, text="↻  Regenerate", font=ctk.CTkFont(size=13),
            height=42, fg_color=C["bg_card"], hover_color=C["bg_hover"],
            border_width=1, border_color=C["border"],
            text_color=C["text_primary"], corner_radius=10,
            command=self._generate,
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            btn_frame, text="✓  Use This", font=ctk.CTkFont(size=13, weight="bold"),
            height=42, fg_color=C["accent"], hover_color=C["accent_hover"],
            corner_radius=10, command=self._accept,
        ).pack(side="right", fill="x", expand=True)

    def _on_mode_change(self):
        if self.mode_var.get() == "password":
            self.pp_frame.pack_forget()
            self.pw_frame.pack(fill="x")
        else:
            self.pw_frame.pack_forget()
            self.pp_frame.pack(fill="x")
        self._generate()

    def _on_length_change(self, val):
        self.length_label.configure(text=str(int(val)))
        self._generate()

    def _on_word_change(self, val):
        self.word_label.configure(text=str(int(val)))
        self._generate()

    def _generate(self, *args):
        C = get_colors()
        try:
            if self.mode_var.get() == "password":
                self.generated_password = generate_password(
                    length=int(self.length_slider.get()),
                    use_lowercase=self.checkboxes["lower"].get(),
                    use_uppercase=self.checkboxes["upper"].get(),
                    use_digits=self.checkboxes["digits"].get(),
                    use_symbols=self.checkboxes["symbols"].get(),
                    exclude_ambiguous=self.checkboxes["ambiguous"].get(),
                )
            else:
                self.generated_password = generate_passphrase(
                    word_count=int(self.word_slider.get()),
                    separator=self.sep_var.get(),
                    capitalize=self.pp_capitalize.get(),
                    include_number=self.pp_number.get(),
                )

            self.output_label.configure(text=self.generated_password)

            result = estimate_strength(self.generated_password)
            entropy = result["entropy_bits"]
            color = get_strength_color(result["strength"])

            if entropy < 28: lit = 1
            elif entropy < 36: lit = 2
            elif entropy < 60: lit = 3
            elif entropy < 80: lit = 4
            else: lit = 5

            for i, seg in enumerate(self.segments):
                seg.configure(fg_color=color if i < lit else C["border"])

            self.strength_label.configure(
                text=f"{result['strength']}  ·  {result['entropy_bits']} bits",
                text_color=color,
            )
        except ValueError as e:
            self.output_label.configure(text=str(e))

    def _accept(self):
        if self.generated_password:
            self.on_accept(self.generated_password)
        self.destroy()
