# app/routes/push.py
import json
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user

from app import db
from app.models.push_subscription import PushSubscription
from app.utils.errors import error_response

push_bp = Blueprint('push', __name__)


@push_bp.route('/push/vapid-public-key', methods=['GET'])
def get_vapid_public_key():
    key = current_app.config.get('VAPID_PUBLIC_KEY', '')
    return jsonify({'publicKey': key}), 200


@push_bp.route('/push/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json(silent=True) or {}
    subscription = data.get('subscription', {})
    endpoint = subscription.get('endpoint', '')
    keys = subscription.get('keys', {})
    p256dh = keys.get('p256dh', '')
    auth = keys.get('auth', '')

    if not all([endpoint, p256dh, auth]):
        return error_response('VALIDATION_FAILED', 400, {'detail': 'Invalid push subscription.'})

    user_id = current_user.id if current_user.is_authenticated else None

    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if existing:
        existing.p256dh = p256dh
        existing.auth = auth
        if user_id:
            existing.user_id = user_id
    else:
        sub = PushSubscription(endpoint=endpoint, p256dh=p256dh, auth=auth, user_id=user_id)
        db.session.add(sub)

    db.session.commit()
    return jsonify({'ok': True}), 200


@push_bp.route('/push/send', methods=['POST'])
def send_push():
    if not current_user.is_authenticated:
        return error_response('UNAUTHORIZED', 401)

    data = request.get_json(silent=True) or {}
    title = data.get('title', 'PNEC Alert')
    body = data.get('body', '')
    url = data.get('url', '/')

    subscriptions = PushSubscription.query.filter_by(user_id=current_user.id).all()
    if not subscriptions:
        return jsonify({'ok': True, 'sent': 0, 'detail': 'No subscriptions found.'}), 200

    sent = _send_push_notifications(subscriptions, title, body, url)
    return jsonify({'ok': True, 'sent': sent}), 200


def _send_push_notifications(subscriptions, title, body, url='/'):
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        current_app.logger.warning('pywebpush not installed — push notifications disabled.')
        return 0

    vapid_private = current_app.config.get('VAPID_PRIVATE_KEY', '')
    vapid_email = current_app.config.get('VAPID_EMAIL', 'info@powaynec.com')

    if not vapid_private:
        return 0

    payload = json.dumps({'title': title, 'body': body, 'url': url, 'icon': '/assets/images/pnec-icon-192.png'})
    sent = 0
    to_remove = []

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
                },
                data=payload,
                vapid_private_key=vapid_private,
                vapid_claims={'sub': f'mailto:{vapid_email}'},
            )
            sub.last_used = datetime.utcnow()
            sent += 1
        except Exception as ex:
            if '410' in str(ex) or '404' in str(ex):
                to_remove.append(sub)

    for sub in to_remove:
        db.session.delete(sub)
    if to_remove or sent:
        db.session.commit()

    return sent
