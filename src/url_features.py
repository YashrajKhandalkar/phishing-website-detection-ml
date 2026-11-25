"""Deterministic URL-only feature extraction shared by training and inference.

The extractor deliberately does not visit the supplied URL. Every feature is
computed from the URL string itself so training-time and prediction-time
representations are identical.
"""
from __future__ import annotations

import ipaddress
import math
import re
import string
from collections import Counter
from urllib.parse import parse_qsl, urlsplit

FEATURE_NAMES = [
    "url_length",
    "domain_length",
    "is_domain_ip",
    "tld_length",
    "subdomain_count",
    "has_punycode",
    "has_obfuscation",
    "obfuscated_char_count",
    "obfuscation_ratio",
    "letter_count",
    "letter_ratio",
    "digit_count",
    "digit_ratio",
    "equals_count",
    "question_count",
    "ampersand_count",
    "other_special_char_count",
    "special_char_ratio",
    "is_https",
    "has_at_symbol",
    "has_hyphen_in_domain",
    "uses_shortener",
    "path_depth",
    "path_length",
    "query_length",
    "query_param_count",
    "fragment_length",
    "url_entropy",
    "suspicious_keyword_count",
    "host_digit_ratio",
    "has_credentials",
    "nonstandard_port",
]

SHORTENER_DOMAINS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd",
    "buff.ly", "adf.ly", "cutt.ly", "tiny.cc", "rb.gy", "shorturl.at",
    "rebrand.ly", "lnkd.in", "soo.gd", "s.id", "trib.al",
}
SUSPICIOUS_KEYWORDS = {
    "login", "signin", "verify", "verification", "secure", "account",
    "update", "password", "confirm", "wallet", "banking", "payment",
    "billing", "recover", "suspend", "unlock", "authenticate", "webscr",
}
_OBFUSCATED_RE = re.compile(r"%[0-9a-fA-F]{2}")
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")


def _candidate_url(raw_url: str) -> str:
    text = str(raw_url or "").strip()
    if not text:
        raise ValueError("Please enter a website URL.")
    if not _SCHEME_RE.match(text):
        text = "https://" + text.lstrip("/")
    return text


def normalize_user_url(raw_url: str) -> str:
    """Normalize a user-entered URL and reject non-web schemes / malformed URLs."""
    candidate = _candidate_url(raw_url)
    try:
        parsed = urlsplit(candidate)
        host = parsed.hostname
        # Accessing .port validates malformed/out-of-range port values.
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(f"Invalid URL: {exc}") from exc
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Only http:// and https:// website URLs are supported.")
    if not host or "." not in host and not _is_ip(host):
        raise ValueError("Enter a public domain such as example.com or a public IP address.")
    if any(ch.isspace() for ch in candidate):
        raise ValueError("The URL cannot contain spaces. Encode spaces as %20.")
    return candidate


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    length = len(text)
    return float(-sum((count / length) * math.log2(count / length) for count in counts.values()))


def _extract_host(parsed) -> str:
    try:
        return (parsed.hostname or "").strip(".").lower()
    except ValueError:
        return ""


def extract_url_features(raw_url: str) -> dict[str, float]:
    """Return the fixed numeric URL feature vector used for both training/inference."""
    candidate = _candidate_url(raw_url)
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError:
        parsed = urlsplit("https://invalid.invalid/")
        port = None

    host = _extract_host(parsed)
    host_labels = [part for part in host.split(".") if part]
    path = parsed.path or ""
    query = parsed.query or ""
    fragment = parsed.fragment or ""
    lower_url = candidate.lower()
    host_is_ip = _is_ip(host)
    tld = "" if host_is_ip or not host_labels else host_labels[-1]
    subdomains = max(0, len(host_labels) - 2) if not host_is_ip else 0

    obfuscated = _OBFUSCATED_RE.findall(candidate)
    letters = sum(ch.isalpha() for ch in candidate)
    digits = sum(ch.isdigit() for ch in candidate)
    # Characters that add URL structure/obfuscation beyond alphanumerics and
    # the common separators counted separately below.
    other_special = sum(ch in "!$'()*+,;[]^\\\"<>" for ch in candidate)
    special = sum(ch in string.punctuation for ch in candidate)
    safe_len = max(1, len(candidate))
    host_len = max(1, len(host))

    try:
        params = parse_qsl(query, keep_blank_values=True, strict_parsing=False)
    except ValueError:
        params = []

    host_for_shortener = host[4:] if host.startswith("www.") else host
    uses_shortener = host_for_shortener in SHORTENER_DOMAINS
    suspicious_count = sum(1 for word in SUSPICIOUS_KEYWORDS if word in lower_url)
    try:
        explicit_port = parsed.port
    except ValueError:
        explicit_port = None
    default_port = 443 if parsed.scheme.lower() == "https" else 80

    features = {
        "url_length": float(len(candidate)),
        "domain_length": float(len(host)),
        "is_domain_ip": float(host_is_ip),
        "tld_length": float(len(tld)),
        "subdomain_count": float(subdomains),
        "has_punycode": float(any(label.startswith("xn--") for label in host_labels)),
        "has_obfuscation": float(bool(obfuscated)),
        "obfuscated_char_count": float(len(obfuscated) * 3),
        "obfuscation_ratio": float((len(obfuscated) * 3) / safe_len),
        "letter_count": float(letters),
        "letter_ratio": float(letters / safe_len),
        "digit_count": float(digits),
        "digit_ratio": float(digits / safe_len),
        "equals_count": float(candidate.count("=")),
        "question_count": float(candidate.count("?")),
        "ampersand_count": float(candidate.count("&")),
        "other_special_char_count": float(other_special),
        "special_char_ratio": float(special / safe_len),
        "is_https": float(parsed.scheme.lower() == "https"),
        "has_at_symbol": float("@" in candidate),
        "has_hyphen_in_domain": float("-" in host),
        "uses_shortener": float(uses_shortener),
        "path_depth": float(len([part for part in path.split("/") if part])),
        "path_length": float(len(path)),
        "query_length": float(len(query)),
        "query_param_count": float(len(params)),
        "fragment_length": float(len(fragment)),
        "url_entropy": float(_entropy(candidate)),
        "suspicious_keyword_count": float(suspicious_count),
        "host_digit_ratio": float(sum(ch.isdigit() for ch in host) / host_len),
        "has_credentials": float(parsed.username is not None or parsed.password is not None),
        "nonstandard_port": float(explicit_port is not None and explicit_port != default_port),
    }
    # Maintain a hard schema contract: this exact order is used by the model.
    return {name: features[name] for name in FEATURE_NAMES}
