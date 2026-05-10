# app/routes/auth.py
# Responsibility: Auth API endpoints — register, login, logout, me.
# Business logic delegated to services/auth_service.py.

import re
import time
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required

from app.services.auth_service import create_user, authenticate_user
from app.models.neighborhood import Neighborhood
from app.utils.errors import error_response
from app.utils.auth_helpers import current_auth_user

auth_bp = Blueprint('auth', __name__)

# ── Rate limiting + email validation (added after security audit) ──────
# Credential-stuffing and account-enumeration attacks were unmetered;
# /register accepted "x" or "x@@x" as an email. In-memory bucket per IP.
_rate_buckets = {}  # (ip, kind) → [timestamps]
_LOGIN_LIMIT  = 8     # per minute per IP
_REGISTER_LIMIT = 3   # per minute per IP
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$')


def _client_ip():
    return (request.headers.get('X-Forwarded-For', request.remote_addr or '')
            .split(',')[0].strip() or '_')


def _is_rate_limited(kind, limit, window=60):
    ip = _client_ip()
    key = (ip, kind)
    now = time.time()
    bucket = [t for t in _rate_buckets.get(key, []) if now - t < window]
    if len(bucket) >= limit:
        _rate_buckets[key] = bucket
        return True
    bucket.append(now)
    _rate_buckets[key] = bucket
    return False


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Purpose: Create a new resident account and establish a session.
    Algorithm:
    1. Rate-limit by IP (3/min — register is rare)
    2. Parse and validate required fields (email regex, password length)
    3. Delegate to create_user()
    4. Log the new user in
    5. Return user dict + 201
    """
    if _is_rate_limited('register', _REGISTER_LIMIT):
        return error_response('RATE_LIMITED', 429,
                              {'detail': 'Too many registration attempts. Try again in a minute.'})

    data = request.get_json(silent=True) or {}

    email        = (data.get('email') or '').strip().lower()
    password     = (data.get('password') or '').strip()
    display_name = (data.get('display_name') or '').strip()
    neighborhood_id = data.get('neighborhood_id') or None

    if not email or not password or not display_name:
        return error_response('VALIDATION_FAILED', 400,
                               {'detail': 'email, password, and display_name are required'})

    if not _EMAIL_RE.match(email) or len(email) > 254:
        return error_response('VALIDATION_FAILED', 400,
                              {'detail': 'Email address is not valid.'})

    if len(password) < 8:
        return error_response('VALIDATION_FAILED', 400,
                               {'detail': 'Password must be at least 8 characters'})

    if len(display_name) > 100:
        return error_response('VALIDATION_FAILED', 400,
                              {'detail': 'Display name must be 100 characters or fewer.'})

    user, err = create_user(email, password, display_name, neighborhood_id)
    if err:
        status = 409 if err == 'DUPLICATE_EMAIL' else 400
        # Audit log: duplicate registration attempts can indicate
        # account-discovery probing
        from app.utils.security import log_event
        from app.models.security_event import KIND_REGISTER_DUP, SEVERITY_INFO
        if err == 'DUPLICATE_EMAIL':
            log_event(KIND_REGISTER_DUP, severity=SEVERITY_INFO,
                      actor_email=email,
                      detail='Registration attempted with existing email')
        return error_response(err, status)

    from app import db
    from flask import session as flask_session
    from app.utils.security import log_event
    from app.models.security_event import KIND_REGISTER, SEVERITY_INFO
    token = user.generate_token()
    db.session.commit()
    flask_session.permanent = True
    login_user(user, remember=True)
    log_event(KIND_REGISTER, severity=SEVERITY_INFO,
              actor_id=user.id, actor_email=email,
              detail=f'New account created ({user.role})')
    return jsonify({'message': 'Account created.', 'user': user.to_dict(), 'token': token}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Purpose: Authenticate and establish a session for an existing user.
    Algorithm:
    1. Rate-limit by IP (8/min — credential-stuffing defense)
    2. Check per-email lockout (5 fails in 15min → 15min lock —
       defends against distributed attacks that beat the IP rate-limit)
    3. Parse email + password
    4. Delegate to authenticate_user()
    5. Log every login attempt to security_events (success/fail/locked)
    6. Call login_user() with remember flag
    7. Return user dict
    """
    from app.utils.security import (
        is_account_locked, record_login_failure, record_login_success,
        log_event, is_suspicious_user_agent,
    )
    from app.models.security_event import (
        KIND_LOGIN_SUCCESS, KIND_LOGIN_FAILURE, KIND_LOGIN_LOCKED,
        KIND_LOGIN_RATE_LIMIT, SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_ALERT,
    )

    if _is_rate_limited('login', _LOGIN_LIMIT):
        log_event(KIND_LOGIN_RATE_LIMIT, severity=SEVERITY_WARNING,
                  detail='IP hit per-minute login rate limit')
        return error_response('RATE_LIMITED', 429,
                              {'detail': 'Too many login attempts. Wait a minute and try again.'})

    data = request.get_json(silent=True) or {}

    email    = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '').strip()
    remember = bool(data.get('remember', False))

    if not email or not password:
        return error_response('VALIDATION_FAILED', 400,
                               {'detail': 'email and password are required'})

    # Per-email lockout check — works across IPs
    locked, secs = is_account_locked(email)
    if locked:
        log_event(KIND_LOGIN_LOCKED, severity=SEVERITY_WARNING,
                  actor_email=email,
                  detail=f'Login attempted while locked ({secs}s remaining)')
        mins = max(1, secs // 60)
        return error_response('ACCOUNT_LOCKED', 423,
                              {'detail': f'Account locked due to too many failed attempts. Try again in ~{mins} minute(s).'})

    user, err = authenticate_user(email, password)
    if err:
        # Record the failure → may flip to locked
        now_locked, remaining = record_login_failure(email)
        # Suspicious UA on a failed login is worth escalating
        suspicious = is_suspicious_user_agent(request.headers.get('User-Agent'))
        log_event(
            KIND_LOGIN_LOCKED if now_locked else KIND_LOGIN_FAILURE,
            severity=(SEVERITY_ALERT if now_locked or suspicious else SEVERITY_WARNING),
            actor_email=email,
            detail=(f'Login failed: {err}' +
                    (f' — account NOW LOCKED after {_LOGIN_LIMIT} failures.' if now_locked
                     else f' — {remaining} attempt(s) remaining before lockout.')),
            extra={'reason': err, 'suspicious_ua': suspicious},
        )
        if now_locked:
            return error_response('ACCOUNT_LOCKED', 423,
                                  {'detail': 'Account locked due to too many failed attempts. Try again in 15 minutes.'})
        return error_response(err, 401)

    # Success path
    record_login_success(email)
    log_event(KIND_LOGIN_SUCCESS, severity=SEVERITY_INFO,
              actor_id=user.id, actor_email=email,
              detail=f'Sign-in success ({user.role})')

    from app import db
    from flask import session as flask_session
    token = user.generate_token()
    db.session.commit()
    flask_session.permanent = True
    login_user(user, remember=True)
    return jsonify({'message': 'Signed in.', 'user': user.to_dict(), 'token': token}), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Purpose: End the current user's session.
    Algorithm:
    1. Call logout_user()
    2. Return 200 confirmation
    """
    logout_user()
    return jsonify({'message': 'Signed out.'}), 200


@auth_bp.route('/me', methods=['GET'])
def me():
    user = current_auth_user()
    if not user:
        return jsonify({'error': 'UNAUTHORIZED', 'message': 'Not signed in.'}), 401
    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/profile', methods=['PATCH'])
def update_profile():
    """
    Purpose: Update editable profile fields for the current user.
    Accepted fields: display_name, bio, avatar_url, phone, neighborhood_id
    Supports both session cookie and Bearer token auth.
    """
    from app import db
    user = current_auth_user()
    if not user:
        return jsonify({'error': 'UNAUTHORIZED', 'message': 'Login required.'}), 401

    data = request.get_json(silent=True) or {}

    if 'display_name' in data:
        name = (data.get('display_name') or '').strip()
        if not name:
            return error_response('VALIDATION_FAILED', 400, {'detail': 'display_name cannot be empty'})
        user.display_name = name[:100]

    if 'neighborhood_id' in data:
        neighborhood_id = data.get('neighborhood_id')
        if neighborhood_id in (None, '', 'null'):
            user.neighborhood_id = None
        else:
            try:
                neighborhood_id = int(neighborhood_id)
            except (TypeError, ValueError):
                return error_response('VALIDATION_FAILED', 400, {'detail': 'neighborhood_id must be a number.'})
            if not Neighborhood.query.get(neighborhood_id):
                return error_response('VALIDATION_FAILED', 400, {'detail': 'Selected neighborhood does not exist.'})
            user.neighborhood_id = neighborhood_id

    for optional_field in ('bio', 'phone', 'avatar_url'):
        if optional_field in data and hasattr(user, optional_field):
            setattr(user, optional_field, data.get(optional_field))

    db.session.commit()
    return jsonify({'message': 'Profile updated.', 'user': user.to_dict()}), 200


@auth_bp.route('/me/inactive', methods=['PATCH'])
def mark_me_inactive():
    """
    Purpose: Let a signed-in resident mark their own account inactive.
    Admin accounts cannot deactivate themselves here.
    """
    from app import db
    user = current_auth_user()
    if not user:
        return jsonify({'error': 'UNAUTHORIZED', 'message': 'Login required.'}), 401
    if user.role == 'admin':
        return error_response('FORBIDDEN', 403, {'detail': 'Admin accounts must be managed from the admin dashboard.'})

    user.is_active = False
    logout_user()
    db.session.commit()
    return jsonify({'message': 'Account marked inactive.'}), 200
