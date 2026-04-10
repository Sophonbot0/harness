# Plan: Input Validation for REST API Endpoint

## Features
1. Email format validation (regex)
2. Required field checks (name, email, message)
3. String length limits (name ≤ 100, email ≤ 254, message ≤ 1000)
4. Proper 400 error responses with descriptive JSON messages

## Definition of Done
- [ ] validate_input() function exists and returns (data, errors)
- [ ] Email regex validation rejects invalid formats
- [ ] Required fields return 400 with field-specific error messages
- [ ] String length violations return 400 with descriptive messages
- [ ] All validation tests pass (pytest)
