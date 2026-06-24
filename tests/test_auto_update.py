import pytest
from modules.auto_update import _compare_versions


class TestCompareVersions:
    def test_equal(self):
        assert _compare_versions("1.0.0", "1.0.0") == 0

    def test_newer_major(self):
        assert _compare_versions("2.0.0", "1.0.0") > 0

    def test_older_major(self):
        assert _compare_versions("1.0.0", "2.0.0") < 0

    def test_newer_minor(self):
        assert _compare_versions("1.2.0", "1.1.0") > 0

    def test_newer_patch(self):
        assert _compare_versions("1.0.2", "1.0.1") > 0

    def test_different_lengths(self):
        assert _compare_versions("1.0.0.0", "1.0.0") > 0
        assert _compare_versions("1.0.0", "1.0.0.0") < 0

    def test_same_major_different_minor(self):
        assert _compare_versions("1.5.0", "1.4.9") > 0

    def test_negative_older(self):
        assert _compare_versions("0.9.0", "1.0.0") < 0
