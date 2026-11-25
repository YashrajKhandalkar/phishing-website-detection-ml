"""Offline tests for URL normalization and the 32-feature extractor."""
import math

import pytest

from src.url_features import FEATURE_NAMES, extract_url_features, normalize_user_url

SAMPLE = "https://secure-login.example.com/account/verify?user=123&next=%2Fhome"


def test_feature_schema_is_stable_and_finite():
    features = extract_url_features(normalize_user_url(SAMPLE))
    assert list(features) == FEATURE_NAMES
    assert len(FEATURE_NAMES) == 32
    assert len(set(FEATURE_NAMES)) == 32
    assert all(math.isfinite(value) for value in features.values())


def test_extraction_is_deterministic():
    assert extract_url_features(SAMPLE) == extract_url_features(SAMPLE)


def test_known_feature_values():
    f = extract_url_features(SAMPLE)
    assert f["is_https"] == 1.0
    assert f["subdomain_count"] == 1.0
    assert f["has_hyphen_in_domain"] == 1.0
    assert f["has_obfuscation"] == 1.0
    assert f["query_param_count"] == 2.0
    assert f["path_depth"] == 2.0
    assert f["suspicious_keyword_count"] >= 3  # secure, login, account, verify
    assert f["is_domain_ip"] == 0.0


def test_ip_host_punycode_shortener_credentials_and_port():
    assert extract_url_features("http://192.168.1.10/login")["is_domain_ip"] == 1.0
    assert extract_url_features("https://xn--pple-43d.com")["has_punycode"] == 1.0
    assert extract_url_features("https://bit.ly/abc123")["uses_shortener"] == 1.0
    assert extract_url_features("https://user:pw@example.com")["has_credentials"] == 1.0
    assert extract_url_features("https://example.com:8443")["nonstandard_port"] == 1.0
    assert extract_url_features("https://example.com:443")["nonstandard_port"] == 0.0
    assert extract_url_features("http://example.com@evil.test")["has_at_symbol"] == 1.0


def test_normalize_adds_https_scheme():
    assert normalize_user_url("example.com") == "https://example.com"
    assert normalize_user_url("  http://example.com/a  ") == "http://example.com/a"


def test_normalize_rejects_bad_input():
    bad_inputs = [
        "",
        "   ",
        "ftp://example.com",
        "file:///etc/passwd",
        "javascript://example.com",
        "https://exa mple.com",
        "https://localhost",
        "https://example.com:99999",
    ]
    for value in bad_inputs:
        with pytest.raises(ValueError):
            normalize_user_url(value)
