# app/models/page_section.py
# Responsibility: A single content section that can be added/ordered/removed on any page.

import json
from datetime import datetime
from app import db


class PageSection(db.Model):
    __tablename__ = 'page_sections'

    id            = db.Column(db.Integer,     primary_key=True)
    page_slug     = db.Column(db.String(80),  nullable=False, index=True)
    block_type    = db.Column(db.String(40),  nullable=False, default='text_block')
    title         = db.Column(db.String(200), nullable=True)
    content       = db.Column(db.Text,        nullable=True)   # JSON string
    display_order = db.Column(db.Integer,     nullable=False, default=0)
    visible       = db.Column(db.Boolean,     nullable=False, default=True)
    created_at    = db.Column(db.DateTime,    nullable=False, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime,    nullable=False, default=datetime.utcnow,
                              onupdate=datetime.utcnow)
    updated_by    = db.Column(db.Integer,     db.ForeignKey('users.id'), nullable=True)

    def get_content(self):
        """Return content parsed as dict, or empty dict on failure."""
        try:
            return json.loads(self.content) if self.content else {}
        except (ValueError, TypeError):
            return {}

    def set_content(self, data):
        self.content = json.dumps(data) if data else None

    def to_dict(self):
        return {
            'id':            self.id,
            'page_slug':     self.page_slug,
            'block_type':    self.block_type,
            'title':         self.title,
            'content':       self.get_content(),
            'display_order': self.display_order,
            'visible':       self.visible,
            'created_at':    self.created_at.isoformat(),
            'updated_at':    self.updated_at.isoformat(),
        }
