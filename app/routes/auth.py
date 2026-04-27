# app/routes/auth.py
# Responsibility: Auth API endpoints — register, login, logout, me.
# Business logic delegated to services/auth_service.py.

from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required

from app.services.auth_service import create_user, authenticate_user
from app.models.neighborhood import Neighborhood
from app.utils.errors import error_response

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Purpose: Create a new resident account and establish a session.
    Algorithm:
    1. Parse and validate required fields
    2. Delegate to create_user()
    3. Log the new user in
    4. Return user dict + 201
    """
    data = request.get_json(silent=True) or {}

    email        = (data.get('email') or '').strip()
    password     = (data.get('password') or '').strip()
    display_name = (data.get('display_name') or '').strip()
    neighborhood_id = data.get('neighborhood_id') or None

    if not email or not password or not display_name:
        return error_response('VALIDATION_FAILED', 400,
                               {'detail': 'email, password, and display_name are required'})

    if len(password) < 8:
        return error_response('VALIDATION_FAILED', 400,
                               {'detail': 'Password must be at least 8 characters'})

    user, err = create_user(email, password, display_name, neighborhood_id)
    if err:
        status = 409 if err == 'DUPLICATE_EMAIL' else 400
        return error_response(err, status)

    login_user(user, remember=False)
    return jsonify({'message': 'Account created.', 'user': user.to_dict()}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Purpose: Authenticate and establish a session for an existing user.
    Algorithm:
    1. Parse email + password
    2. Delegate to authenticate_user()
    3. Call login_user() with remember flag
    4. Return user dict
    """
    data = request.get_json(silent=True) or {}

    email    = (data.get('email') or '').strip()
    password = (data.get('password') or '').strip()
    remember = bool(data.get('remember', False))

    if not email or not password:
        return error_response('VALIDATION_FAILED', 400,
                               {'detail': 'email and password are required'})

    user, err = authenticate_user(email, password)
    if err:
        return error_response(err, 401)

    login_user(user, remember=remember)
    return jsonify({'message': 'Signed in.', 'user': user.to_dict()}), 200


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
    """
    Purpose: Return the currently authenticated user's profile and role.
    Algorithm:
    1. Check if user is authenticated
    2. If not: return 401
    3. If yes: return user dict
    """
    if not current_user.is_authenticated:
        return jsonify({'error': 'UNAUTHORIZED', 'message': 'Not signed in.'}), 401
    return jsonify({'user': current_user.to_dict()}), 200


@auth_bp.route('/profile', methods=['PATCH'])
@login_required
def update_profile():
    """
    Purpose: Let signed-in users update basic profile fields.
    Currently supports display name and neighborhood selection. Optional profile
    fields are applied only if the database model includes those columns.
    """
    data = request.get_json(silent=True) or {}

    display_name = (data.get('display_name') or '').strip()
    if display_name:
        current_user.display_name = display_name[:100]

    if 'neighborhood_id' in data:
        neighborhood_id = data.get('neighborhood_id')
        if neighborhood_id in (None, '', 'null'):
            current_user.neighborhood_id = None
        else:
            try:
                neighborhood_id = int(neighborhood_id)
            except (TypeError, ValueError):
                return error_response('VALIDATION_FAILED', 400, {'detail': 'neighborhood_id must be a number.'})

            if not Neighborhood.query.get(neighborhood_id):
                return error_response('VALIDATION_FAILED', 400, {'detail': 'Selected neighborhood does not exist.'})
            current_user.neighborhood_id = neighborhood_id

    for optional_field in ('bio', 'phone', 'avatar_url'):
        if optional_field in data and hasattr(current_user, optional_field):
            setattr(current_user, optional_field, data.get(optional_field))

    from app import db
    db.session.commit()

    return jsonify({'message': 'Profile updated.', 'user': current_user.to_dict()}), 200


@auth_bp.route('/me/inactive', methods=['PATCH'])
@login_required
def mark_me_inactive():
    """
    Purpose: Let a signed-in resident mark their own account inactive.
    This is useful when someone moves out of their neighborhood or no longer
    wants to participate. Admin accounts cannot deactivate themselves here.
    """
    if current_user.role == 'admin':
        return error_response('FORBIDDEN', 403, {'detail': 'Admin accounts must be managed from the admin dashboard.'})

    current_user.is_active = False
    logout_user()

    from app import db
    db.session.commit()

    return jsonify({'message': 'Account marked inactive.'}), 200
