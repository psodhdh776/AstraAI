"""Tests for assistant module (crypto, utilities)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import pytest


def test_crypto_roundtrip():
    from assistant import encrypt_plaintext, decrypt_plaintext
    original = "AIzaSyTestKey123456789"
    encrypted = encrypt_plaintext(original)
    assert encrypted != original
    assert encrypted != ""
    decrypted = decrypt_plaintext(encrypted)
    assert decrypted == original


def test_crypto_empty():
    from assistant import encrypt_plaintext, decrypt_plaintext
    assert encrypt_plaintext("") == ""
    assert decrypt_plaintext("") == ""


def test_crypto_plaintext_fallback():
    from assistant import decrypt_plaintext
    assert decrypt_plaintext("AIzaSyRawKey") == "AIzaSyRawKey"


def test_md_to_html():
    from chat_widget import _md_to_html
    assert "bold" in _md_to_html("**bold**") and "#ffffff" in _md_to_html("**bold**")
    assert "<i>" in _md_to_html("*italic*") or "italic" in _md_to_html("*italic*")
    assert "code" in _md_to_html("`code`")
    assert "href=" in _md_to_html("[link](http://x.com)")
    assert "<li" in _md_to_html("- list item")
    assert "<li" in _md_to_html("1. numbered")


def test_md_xss():
    from chat_widget import _md_to_html
    result = _md_to_html("<script>alert('xss')</script>")
    assert "&lt;script&gt;" in result
    assert "<script>" not in result
