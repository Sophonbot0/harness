import re

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

REQUIRED_FIELDS = ['name', 'email', 'message']
MAX_LENGTHS = {'name': 100, 'email': 254, 'message': 1000}


def validate_input(data: dict):
    """Validate input data. Returns (cleaned_data, errors_list).
    errors_list is empty on success."""
    errors = []

    if not isinstance(data, dict):
        return None, [{'field': '_body', 'message': 'Request body must be a JSON object'}]

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            errors.append({'field': field, 'message': f"'{field}' is required"})
        elif not isinstance(data[field], str):
            errors.append({'field': field, 'message': f"'{field}' must be a string"})
        elif data[field].strip() == '':
            errors.append({'field': field, 'message': f"'{field}' must not be empty"})

    if errors:
        return None, errors

    # Length limits
    for field, max_len in MAX_LENGTHS.items():
        if len(data[field]) > max_len:
            errors.append({'field': field,
                           'message': f"'{field}' must be at most {max_len} characters"})

    # Email format
    if 'email' in data and isinstance(data.get('email'), str):
        if not EMAIL_REGEX.match(data['email']):
            errors.append({'field': 'email', 'message': "'email' must be a valid email address"})

    if errors:
        return None, errors

    return {f: data[f].strip() for f in REQUIRED_FIELDS}, []


def handle_contact(data: dict):
    """Simulate endpoint handler. Returns (response_body, status_code)."""
    cleaned, errors = validate_input(data)
    if errors:
        return {'status': 'error', 'errors': errors}, 400
    return {'status': 'ok', 'data': cleaned}, 200
