# app/routes/titanic.py
# Responsibility: Titanic survival prediction endpoint used by the portfolio frontend.

from math import exp

from flask import Blueprint, jsonify, request

from app.utils.errors import error_response

titanic_bp = Blueprint('titanic', __name__)


def _clamp_probability(value):
    return max(0.001, min(0.999, value))


def _normalize_inputs(data):
    try:
        pclass = int(data.get('pclass'))
        age = float(data.get('age'))
        sibsp = int(data.get('sibsp'))
        parch = int(data.get('parch'))
        fare = float(data.get('fare'))
    except (TypeError, ValueError):
        raise ValueError('pclass, age, sibsp, parch, and fare must be numeric')

    sex = str(data.get('sex', '')).strip().lower()
    embarked = str(data.get('embarked', '')).strip().upper()
    alone = bool(data.get('alone'))

    if pclass not in {1, 2, 3}:
        raise ValueError('pclass must be 1, 2, or 3')
    if sex not in {'male', 'female'}:
        raise ValueError("sex must be 'male' or 'female'")
    if embarked not in {'C', 'Q', 'S'}:
        raise ValueError("embarked must be 'C', 'Q', or 'S'")
    if age < 0 or fare < 0 or sibsp < 0 or parch < 0:
        raise ValueError('age, fare, sibsp, and parch must be non-negative')

    return {
        'pclass': pclass,
        'sex': sex,
        'age': age,
        'sibsp': sibsp,
        'parch': parch,
        'fare': fare,
        'embarked': embarked,
        'alone': alone,
    }


def _predict_survival_probability(passenger):
    """
    Lightweight heuristic model tuned to Titanic-era signals.
    Returns a probability in [0, 1] with the same shape the frontend expects.
    """
    score = -0.35

    if passenger['sex'] == 'female':
        score += 2.45
    else:
        score -= 0.95

    score += {1: 1.10, 2: 0.30, 3: -0.85}[passenger['pclass']]

    if passenger['age'] < 12:
        score += 0.80
    elif passenger['age'] > 60:
        score -= 0.35
    else:
        score -= 0.012 * max(passenger['age'] - 28, 0)

    score -= 0.18 * passenger['sibsp']
    score -= 0.10 * passenger['parch']

    if passenger['alone']:
        score -= 0.12
    elif passenger['sibsp'] + passenger['parch'] in {1, 2, 3}:
        score += 0.18

    score += min(passenger['fare'], 100) * 0.012
    score += {'C': 0.22, 'Q': -0.05, 'S': -0.08}[passenger['embarked']]

    survive = _clamp_probability(1 / (1 + exp(-score)))
    return survive


@titanic_bp.route('/titanic/predict', methods=['POST', 'OPTIONS'])
def predict_titanic():
    if request.method == 'OPTIONS':
        return '', 204

    data = request.get_json(silent=True) or {}

    try:
        passenger = _normalize_inputs(data)
    except ValueError as exc:
        return error_response('VALIDATION_FAILED', 400, {'detail': str(exc)})

    survive = _predict_survival_probability(passenger)
    die = round(1 - survive, 4)
    survive = round(survive, 4)

    return jsonify({
        'name': str(data.get('name', '')).strip() or 'Anonymous',
        'survive': survive,
        'die': die,
    }), 200
