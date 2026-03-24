# app/__init__.py
# Responsibility: Flask application factory — creates and wires together the app instance.
# All extensions, blueprints, and startup tasks are registered here and nowhere else.

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS

try:
    from flask_mail import Mail
    mail = Mail()
    MAIL_ENABLED = True
except ImportError:
    mail = None
    MAIL_ENABLED = False
    print("Warning: flask_mail not installed. Email notifications disabled.")

# ─── Extension instances (no app bound yet) ───────────────────────────────────
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    """
    Purpose: Bootstrap the Flask application with all extensions and blueprints.
    @returns {Flask} Fully configured Flask application instance
    Algorithm:
    1. Instantiate Flask app
    2. Load configuration
    3. Initialize extensions
    4. Register all route blueprints
    5. Create database tables and seed admin on first run
    """
    app = Flask(__name__, instance_relative_config=False)

    # ── Load configuration ────────────────────────────────────────────────────
    from app.config import get_config
    app.config.from_object(get_config())

    # ── Initialize extensions ─────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    if MAIL_ENABLED:
        mail.init_app(app)

    CORS(
        app,
        supports_credentials=True,
        origins=[
            'http://localhost:4000',
            'http://127.0.0.1:4000',
            'http://localhost:4600',
            'http://127.0.0.1:4600',
            'http://localhost:4500',
            'http://127.0.0.1:4500',
            'http://localhost:8080',
            'http://127.0.0.1:8080',
        ],
        methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    )

    @app.get('/')
    def root_health():
        """Return a simple health payload for the backend root URL."""
        return jsonify({'status': 'ok', 'message': 'Flask backend is running'}), 200

    # ── Register blueprints ───────────────────────────────────────────────────
    _register_blueprints(app)

    # ── Create tables + seed on first run ─────────────────────────────────────
    with app.app_context():
        db.create_all()
        _seed_admin_if_missing(app)
        _seed_initial_data()

    return app


def _register_blueprints(app):
    """
    Purpose: Import and register every route blueprint onto the app.
    @param {Flask} app - The Flask application instance
    Algorithm:
    1. Import each blueprint module
    2. Register with url_prefix
    """
    from app.routes.auth import auth_bp
    from app.routes.faq import faq_bp
    from app.routes.neighborhoods import neighborhoods_bp
    from app.routes.risk import risk_bp
    from app.routes.events import events_bp
    from app.routes.media import media_bp
    from app.routes.game import game_bp
    from app.routes.titanic import titanic_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp,          url_prefix='/api/auth')
    app.register_blueprint(faq_bp,           url_prefix='/api')
    app.register_blueprint(neighborhoods_bp, url_prefix='/api')
    app.register_blueprint(risk_bp,          url_prefix='/api')
    app.register_blueprint(events_bp,        url_prefix='/api')
    app.register_blueprint(media_bp,         url_prefix='/api')
    app.register_blueprint(game_bp,          url_prefix='/api')
    app.register_blueprint(titanic_bp,       url_prefix='/api')
    app.register_blueprint(admin_bp,         url_prefix='/api/admin')


def _seed_admin_if_missing(app):
    """
    Purpose: Create the admin user on first run if no admin exists.
    @param {Flask} app - App instance (used for config access)
    Algorithm:
    1. Query for any existing admin user
    2. If none found, create from env-configured credentials
    3. Commit to database
    """
    from app.models.user import User
    from werkzeug.security import generate_password_hash

    existing_admin = User.query.filter_by(role='admin').first()
    if existing_admin:
        return

    admin = User(
        email=app.config['ADMIN_EMAIL'],
        password_hash=generate_password_hash(app.config['ADMIN_PASSWORD'], method='pbkdf2:sha256'),
        display_name=app.config['ADMIN_DISPLAY_NAME'],
        role='admin',
        is_active=True,
    )
    db.session.add(admin)
    db.session.commit()


def _seed_initial_data():
    """
    Purpose: Seed neighborhoods and FAQ data on first run.
    @returns {void}
    Algorithm:
    1. Call seed_neighborhoods() — skips if data exists
    2. Call seed_faq() — skips if data exists
    """
    from app.services.neighborhood_service import seed_neighborhoods
    from app.services.faq_service import seed_faq
    seed_neighborhoods()
    seed_faq()


# ── Flask-Login user loader ────────────────────────────────────────────────────
@login_manager.user_loader
def load_user(user_id):
    """
    Purpose: Reload a user object from the database by user ID for Flask-Login.
    @param {str} user_id - The user's primary key as a string
    @returns {User|None} The User instance or None
    """
    from app.models.user import User
    return User.query.get(int(user_id))
