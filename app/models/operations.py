# app/models/operations.py
# Responsibility: Volunteer availability and neighborhood resource inventory models.

from datetime import datetime

from app import db


class VolunteerAvailability(db.Model):
    """Tracks residents or coordinators who can help during incidents."""

    __tablename__ = 'volunteer_availability'

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    neighborhood_id = db.Column(db.Integer, db.ForeignKey('neighborhoods.id'), nullable=True)
    availability_status = db.Column(db.String(20), nullable=False, default='available')
    skills_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    neighborhood = db.relationship('Neighborhood')


class ResourceInventory(db.Model):
    """Tracks emergency supplies available for a neighborhood or citywide pool."""

    __tablename__ = 'resource_inventory'

    id = db.Column(db.Integer, primary_key=True)
    neighborhood_id = db.Column(db.Integer, db.ForeignKey('neighborhoods.id'), nullable=True)
    resource_type = db.Column(db.String(80), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    unit = db.Column(db.String(30), nullable=False, default='items')
    is_available = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    neighborhood = db.relationship('Neighborhood')
