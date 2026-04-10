# Plan: Add Input Validation (search-002)

## Task
Add input validation to an existing REST API endpoint. Validate email format, required fields, string length limits. Return proper 400 errors with descriptive messages.

## Assumptions
- Python-based API with no framework (pure functions simulating endpoint)
- Contact form endpoint with name, email, message fields
- Validation returns structured error objects with field name and message

## Features & Coverage Matrix

### F1: Required Field Validation
- [x] Missing fields detected and reported
- [x] Null/None fields rejected
- [x] Empty/whitespace-only strings rejected
- [x] Non-string types rejected

### F2: Email Format Validation
- [x] Valid emails accepted (standard, subdomains)
- [x] Invalid emails rejected (no @, no TLD, double @)
- [x] Email regex covers common patterns

### F3: String Length Limits
- [x] name ≤ 100, email ≤ 254, message ≤ 1000
- [x] Boundary values pass (exact max length)
- [x] Over-limit values rejected with descriptive error

### F4: HTTP Error Response Format
- [x] Valid input → 200 with cleaned data
- [x] Invalid input → 400 with error list
- [x] Error messages are descriptive (include field name)
- [x] Cleaned data has whitespace stripped

### F5: Non-dict Body Handling
- [x] Non-dict input returns structured error
