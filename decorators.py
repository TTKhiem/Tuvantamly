from flask import session, abort
from functools import wraps

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            return abort(403)   # Forbidden
        return f(*args, **kwargs)
    return wrapper

def student_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "student":
            return abort(403)
        return f(*args, **kwargs)
    return wrapper

def therapist_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "therapist":
            return abort(403)
        return f(*args, **kwargs)
    return wrapper  