# URL Feature Dictionary

The project uses the same `extract_url_features()` function during training and prediction. All features are derived locally from the URL string; the extractor does not open the website.

| Feature | Meaning |
|---|---|
| `url_length` | Number of characters in the normalized URL string |
| `domain_length` | Number of characters in the hostname |
| `is_domain_ip` | 1 when the hostname is an IP address; otherwise 0 |
| `tld_length` | Number of characters in the final hostname label |
| `subdomain_count` | Approximate labels before the registrable-domain and TLD labels |
| `has_punycode` | 1 when a hostname label begins with `xn--` |
| `has_obfuscation` | 1 when one or more percent-encoded octets such as `%2F` occur |
| `obfuscated_char_count` | Count of percent-encoded octets multiplied by three characters |
| `obfuscation_ratio` | Obfuscated character count divided by URL length |
| `letter_count` | Number of alphabetic characters in the URL |
| `letter_ratio` | Letter count divided by URL length |
| `digit_count` | Number of digits in the URL |
| `digit_ratio` | Digit count divided by URL length |
| `equals_count` | Count of `=` characters |
| `question_count` | Count of `?` characters |
| `ampersand_count` | Count of `&` characters |
| `other_special_char_count` | Count of selected less-common punctuation characters |
| `special_char_ratio` | Punctuation count divided by URL length |
| `is_https` | 1 when the URL uses the HTTPS scheme; otherwise 0 |
| `has_at_symbol` | 1 when `@` occurs in the URL |
| `has_hyphen_in_domain` | 1 when the hostname contains a hyphen |
| `uses_shortener` | 1 when the hostname is in the extractor's known shortener list |
| `path_depth` | Number of non-empty path segments |
| `path_length` | Number of characters in the URL path |
| `query_length` | Number of characters in the query string |
| `query_param_count` | Number of parsed query-string parameters |
| `fragment_length` | Number of characters in the fragment |
| `url_entropy` | Shannon entropy of characters in the URL string |
| `suspicious_keyword_count` | Count of selected security/account-related terms found in URL text |
| `host_digit_ratio` | Hostname digit count divided by hostname length |
| `has_credentials` | 1 when username or password syntax occurs in URL authority |
| `nonstandard_port` | 1 when an explicit port differs from the scheme's default port |

These are project-defined lexical/domain indicators. They are not the UCI 327 ternary feature codes and should not be explained as identical to the older 30-feature Phishing Websites benchmark.
