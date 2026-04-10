# Challenge Report: search-002

## C1: SQL/NoSQL injection in fields
- **Risk**: Malicious strings in name/message not sanitized beyond length
- **Reproduction**: `python3 -c "from api import handle_contact; print(handle_contact({'name': \"'; DROP TABLE--\", 'email': 'a@b.com', 'message': 'hi'}))"`
- **Severity**: LOW — no DB layer exists; validation passes through cleaned strings

## C2: Unicode edge cases in email
- **Risk**: Unicode chars might bypass regex
- **Reproduction**: `python3 -c "from api import validate_input; print(validate_input({'name': 'A', 'email': 'ü@b.com', 'message': 'hi'}))"` 
- **Severity**: LOW — regex rejects non-ASCII in local part

## C3: Extra fields not stripped
- **Risk**: Extra keys in input dict pass through unchecked
- **Reproduction**: `python3 -c "from api import handle_contact; print(handle_contact({'name': 'A', 'email': 'a@b.com', 'message': 'hi', 'admin': True}))"`
- **Severity**: LOW — cleaned output only includes REQUIRED_FIELDS

## C4: Email with spaces accepted after strip?
- **Risk**: Email with leading/trailing spaces
- **Reproduction**: `python3 -c "from api import validate_input; print(validate_input({'name': 'A', 'email': ' a@b.com ', 'message': 'hi'}))"` 
- **Severity**: MEDIUM — email validated before strip, spaces cause rejection (correct behavior)

## C5: Multiple validation errors reported together
- **Risk**: Only first error returned
- **Reproduction**: `python3 -c "from api import validate_input; _, e = validate_input({}); print(len(e))"`
- **Severity**: NONE — returns all 3 errors for empty dict ✓

## C6: Extremely long input DoS
- **Risk**: Very long string before length check
- **Reproduction**: `python3 -c "from api import validate_input; print(validate_input({'name': 'A'*10**7, 'email': 'a@b.com', 'message': 'hi'})[1])"`
- **Severity**: LOW — length check catches it; no regex on name field
