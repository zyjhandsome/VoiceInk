import pytest
from voiceink.version import __version__


class TestVersion:
    def test_version_exists(self):
        assert __version__ is not None

    def test_version_format(self):
        parts = __version__.split(".")
        assert len(parts) >= 2
        for part in parts:
            assert part.isdigit() or part.replace(".", "").isalnum()

    def test_version_not_empty(self):
        assert len(__version__) > 0
