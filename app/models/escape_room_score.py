# app/models/escape_room_score.py
# Responsibility: Score model for the Poway Prepared RPG game.

from datetime import datetime
from app import db


class EscapeRoomScore(db.Model):
    """A single score entry from the Poway Prepared RPG game."""

    __tablename__ = 'escape_room_scores'

    id             = db.Column(db.Integer,    primary_key=True)
    player_name    = db.Column(db.String(80), nullable=False)
    score          = db.Column(db.Integer,    nullable=False)
    badge          = db.Column(db.String(50), nullable=True)
    acts_completed = db.Column(db.Integer,    nullable=False, default=0)
    time_remaining = db.Column(db.Integer,    nullable=False, default=0)
    created_at     = db.Column(db.DateTime,   nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':             self.id,
            'player_name':    self.player_name,
            'score':          self.score,
            'badge':          self.badge,
            'acts_completed': self.acts_completed,
            'time_remaining': self.time_remaining,
            'created_at':     self.created_at.isoformat(),
        }

    def __repr__(self):
        return f'<EscapeRoomScore {self.player_name}: {self.score}>'
