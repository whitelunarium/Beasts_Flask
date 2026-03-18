# app/routes/events.py
# Responsibility: Events API endpoints — list, calendar view, create.

from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_login import current_user

from app.services import events_service
from app.utils.errors import error_response
from app.utils.auth_decorators import requires_role

events_bp = Blueprint('events', __name__)


@events_bp.route('/events', methods=['GET'])
def get_events():
    """Return upcoming events, sorted by date ascending."""
    events = events_service.get_upcoming_events(limit=50)
    return jsonify({'events': events}), 200


@events_bp.route('/events/calendar', methods=['GET'])
def get_calendar_events():
    """Return events for a specific month. Params: ?month=&year="""
    try:
        year  = int(request.args.get('year',  datetime.utcnow().year))
        month = int(request.args.get('month', datetime.utcnow().month))
    except (ValueError, TypeError):
        return error_response('VALIDATION_FAILED', 400, {'detail': 'year and month must be integers'})

    events = events_service.get_events_for_month(year, month)
    return jsonify({'events': events, 'year': year, 'month': month}), 200


@events_bp.route('/events', methods=['POST'])
@requires_role('coordinator', 'staff', 'admin')
def create_event():
    """Create a new PNEC event. Coordinator+ only."""
    data = request.get_json(silent=True) or {}

    result, err = events_service.create_event(
        title=data.get('title', ''),
        description=data.get('description', ''),
        date_str=data.get('date', ''),
        location=data.get('location', ''),
        image_url=data.get('image_url'),
        created_by=current_user.id,
    )
    if err:
        return error_response(err, 400)
    return jsonify({'message': 'Event created.', 'event': result}), 201
