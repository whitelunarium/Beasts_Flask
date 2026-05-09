# app/routes/faq.py
# Responsibility: FAQ API endpoints — categories, items, search, helpful votes, questions.
# All business logic delegated to services/faq_service.py.

import re
import time
from flask import Blueprint, request, jsonify
from flask_login import current_user

from app.services import faq_service
from app.utils.errors import error_response
from app.utils.auth_decorators import requires_role

faq_bp = Blueprint('faq', __name__)

# Spam defenses for the open /questions/submit endpoint
_qbuckets = {}
_QUESTION_LIMIT = 3       # per minute per IP
_QUESTION_MIN_LEN = 10
_QUESTION_MAX_URLS = 3
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$')


def _q_rate_limited():
    ip = (request.headers.get('X-Forwarded-For', request.remote_addr or '')
          .split(',')[0].strip() or '_')
    now = time.time()
    bucket = [t for t in _qbuckets.get(ip, []) if now - t < 60]
    if len(bucket) >= _QUESTION_LIMIT:
        _qbuckets[ip] = bucket
        return True
    bucket.append(now)
    _qbuckets[ip] = bucket
    return False


@faq_bp.route('/faq/categories', methods=['GET'])
def get_categories():
    """Return all FAQ categories in display order."""
    categories = faq_service.get_all_categories()
    return jsonify({'categories': categories}), 200


@faq_bp.route('/faq/items', methods=['GET'])
def get_items():
    """Return FAQ items filtered by category_id query param."""
    category_id = request.args.get('category_id', type=int)
    if not category_id:
        return error_response('VALIDATION_FAILED', 400,
                               {'detail': 'category_id query param is required'})
    items = faq_service.get_items_for_category(category_id)
    return jsonify({'items': items}), 200


@faq_bp.route('/faq/search', methods=['GET'])
def search_faq():
    """Full-text search across FAQ questions and answers."""
    q = request.args.get('q', '').strip()
    results = faq_service.search_faq(q)
    return jsonify({'results': results}), 200


@faq_bp.route('/faq/helpful/<int:item_id>', methods=['POST'])
def mark_helpful(item_id):
    """Increment the helpful count for a FAQ item."""
    success = faq_service.increment_helpful(item_id)
    if not success:
        return error_response('NOT_FOUND', 404)
    return jsonify({'message': 'Thanks for your feedback!'}), 200


@faq_bp.route('/questions/submit', methods=['POST'])
def submit_question():
    """Submit a question to PNEC staff. Auth optional — guests may submit.

    Spam defenses (added after security audit):
      • 3 submissions per minute per IP
      • Email regex check
      • question_text minimum length 10
      • Reject submissions with more than 3 URLs (link-bait spam pattern)
    """
    if _q_rate_limited():
        return error_response('RATE_LIMITED', 429,
                              {'detail': 'Too many submissions. Wait a minute before sending another.'})

    data = request.get_json(silent=True) or {}

    display_name  = (data.get('display_name') or '').strip()[:100]
    email         = (data.get('email') or '').strip().lower()[:254]
    question_text = (data.get('question_text') or '').strip()

    # Pre-fill from session if logged in
    if current_user.is_authenticated:
        display_name = display_name or current_user.display_name
        email        = email        or (current_user.email or '').lower()

    if email and not _EMAIL_RE.match(email):
        return error_response('VALIDATION_FAILED', 400, {'detail': 'Email address is not valid.'})

    if len(question_text) < _QUESTION_MIN_LEN:
        return error_response('VALIDATION_FAILED', 400,
                              {'detail': f'Question text must be at least {_QUESTION_MIN_LEN} characters.'})

    if len(question_text) > 4000:
        return error_response('VALIDATION_FAILED', 400,
                              {'detail': 'Question text is too long (max 4000 characters).'})

    url_count = len(re.findall(r'https?://\S+', question_text))
    if url_count > _QUESTION_MAX_URLS:
        return error_response('VALIDATION_FAILED', 400,
                              {'detail': 'Question contains too many links.'})

    user_id = current_user.id if current_user.is_authenticated else None
    result, err = faq_service.submit_question(display_name, email, question_text, user_id)
    if err:
        return error_response(err, 400)
    return jsonify({'message': 'Your question has been submitted. A staff member will respond soon.',
                    'question': result}), 201


@faq_bp.route('/questions', methods=['GET'])
@requires_role('staff', 'admin')
def get_questions():
    """Return all submitted questions (staff+ only). Filter by ?status=open|claimed|answered."""
    status_filter = request.args.get('status') or None
    questions = faq_service.get_all_questions(status_filter)
    return jsonify({'questions': questions}), 200


@faq_bp.route('/questions/<int:question_id>/claim', methods=['PATCH'])
@requires_role('staff', 'admin')
def claim_question(question_id):
    """Mark a question as claimed by the requesting staff member."""
    result, err = faq_service.claim_question(question_id, current_user.id)
    if err:
        status = 404 if err == 'NOT_FOUND' else 400
        return error_response(err, status)
    return jsonify({'message': 'Question claimed.', 'question': result}), 200


@faq_bp.route('/questions/<int:question_id>/answer', methods=['PATCH'])
@requires_role('staff', 'admin')
def answer_question(question_id):
    """Submit an answer to a question."""
    data = request.get_json(silent=True) or {}
    answer_text = (data.get('answer_text') or '').strip()
    if not answer_text:
        return error_response('VALIDATION_FAILED', 400, {'detail': 'answer_text is required'})
    result, err = faq_service.answer_question(question_id, answer_text, current_user.id)
    if err:
        status = 404 if err == 'NOT_FOUND' else 400
        return error_response(err, status)
    return jsonify({'message': 'Answer submitted.', 'question': result}), 200
