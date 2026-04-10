"""
app_legacy.py — BEFORE: bare try/except anti-patterns
"""
import json

def get_user(user_id):
    try:
        if not isinstance(user_id, int):
            raise Exception("bad id")
        if user_id <= 0:
            raise Exception("not found")
        return {"id": user_id, "name": "Alice"}
    except:
        return None

def create_user(data):
    try:
        name = data["name"]
        age = data["age"]
        if not name:
            raise Exception("name required")
        if age < 0:
            raise Exception("bad age")
        return {"id": 1, "name": name, "age": age}
    except Exception as e:
        print("error:", e)
        return {"error": str(e)}

def authenticate(token):
    try:
        if not token:
            raise Exception("no token")
        if token != "valid":
            raise Exception("invalid token")
        return {"user": "alice"}
    except Exception as e:
        return None

def divide(a, b):
    try:
        return a / b
    except:
        return 0

def parse_config(text):
    try:
        return json.loads(text)
    except:
        return {}
