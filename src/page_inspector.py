"""Optional defensive HTML inspection with basic SSRF safeguards.

This module makes a small GET request only after the user explicitly clicks
Inspect. It blocks private/local IP targets, non-HTTP schemes, non-standard
ports, credentials in URLs, and redirects to blocked destinations. It does not
execute JavaScript, submit forms, use cookies, or download page assets.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from src.url_features import normalize_user_url

MAX_BYTES = 1_500_000
MAX_REDIRECTS = 4
TIMEOUT_SECONDS = 6
USER_AGENT = "EducationalPhishingURLAnalyzer/1.0 (+local student project)"


def _resolve_public_host(host: str, port: int) -> list[str]:
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError(f"DNS lookup failed for {host}: {exc}") from exc
    addresses = sorted({record[4][0].split("%", 1)[0] for record in records})
    if not addresses:
        raise ValueError("The hostname did not resolve to an IP address.")
    for address in addresses:
        ip_obj = ipaddress.ip_address(address)
        if not ip_obj.is_global:
            raise ValueError("For safety, page inspection is blocked for private, local, reserved, or non-public IP addresses.")
    return addresses


def _validate_public_url(raw_url: str) -> tuple[str, str, int]:
    url = normalize_user_url(raw_url)
    parsed = urlsplit(url)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URLs containing embedded usernames or passwords are not inspected.")
    host = parsed.hostname or ""
    try:
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise ValueError(f"Invalid port: {exc}") from exc
    if port not in {80, 443}:
        raise ValueError("For safety, optional page inspection only allows standard HTTP (80) and HTTPS (443) ports.")
    if host.lower() in {"localhost", "localhost.localdomain"} or host.lower().endswith((".local", ".internal", ".localhost")):
        raise ValueError("Local or internal hostnames are not inspected.")
    _resolve_public_host(host, port)
    return url, host, port


def inspect_public_page(raw_url: str) -> dict:
    """Fetch and inspect a small amount of public HTML after validation."""
    current_url, _, _ = _validate_public_url(raw_url)
    session = requests.Session()
    session.trust_env = False  # ignore environment proxy variables for this feature
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1"}
    redirects = 0
    response = None
    body = bytearray()
    try:
        while True:
            _, host, port = _validate_public_url(current_url)
            response = session.get(
                current_url, headers=headers, timeout=TIMEOUT_SECONDS,
                allow_redirects=False, stream=True, verify=True,
            )
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise ValueError("The website returned a redirect without a Location header.")
                if redirects >= MAX_REDIRECTS:
                    raise ValueError(f"Redirect limit ({MAX_REDIRECTS}) reached.")
                current_url = urljoin(current_url, location)
                redirects += 1
                continue
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                response.close()
                raise ValueError(f"The destination did not return HTML (Content-Type: {content_type or 'unknown'}).")
            for chunk in response.iter_content(chunk_size=32_768):
                if not chunk:
                    continue
                remaining = MAX_BYTES - len(body)
                body.extend(chunk[:remaining])
                if len(body) >= MAX_BYTES:
                    break
            status_code = int(response.status_code)
            final_url = response.url
            encoding = response.encoding or "utf-8"
            response.close()
            break

        html = bytes(body).decode(encoding, errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        final_host = (urlsplit(final_url).hostname or "").lower()

        def _host_of(value: str) -> str:
            if not value:
                return ""
            try:
                return (urlsplit(urljoin(final_url, value)).hostname or "").lower()
            except ValueError:
                return ""

        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        description_tag = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "description"})
        description = str(description_tag.get("content", "")).strip() if description_tag else ""
        links = soup.find_all("a", href=True)
        hrefs = [str(a.get("href", "")).strip() for a in links]
        empty_links = sum(not href or href == "#" or href.lower().startswith("javascript:") for href in hrefs)
        external_links = sum(bool(_host_of(href)) and _host_of(href) != final_host for href in hrefs)
        same_host_links = sum(bool(_host_of(href)) and _host_of(href) == final_host for href in hrefs)

        forms = soup.find_all("form")
        external_form_targets = 0
        for form in forms:
            action = str(form.get("action", "")).strip()
            if action and _host_of(action) and _host_of(action) != final_host:
                external_form_targets += 1
        password_fields = len(soup.find_all("input", attrs={"type": lambda v: v and v.lower() == "password"}))
        hidden_fields = len(soup.find_all("input", attrs={"type": lambda v: v and v.lower() == "hidden"}))
        iframes = soup.find_all("iframe")
        scripts = soup.find_all("script")
        images = soup.find_all("img")
        stylesheets = soup.find_all("link", rel=lambda v: v and "stylesheet" in [str(x).lower() for x in (v if isinstance(v, list) else [v])])
        popup_count = html.lower().count("window.open")
        mouseover_count = sum(1 for tag in soup.find_all(True) if tag.has_attr("onmouseover"))
        rightclick_count = sum(1 for tag in soup.find_all(True) if tag.has_attr("oncontextmenu"))
        favicon_tags = soup.find_all("link", rel=lambda v: v and "icon" in " ".join(v if isinstance(v, list) else [str(v)]).lower())
        favicon_hosts = [_host_of(str(tag.get("href", ""))) for tag in favicon_tags]
        favicon_external = sum(bool(h) and h != final_host for h in favicon_hosts)
        asset_tags = soup.find_all(["img", "script", "link", "source", "video", "audio"])
        asset_urls = [str(tag.get("src") or tag.get("href") or "").strip() for tag in asset_tags]
        external_assets = sum(bool(_host_of(value)) and _host_of(value) != final_host for value in asset_urls)
        social_domains = ("facebook.com", "instagram.com", "linkedin.com", "youtube.com", "x.com", "twitter.com")
        social_links = sum(any(domain in (_host_of(href) or "") for domain in social_domains) for href in hrefs)

        return {
            "requested_url": raw_url,
            "final_url": final_url,
            "http_status": status_code,
            "redirects_followed": redirects,
            "dns_resolved_to_public_ip": True,
            "https_certificate_verified": final_url.lower().startswith("https://"),
            "html_bytes_inspected": len(body),
            "content_truncated_at_limit": len(body) >= MAX_BYTES,
            "page_title": title[:300],
            "has_meta_description": bool(description),
            "form_count": len(forms),
            "external_form_targets": external_form_targets,
            "password_input_count": password_fields,
            "hidden_input_count": hidden_fields,
            "iframe_count": len(iframes),
            "script_count": len(scripts),
            "image_count": len(images),
            "stylesheet_count": len(stylesheets),
            "anchor_count": len(links),
            "external_anchor_count": external_links,
            "same_host_anchor_count": same_host_links,
            "empty_or_javascript_anchor_count": empty_links,
            "external_asset_count": external_assets,
            "external_favicon_count": favicon_external,
            "social_link_count": social_links,
            "window_open_occurrences": popup_count,
            "onmouseover_handler_count": mouseover_count,
            "oncontextmenu_handler_count": rightclick_count,
            "note": "Supplementary HTML observations only; these values are not fed into the URL ML classifier.",
        }
    except requests.exceptions.SSLError as exc:
        raise ValueError(f"HTTPS certificate verification failed: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise ValueError(f"Could not fetch the public page: {exc}") from exc
    finally:
        if response is not None:
            response.close()
        session.close()
