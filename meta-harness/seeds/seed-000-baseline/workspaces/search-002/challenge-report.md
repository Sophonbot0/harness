# Challenge Report

## Edge Cases Identified & Addressed

1. **Non-dict body** — validated upfront; returns `_body` field error immediately.
2. **None / null fields** — treated as missing (required-field error), not as empty-string.
3. **Non-string typed fields** (e.g., integer name) — caught before length/regex checks.
4. **Whitespace-only fields** — treated as empty after `.strip()` check.
5. **Email length vs regex order** — length check runs before regex to avoid slow regex on huge strings.
6. **Email too-long boundary** — initial test used 251 chars (under 254 limit); corrected to 255 chars.
7. **Multiple errors returned at once** — all field errors accumulated; early-exit only for non-dict body.
8. **Cleaned data strips whitespace** — output data is stripped, not raw input.

## Known Limitations

- Email regex does not validate internationalized domain names (IDN / punycode).
- No rate-limit or abuse protection (out of scope for this task).
- No Flask/HTTP layer — pure function API; wire-up to Flask trivial.
