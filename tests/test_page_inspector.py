"""Offline tests for the optional page inspector's destination guards.

Every URL below is rejected before any HTTP request is made.
"""
import pytest

from src.page_inspector import _validate_public_url

BLOCKED = [
    "http://127.0.0.1",
    "http://localhost",
    "http://app.internal",
    "http://10.0.0.2",
    "http://192.168.1.1",
    "http://169.254.169.254/latest/meta-data",
    "http://[::1]",
    "file:///etc/passwd",
    "ftp://example.com",
    "https://user:secret@example.com",
    "https://example.com:8443",
]


def test_private_local_and_non_web_targets_are_blocked():
    for url in BLOCKED:
        with pytest.raises(ValueError):
            _validate_public_url(url)
