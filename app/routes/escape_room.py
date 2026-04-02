# app/routes/escape_room.py
# Responsibility: Emergency Escape Room API endpoints — leaderboard save and fetch.

from flask import Blueprint, request, jsonify
from app.services import escape_room_service
from app.services import escape_room_score_service
from app.utils.errors import error_response

escape_room_bp = Blueprint('escape_room', __name__)


@escape_room_bp.route('/escape-room/leaderboard', methods=['GET'])
def get_leaderboard():
    """Return the top 10 escape room leaderboard scores."""
    entries = escape_room_service.get_top_scores(limit=10)
    return jsonify({'leaderboard': entries}), 200


@escape_room_bp.route('/escape-room/leaderboard', methods=['POST'])
def post_score():
    """
    Submit a completed escape room score. No auth required — guests can play.
    Expects JSON: { display_name, score, time_remaining, rooms_completed }
    """
    data           = request.get_json(silent=True) or {}
    display_name   = (data.get('display_name') or '').strip()
    score          = data.get('score')
    time_remaining = data.get('time_remaining')
    rooms_completed = data.get('rooms_completed')

    if not display_name or score is None or time_remaining is None or rooms_completed is None:
        return error_response('VALIDATION_FAILED', 400,
                              {'detail': 'display_name, score, time_remaining, and rooms_completed are required'})

    try:
        score           = int(score)
        time_remaining  = int(time_remaining)
        rooms_completed = int(rooms_completed)
    except (ValueError, TypeError):
        return error_response('VALIDATION_FAILED', 400, {'detail': 'score, time_remaining, and rooms_completed must be integers'})

    result, err = escape_room_service.save_score(display_name, score, time_remaining, rooms_completed)
    if err:
        return error_response(err, 400)
    return jsonify({'message': 'Score saved.', 'entry': result}), 201


@escape_room_bp.route('/escape-room/score', methods=['POST'])
def post_rpg_score():
    """
    Submit a Poway Prepared RPG game score.
    Expects JSON: { player_name, score, badge, acts_completed, time_remaining }
    """
    data           = request.get_json(silent=True) or {}
    player_name    = (data.get('player_name') or '').strip()
    score          = data.get('score')
    badge          = data.get('badge', '')
    acts_completed = data.get('acts_completed', 0)
    time_remaining = data.get('time_remaining', 0)

    if not player_name or score is None:
        return error_response('VALIDATION_FAILED', 400,
                              {'detail': 'player_name and score are required'})

    try:
        score          = int(score)
        acts_completed = int(acts_completed)
        time_remaining = int(time_remaining)
    except (ValueError, TypeError):
        return error_response('VALIDATION_FAILED', 400, {'detail': 'score, acts_completed, time_remaining must be integers'})

    result, err = escape_room_score_service.save_rpg_score(
        player_name, score, badge, acts_completed, time_remaining
    )
    if err:
        return error_response(err, 400)
    return jsonify({'message': 'Score saved.', 'entry': result}), 201


@escape_room_bp.route('/escape-room/scores', methods=['GET'])
def get_rpg_leaderboard():
    """Return the top 10 Poway Prepared RPG scores."""
    entries = escape_room_score_service.get_top_rpg_scores(limit=10)
    return jsonify({'leaderboard': entries}), 200
