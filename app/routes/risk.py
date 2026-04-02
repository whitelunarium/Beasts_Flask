# app/routes/risk.py
# Responsibility: Risk API endpoint — returns current fire/flood/heat assessment.

from flask import Blueprint, jsonify, request
from app.services import risk_service
from app.utils.errors import error_response

risk_bp = Blueprint('risk', __name__)


@risk_bp.route('/risk', methods=['GET'])
def get_risk():
    """
    Purpose: Return the current risk assessment for Poway (fire, flood, heat).
    Responses are cached for 30 minutes to avoid hammering Open-Meteo.
    Algorithm:
    1. Delegate to risk_service.get_risk_assessment()
    2. Return JSON payload
    3. Catch any unexpected errors and return 503
    """
    try:
        neighborhood_id = request.args.get('neighborhood_id', type=int)
        assessment = risk_service.get_risk_assessment(neighborhood_id=neighborhood_id)
        return jsonify(assessment), 200
    except Exception as e:
        return error_response('SERVER_ERROR', 503, {'detail': str(e)})
