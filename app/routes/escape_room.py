# app/routes/escape_room.py
# Responsibility: Emergency Escape Room API endpoints — leaderboard save and fetch.

import re
import time
from flask import Blueprint, request, jsonify
from app.services import escape_room_service
from app.services import escape_room_score_service
from app.utils.errors import error_response

escape_room_bp = Blueprint('escape_room', __name__)

# Sanity bounds + per-IP rate limit (matches game.py pattern). Was a known
# abuse vector — anyone could POST 99,999,999 with a defacing display_name.
SCORE_MAX             = 1_000_000   # generous; tune to game ceiling
SCORE_MIN             = 0
TIME_MAX              = 36_000      # 10 hr — defensive ceiling
NAME_MAX_LEN          = 32
RATE_LIMIT_WINDOW_SEC = 60
RATE_LIMIT_MAX_POSTS  = 5

_recent_posts = {}  # ip → [timestamps]
_NAME_RE = re.compile(r'[\x00-\x1f\x7f<>]')


def _client_ip():
    return (request.headers.get('X-Forwarded-For', request.remote_addr or '')
            .split(',')[0].strip() or '_')


def _is_rate_limited(ip):
    now = time.time()
    bucket = [t for t in _recent_posts.get(ip, []) if now - t < RATE_LIMIT_WINDOW_SEC]
    if len(bucket) >= RATE_LIMIT_MAX_POSTS:
        _recent_posts[ip] = bucket
        return True
    bucket.append(now)
    _recent_posts[ip] = bucket
    return False


def _clean_name(s):
    return _NAME_RE.sub('', (s or '').strip()).strip()[:NAME_MAX_LEN]


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
    if _is_rate_limited(_client_ip()):
        return error_response('RATE_LIMITED', 429,
                              {'detail': 'Too many submissions. Wait a minute and try again.'})

    data           = request.get_json(silent=True) or {}
    display_name   = _clean_name(data.get('display_name'))
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

    if score < SCORE_MIN or score > SCORE_MAX:
        return error_response('VALIDATION_FAILED', 400,
                              {'detail': f'score must be between {SCORE_MIN} and {SCORE_MAX}'})
    if time_remaining < 0 or time_remaining > TIME_MAX:
        return error_response('VALIDATION_FAILED', 400,
                              {'detail': f'time_remaining must be between 0 and {TIME_MAX}'})
    if rooms_completed < 0 or rooms_completed > 100:
        return error_response('VALIDATION_FAILED', 400,
                              {'detail': 'rooms_completed must be between 0 and 100'})

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
    if _is_rate_limited(_client_ip()):
        return error_response('RATE_LIMITED', 429,
                              {'detail': 'Too many submissions. Wait a minute and try again.'})

    data           = request.get_json(silent=True) or {}
    player_name    = _clean_name(data.get('player_name'))
    score          = data.get('score')
    badge          = (data.get('badge') or '')[:64]
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

    if score < SCORE_MIN or score > SCORE_MAX:
        return error_response('VALIDATION_FAILED', 400,
                              {'detail': f'score must be between {SCORE_MIN} and {SCORE_MAX}'})
    if time_remaining < 0 or time_remaining > TIME_MAX:
        return error_response('VALIDATION_FAILED', 400,
                              {'detail': f'time_remaining must be between 0 and {TIME_MAX}'})
    if acts_completed < 0 or acts_completed > 100:
        return error_response('VALIDATION_FAILED', 400,
                              {'detail': 'acts_completed must be between 0 and 100'})

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
