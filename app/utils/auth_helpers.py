from flask import request
from flask_login import current_user


def get_token_user():
    """Return user from Bearer token header, or None."""
    from app.models.user import User
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        token = auth[7:].strip()
        if token:
            return User.query.filter_by(auth_token=token, is_active=True).first()
    return None


def current_auth_user():
    """Return authenticated user from Bearer token or Flask session."""
    token_user = get_token_user()
    if token_user:
        return token_user
    if current_user.is_authenticated:
        return current_user
    return None
