# app/services/escape_room_score_service.py
# Responsibility: RPG game score persistence for Poway Prepared.

from app import db
from app.models.escape_room_score import EscapeRoomScore


def save_rpg_score(player_name, score, badge, acts_completed, time_remaining):
    """Persist a Poway Prepared RPG score. Returns (dict, None) or (None, err_key)."""
    if not player_name or score is None:
        return None, 'VALIDATION_FAILED'

    entry = EscapeRoomScore(
        player_name=player_name.strip()[:80],
        score=max(0, int(score)),
        badge=badge or '',
        acts_completed=max(0, min(3, int(acts_completed))),
        time_remaining=max(0, int(time_remaining)),
    )
    db.session.add(entry)
    db.session.commit()
    return entry.to_dict(), None


def get_top_rpg_scores(limit=10):
    """Return top RPG leaderboard entries sorted by score descending."""
    entries = (EscapeRoomScore.query
               .order_by(EscapeRoomScore.score.desc())
               .limit(limit)
               .all())
    return [e.to_dict() for e in entries]
