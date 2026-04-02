# app/services/escape_room_service.py
# Responsibility: Escape Room leaderboard business logic — save score, fetch top 10.

from app import db
from app.models.escape_room import EscapeRoomEntry

BADGE_THRESHOLDS = [
    (400, 'PNEC Escape Artist'),
    (250, 'Crisis Commander'),
    (100, 'Emergency Ready'),
    (0,   'Disoriented Resident'),
]


def assign_badge(score):
    """
    Purpose: Determine the badge label earned for a given escape room score.
    @param {int} score - Final game score
    @returns {str} Badge name string
    Algorithm:
    1. Iterate thresholds from highest to lowest
    2. Return the first badge whose threshold the score meets or exceeds
    """
    for threshold, badge in BADGE_THRESHOLDS:
        if score >= threshold:
            return badge
    return BADGE_THRESHOLDS[-1][1]


def save_score(display_name, score, time_remaining, rooms_completed):
    """
    Purpose: Persist an escape room leaderboard entry after a completed game.
    @param {str} display_name    - Player's chosen display name
    @param {int} score           - Final score (choice points + time bonus)
    @param {int} time_remaining  - Seconds left on clock at end
    @param {int} rooms_completed - Number of rooms completed (0–3)
    @returns {tuple} (EscapeRoomEntry dict, None) on success, (None, error_key) on failure
    Algorithm:
    1. Validate inputs
    2. Assign badge based on score
    3. Create and persist EscapeRoomEntry
    4. Return dict
    """
    if not display_name or score is None or time_remaining is None or rooms_completed is None:
        return None, 'VALIDATION_FAILED'

    badge = assign_badge(int(score))
    entry = EscapeRoomEntry(
        display_name=display_name.strip()[:80],
        score=int(score),
        time_remaining=max(0, int(time_remaining)),
        rooms_completed=max(0, min(3, int(rooms_completed))),
        badge=badge,
    )
    db.session.add(entry)
    db.session.commit()
    return entry.to_dict(), None


def get_top_scores(limit=10):
    """
    Purpose: Return the top escape room leaderboard entries by score.
    @param {int} limit - Number of entries to return (default 10)
    @returns {list} List of EscapeRoomEntry dicts, highest score first
    Algorithm:
    1. Query EscapeRoomEntry ordered by score descending
    2. Apply limit
    3. Return as list of dicts
    """
    entries = (EscapeRoomEntry.query
               .order_by(EscapeRoomEntry.score.desc())
               .limit(limit)
               .all())
    return [e.to_dict() for e in entries]
