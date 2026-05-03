# app/config.py
# Responsibility: All Flask configuration in one place.
# Environment variables override defaults for production deployments.

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration shared by all environments."""

    # ─── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-prod'
    SESSION_COOKIE_NAME = 'pnec_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    JWT_TOKEN_NAME = 'pnec_jwt'

    # ─── Database ─────────────────────────────────────────────────────────────
    DB_ENDPOINT = os.environ.get('DB_ENDPOINT') or None
    DB_USERNAME = os.environ.get('DB_USERNAME') or None
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or None

    @staticmethod
    def build_db_uri():
        ep = os.environ.get('DB_ENDPOINT')
        un = os.environ.get('DB_USERNAME')
        pw = os.environ.get('DB_PASSWORD')
        if ep and un and pw:
            return f'mysql+pymysql://{un}:{pw}@{ep}:3306/pnec'
        # Absolute path so Flask works regardless of CWD
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base, 'instance', 'volumes', 'pnec.db')
        return f'sqlite:///{db_path}'

    SQLALCHEMY_DATABASE_URI = build_db_uri.__func__()
    SQLALCHEMY_BACKUP_URI = 'sqlite:///volumes/pnec_bak.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ─── File uploads ─────────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    UPLOAD_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4']
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'instance', 'uploads')

    # ─── Admin seed credentials ────────────────────────────────────────────────
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'admin@powaynec.com'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'changeme123'
    ADMIN_DISPLAY_NAME = os.environ.get('ADMIN_DISPLAY_NAME') or 'PNEC Admin'

    # ─── Email (Flask-Mail) ────────────────────────────────────────────────────
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or None
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or None
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or None
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@powaynec.com'

    # ─── External APIs ────────────────────────────────────────────────────────
    OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast'
    POWAY_LAT = 32.9628
    POWAY_LON = -117.0359
    RISK_CACHE_SECONDS = 1800  # 30 minutes
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or None
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL') or 'gemini-2.5-flash-lite'
    GEMINI_API_URL = os.environ.get('GEMINI_API_URL') or 'https://generativelanguage.googleapis.com/v1beta'
    GEMINI_RATE_LIMIT_PER_MINUTE = int(os.environ.get('GEMINI_RATE_LIMIT_PER_MINUTE') or 20)
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY') or None
    GROQ_MODEL = os.environ.get('GROQ_MODEL') or 'llama-3.3-70b-versatile'
    GROQ_API_URL = 'https://api.groq.com/openai/v1'
    REDIS_URL = os.environ.get('REDIS_URL') or None

    # ─── Web Push (VAPID) ─────────────────────────────────────────────────────
    VAPID_PUBLIC_KEY  = os.environ.get('VAPID_PUBLIC_KEY', '')
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
    VAPID_EMAIL       = os.environ.get('VAPID_EMAIL', 'info@powaynec.com')

    # ─── CMS v2 ───────────────────────────────────────────────────────────────
    # Where on disk the section type definitions live (each subdir is a type
    # containing <type>.html and <type>.schema.json).
    CMS_SECTIONS_PATH = os.environ.get('CMS_SECTIONS_PATH') or os.path.join(
        os.path.dirname(__file__), 'cms_sections'
    )


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'None'


config_map = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}


def get_config():
    """Return the correct Config class based on FLASK_ENV."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)
