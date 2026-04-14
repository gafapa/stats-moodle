"""
Runtime i18n helpers for the desktop app.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict

import customtkinter as ctk
from tkinter import filedialog, messagebox

from .i18n_data import EXACT, PATTERNS


SUPPORTED_LANGUAGES: Dict[str, str] = {
    "es": "Español",
    "gl": "Galego",
    "en": "English",
    "fr": "Français",
    "de": "Deutsch",
    "ca": "Català",
    "eu": "Euskara",
}
DEFAULT_LANGUAGE = "es"

SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".moodle_analyzer")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "ui_settings.json")


def _ensure_dir() -> None:
    os.makedirs(SETTINGS_DIR, exist_ok=True)


def load_language() -> str:
    _ensure_dir()
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_LANGUAGE
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return DEFAULT_LANGUAGE
    lang = data.get("language", DEFAULT_LANGUAGE)
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def save_language(lang: str) -> None:
    _ensure_dir()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as handle:
        json.dump({"language": lang}, handle, ensure_ascii=False, indent=2)


_current_language = load_language()


def get_language() -> str:
    return _current_language


def set_language(lang: str) -> None:
    global _current_language
    _current_language = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    save_language(_current_language)


def current_language_name() -> str:
    return SUPPORTED_LANGUAGES.get(get_language(), SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])


def code_from_name(name: str) -> str:
    for code, label in SUPPORTED_LANGUAGES.items():
        if label == name:
            return code
    return DEFAULT_LANGUAGE


def report_language_name(code: str | None = None) -> str:
    return {
        "es": "Spanish",
        "gl": "Galician",
        "en": "English",
        "fr": "French",
        "de": "German",
        "ca": "Catalan",
        "eu": "Basque",
    }.get(code or get_language(), "Spanish")


def _text_variants(text: str) -> list[str]:
    variants = [text]
    transforms = (
        ("utf-8", "latin1"),
        ("utf-8", "cp1252"),
        ("latin1", "utf-8"),
        ("cp1252", "utf-8"),
    )
    for source_encoding, target_encoding in transforms:
        try:
            candidate = text.encode(source_encoding).decode(target_encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if candidate not in variants:
            variants.append(candidate)
    return variants


def _translate_lookup(text: str, target: str) -> str | None:
    for candidate in _text_variants(text):
        direct = EXACT.get(candidate)
        if direct and target in direct:
            return direct[target]
        for pattern, mapping in PATTERNS:
            match = pattern.match(candidate)
            if match and target in mapping:
                values = {
                    key: translate_text(value, target) if isinstance(value, str) else value
                    for key, value in match.groupdict().items()
                }
                return mapping[target].format(**values)
    return None


def translate_text(text: Any, lang: str | None = None) -> Any:
    if not isinstance(text, str):
        return text
    target = lang or get_language()
    if target == DEFAULT_LANGUAGE or not text:
        return text
    leading = len(text) - len(text.lstrip())
    trailing = len(text) - len(text.rstrip())
    if leading or trailing:
        core = text.strip()
        if not core:
            return text
        translated_core = translate_text(core, target)
        if translated_core != core:
            return f"{text[:leading]}{translated_core}{text[len(text) - trailing:] if trailing else ''}"
    translated = _translate_lookup(text, target)
    if translated is not None:
        return translated
    icon_match = re.match(r"^([^\w\s]+(?:\s+[^\w\s]+)*\s+)(.+)$", text)
    if icon_match:
        prefix, remainder = icon_match.groups()
        translated_remainder = _translate_lookup(remainder, target)
        if translated_remainder is not None:
            return f"{prefix}{translated_remainder}"
    return text


def translate_data(value: Any, lang: str | None = None) -> Any:
    target = lang or get_language()
    if isinstance(value, str):
        return translate_text(value, target)
    if isinstance(value, list):
        return [translate_data(item, target) for item in value]
    if isinstance(value, tuple):
        return tuple(translate_data(item, target) for item in value)
    if isinstance(value, dict):
        return {translate_data(key, target): translate_data(item, target) for key, item in value.items()}
    return value


def translate_figure(fig: Any) -> None:
    try:
        if getattr(fig, "_i18n_applied_language", None) == get_language():
            return
        if getattr(fig, "_suptitle", None) is not None:
            fig._suptitle.set_text(translate_text(fig._suptitle.get_text()))
        for text in getattr(fig, "texts", []):
            text.set_text(translate_text(text.get_text()))
        for ax in fig.get_axes():
            ax.set_title(translate_text(ax.get_title()))
            ax.set_xlabel(translate_text(ax.get_xlabel()))
            ax.set_ylabel(translate_text(ax.get_ylabel()))
            for label in ax.get_xticklabels():
                label.set_text(translate_text(label.get_text()))
            for label in ax.get_yticklabels():
                label.set_text(translate_text(label.get_text()))
            for text in ax.texts:
                text.set_text(translate_text(text.get_text()))
            legend = ax.get_legend()
            if legend is not None:
                if legend.get_title() is not None:
                    legend.get_title().set_text(translate_text(legend.get_title().get_text()))
                for item in legend.get_texts():
                    item.set_text(translate_text(item.get_text()))
        fig._i18n_applied_language = get_language()
    except Exception:
        pass


_installed = False
_patched_classes: Dict[type, Any] = {}


def _patch_widget_class(cls: type) -> None:
    original_init = cls.__init__
    original_configure = cls.configure
    _patched_classes[cls] = original_configure

    def __init__(self, *args, **kwargs):
        if isinstance(kwargs.get("text"), str):
            self._i18n_source_text = kwargs["text"]
            kwargs["text"] = translate_text(kwargs["text"])
        if isinstance(kwargs.get("placeholder_text"), str):
            self._i18n_source_placeholder = kwargs["placeholder_text"]
            kwargs["placeholder_text"] = translate_text(kwargs["placeholder_text"])
        original_init(self, *args, **kwargs)

    def configure(self, require_redraw=False, **kwargs):
        if getattr(self, "_i18n_refreshing", False):
            return original_configure(self, require_redraw=require_redraw, **kwargs)
        if isinstance(kwargs.get("text"), str):
            self._i18n_source_text = kwargs["text"]
            kwargs["text"] = translate_text(kwargs["text"])
        if isinstance(kwargs.get("placeholder_text"), str):
            self._i18n_source_placeholder = kwargs["placeholder_text"]
            kwargs["placeholder_text"] = translate_text(kwargs["placeholder_text"])
        return original_configure(self, require_redraw=require_redraw, **kwargs)

    cls.__init__ = __init__
    cls.configure = configure


def refresh_widget_tree(widget: Any) -> None:
    original_configure = _patched_classes.get(type(widget))
    if hasattr(widget, "_i18n_source_text") and original_configure:
        widget._i18n_refreshing = True
        try:
            original_configure(widget, text=translate_text(widget._i18n_source_text))
        finally:
            widget._i18n_refreshing = False
    if hasattr(widget, "_i18n_source_placeholder") and original_configure:
        widget._i18n_refreshing = True
        try:
            original_configure(widget, placeholder_text=translate_text(widget._i18n_source_placeholder))
        finally:
            widget._i18n_refreshing = False

    try:
        children = widget.winfo_children()
    except Exception:
        children = []
    for child in children:
        refresh_widget_tree(child)


def install_runtime_translations() -> None:
    global _installed
    if _installed:
        return
    _installed = True

    for cls in (ctk.CTkLabel, ctk.CTkButton, ctk.CTkCheckBox, ctk.CTkEntry):
        _patch_widget_class(cls)

    for name in ("showerror", "showinfo", "showwarning", "askyesno"):
        original = getattr(messagebox, name)

        def wrapper(title, message=None, *args, __orig=original, **kwargs):
            return __orig(translate_text(title), translate_text(message), *args, **kwargs)

        setattr(messagebox, name, wrapper)

    original_save = filedialog.asksaveasfilename

    def asksaveasfilename(*args, **kwargs):
        if isinstance(kwargs.get("title"), str):
            kwargs["title"] = translate_text(kwargs["title"])
        return original_save(*args, **kwargs)

    filedialog.asksaveasfilename = asksaveasfilename
