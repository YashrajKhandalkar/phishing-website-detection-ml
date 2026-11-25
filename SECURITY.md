# Security Policy

This is an educational project. It is not a production security product and has no guaranteed support window.

## Reporting a vulnerability

Please do **not** open a public issue for a security problem. Use GitHub's **Security → Report a vulnerability** (private advisory) on this repository, or contact the maintainer through the email on their GitHub profile.

## Scope and known limitations

- The optional page inspector (`src/page_inspector.py`) validates the destination (public IPs only, ports 80/443, no embedded credentials, redirect re-validation) before every request. The check resolves DNS first and `requests` resolves it again when connecting, so a hostile DNS server could in principle answer differently (DNS rebinding). Treat the inspector as a best-effort learning feature and do not expose the Streamlit app to untrusted users on a network that can reach internal services.
- Model output is a statistical estimate and must not be used as the sole basis for a security decision.
- Never enter private URLs, tokens or password-reset links into the app.
