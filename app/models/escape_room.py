# app/models/escape_room.py
# Responsibility: Leaderboard entry model for the Emergency Escape Room game.

from datetime import datetime
from app import db


class EscapeRoomEntry(db.Model):
    """A single leaderboard score entry from the Emergency Escape Room game."""

    __tablename__ = 'escape_room_leaderboard'

    id             = db.Column(db.Integer,    primary_key=True)
    display_name   = db.Column(db.String(80), nullable=False)
    score          = db.Column(db.Integer,    nullable=False)
    time_remaining = db.Column(db.Integer,    nullable=False)   # seconds remaining at completion
    rooms_completed = db.Column(db.Integer,   nullable=False)   # 0–3
    badge          = db.Column(db.String(50), nullable=True)
    created_at     = db.Column(db.DateTime,   nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':              self.id,
            'display_name':    self.display_name,
            'score':           self.score,
            'time_remaining':  self.time_remaining,
            'rooms_completed': self.rooms_completed,
            'badge':           self.badge,
            'created_at':      self.created_at.isoformat(),
        }

    def __repr__(self):
        return f'<EscapeRoomEntry {self.display_name}: {self.score}>'
