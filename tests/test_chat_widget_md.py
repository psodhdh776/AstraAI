import pytest
from modules.chat_widget import _md_to_html


class TestMdToHtml:
    def test_empty(self):
        assert _md_to_html("") == ""

    def test_plain_text(self):
        result = _md_to_html("hello world")
        assert "hello world" in result

    def test_escapes_html(self):
        result = _md_to_html("<script>alert('xss')</script>")
        assert "&lt;" in result
        assert "&gt;" in result
        assert "<script>" not in result

    def test_bold(self):
        result = _md_to_html("hello **world**")
        assert "<b" in result
        assert "world" in result

    def test_italic(self):
        result = _md_to_html("hello *world*")
        assert "<i>" in result
        assert "world" in result

    def test_inline_code(self):
        result = _md_to_html("use `code` here")
        assert "<code" in result
        assert "code" in result

    def test_link(self):
        result = _md_to_html("[text](https://example.com)")
        assert '<a href="https://example.com"' in result
        assert "text" in result

    def test_code_block(self):
        result = _md_to_html("```python\nprint('hi')\n```")
        assert "<pre" in result
        assert "print('hi')" in result
        assert "python" in result

    def test_unordered_list(self):
        result = _md_to_html("- item")
        assert "<li" in result

    def test_ordered_list(self):
        result = _md_to_html("1. item")
        assert "<li" in result

    def test_newlines(self):
        result = _md_to_html("line1\nline2")
        assert "<br>" in result

    def test_html_unchanged(self):
        result = _md_to_html("<b>raw html</b>")
        assert "<b>raw html</b>" in result

    def test_mixed_formatting(self):
        text = "**bold** and *italic* with `code`"
        result = _md_to_html(text)
        assert "<b" in result
        assert "<i" in result or "<i>" in result
        assert "<code" in result

    def test_ampersand_escaped(self):
        result = _md_to_html("a & b")
        assert "&amp;" in result

    def test_multiline_code_block(self):
        result = _md_to_html("```\nline1\nline2\n```")
        assert "<pre" in result
        assert "line1" in result
        assert "line2" in result
