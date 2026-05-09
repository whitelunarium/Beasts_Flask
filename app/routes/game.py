# app/routes/game.py
# Responsibility: Game API endpoints — save score and fetch leaderboard top 10.

import re
import time
from flask import Blueprint, request, jsonify
from app.services import game_service
from app.utils.errors import error_response

game_bp = Blueprint('game', __name__)

# Leaderboard sanity bounds + per-IP rate limit. Was a known abuse vector:
# anyone could POST a 99,999,999 score with a defacing display_name.
SCORE_MAX = 100_000          # generous cap; tune to whatever the game can plausibly score
SCORE_MIN = 0
NAME_MAX_LEN = 32
NAME_MIN_LEN = 1
RATE_LIMIT_WINDOW_SEC = 60
RATE_LIMIT_MAX_POSTS  = 5

_recent_posts = {}  # ip → [timestamps]
_NAME_RE = re.compile(r'[\x00-\x1f\x7f<>]')   # strip control chars + angle brackets


def _is_rate_limited(ip):
    now = time.time()
    bucket = [t for t in _recent_posts.get(ip, []) if now - t < RATE_LIMIT_WINDOW_SEC]
    if len(bucket) >= RATE_LIMIT_MAX_POSTS:
        _recent_posts[ip] = bucket
        return True
    bucket.append(now)
    _recent_posts[ip] = bucket
    return False


@game_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """Return the top 10 leaderboard scores."""
    entries = game_service.get_top_scores(limit=10)
    return jsonify({'leaderboard': entries}), 200


@game_bp.route('/leaderboard', methods=['POST'])
def post_score():
    """
    Submit a completed game score. No auth required — guests can play.
    Expects JSON: { display_name, score }

    Validation (added after security audit):
      • score clamped to [SCORE_MIN, SCORE_MAX]
      • display_name 1–32 chars, control chars + < > stripped
      • per-IP rate limit: 5 posts per 60 seconds
    """
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip() or '_'
    if _is_rate_limited(ip):
        return error_response('RATE_LIMITED', 429,
                              {'detail': 'Too many submissions. Wait a minute and try again.'})

    data = request.get_json(silent=True) or {}
    display_name = (data.get('display_name') or '').strip()
    score        = data.get('score')

    if not display_name or score is None:
        return error_response('VALIDATION_FAILED', 400,
                               {'detail': 'display_name and score are required'})

    # Sanitize display_name
    display_name = _NAME_RE.sub('', display_name).strip()[:NAME_MAX_LEN]
    if len(display_name) < NAME_MIN_LEN:
        return error_response('VALIDATION_FAILED', 400, {'detail': 'display_name must be at least 1 character'})

    try:
        score = int(score)
    except (ValueError, TypeError):
        return error_response('VALIDATION_FAILED', 400, {'detail': 'score must be an integer'})
    if score < SCORE_MIN or score > SCORE_MAX:
        return error_response('VALIDATION_FAILED', 400,
                              {'detail': f'score must be between {SCORE_MIN} and {SCORE_MAX}'})

    result, err = game_service.save_score(display_name, score)
    if err:
        return error_response(err, 400)
    return jsonify({'message': 'Score saved.', 'entry': result}), 201
