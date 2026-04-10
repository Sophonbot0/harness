import pytest
from api import validate_input, handle_contact


# ── Required field tests ──────────────────────────────────────────────────────

def test_missing_name():
    _, errors = validate_input({'email': 'a@b.com', 'message': 'hi'})
    fields = [e['field'] for e in errors]
    assert 'name' in fields

def test_missing_email():
    _, errors = validate_input({'name': 'Alice', 'message': 'hi'})
    fields = [e['field'] for e in errors]
    assert 'email' in fields

def test_missing_message():
    _, errors = validate_input({'name': 'Alice', 'email': 'a@b.com'})
    fields = [e['field'] for e in errors]
    assert 'message' in fields

def test_empty_name():
    _, errors = validate_input({'name': '   ', 'email': 'a@b.com', 'message': 'hi'})
    fields = [e['field'] for e in errors]
    assert 'name' in fields

def test_all_missing():
    _, errors = validate_input({})
    assert len(errors) == 3

def test_non_dict_body():
    _, errors = validate_input("not a dict")
    assert errors[0]['field'] == '_body'

def test_null_field():
    _, errors = validate_input({'name': None, 'email': 'a@b.com', 'message': 'hi'})
    fields = [e['field'] for e in errors]
    assert 'name' in fields

def test_non_string_field():
    _, errors = validate_input({'name': 123, 'email': 'a@b.com', 'message': 'hi'})
    fields = [e['field'] for e in errors]
    assert 'name' in fields


# ── Email validation tests ────────────────────────────────────────────────────

def test_valid_email():
    data, errors = validate_input({'name': 'Alice', 'email': 'alice@example.com', 'message': 'hello'})
    assert errors == []

def test_invalid_email_no_at():
    _, errors = validate_input({'name': 'Alice', 'email': 'aliceexample.com', 'message': 'hi'})
    fields = [e['field'] for e in errors]
    assert 'email' in fields

def test_invalid_email_no_tld():
    _, errors = validate_input({'name': 'Alice', 'email': 'alice@example', 'message': 'hi'})
    fields = [e['field'] for e in errors]
    assert 'email' in fields

def test_invalid_email_double_at():
    _, errors = validate_input({'name': 'Alice', 'email': 'a@@b.com', 'message': 'hi'})
    fields = [e['field'] for e in errors]
    assert 'email' in fields

def test_valid_subdomain_email():
    data, errors = validate_input({'name': 'Bob', 'email': 'bob@mail.example.co.uk', 'message': 'hey'})
    assert errors == []


# ── Length limit tests ────────────────────────────────────────────────────────

def test_name_too_long():
    _, errors = validate_input({'name': 'A' * 101, 'email': 'a@b.com', 'message': 'hi'})
    fields = [e['field'] for e in errors]
    assert 'name' in fields

def test_name_at_max():
    data, errors = validate_input({'name': 'A' * 100, 'email': 'a@b.com', 'message': 'hi'})
    assert errors == []

def test_email_too_long():
    long_email = 'a' * 249 + '@b.com'  # 255 chars > 254 limit
    _, errors = validate_input({'name': 'Alice', 'email': long_email, 'message': 'hi'})
    fields = [e['field'] for e in errors]
    assert 'email' in fields

def test_message_too_long():
    _, errors = validate_input({'name': 'Alice', 'email': 'a@b.com', 'message': 'x' * 1001})
    fields = [e['field'] for e in errors]
    assert 'message' in fields

def test_message_at_max():
    data, errors = validate_input({'name': 'Alice', 'email': 'a@b.com', 'message': 'x' * 1000})
    assert errors == []


# ── Handler / HTTP response tests ─────────────────────────────────────────────

def test_valid_returns_200():
    body, status = handle_contact({'name': 'Alice', 'email': 'alice@example.com', 'message': 'hello'})
    assert status == 200
    assert body['status'] == 'ok'

def test_invalid_returns_400():
    body, status = handle_contact({'name': '', 'email': 'bad', 'message': ''})
    assert status == 400
    assert body['status'] == 'error'
    assert isinstance(body['errors'], list)

def test_error_messages_are_descriptive():
    body, status = handle_contact({'email': 'a@b.com', 'message': 'hi'})
    assert status == 400
    msgs = [e['message'] for e in body['errors']]
    assert any('name' in m for m in msgs)

def test_cleaned_data_stripped():
    body, status = handle_contact({'name': '  Alice  ', 'email': 'alice@example.com', 'message': '  hello  '})
    assert status == 200
    assert body['data']['name'] == 'Alice'
    assert body['data']['message'] == 'hello'
