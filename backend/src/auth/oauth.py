from functools import wraps
from http import HTTPStatus

from flask_jwt_extended import get_jwt, verify_jwt_in_request
from flask_restx import abort


def admin_required(fn):
    @wraps(fn)
    def decorator(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims["role"] == "admin":
            return fn(*args, **kwargs)
        else:
            abort(HTTPStatus.FORBIDDEN, "You are not authorized to perform this action!")

    return decorator
