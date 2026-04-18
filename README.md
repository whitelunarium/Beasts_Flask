# PNEC Backend — Flask REST API

Python Flask API server for the Poway Neighborhood Emergency Corps website. Provides all data endpoints consumed by the Jekyll frontend.

## Setup

**Prerequisites:** Python 3.9+

```bash
cd Beasts_Flask
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` (or set in your shell):

```bash
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///instance/pnec.db   # or mysql+pymysql://user:pass@host/db for prod

# Admin account seeded on first run
ADMIN_EMAIL=admin@powaynec.com
ADMIN_PASSWORD=change-me-in-production
ADMIN_DISPLAY_NAME=PNEC Admin

# Mail (leave blank to log emails to console in dev)
MAIL_SERVER=
MAIL_PORT=587
MAIL_USERNAME=
MAIL_PASSWORD=

# Gemini proxy used by the PNEC helper chatbot
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_RATE_LIMIT_PER_MINUTE=20

# Optional but recommended in production so rate limits work across workers
REDIS_URL=redis://localhost:6379/0
```

### Run

```bash
source venv/bin/activate
flask run --port 8425
```

API available at `http://localhost:8425`.

### Database

SQLite database is created automatically on first run at `instance/pnec.db`. On first run, the app also seeds:
- 8 FAQ categories with 30 preparedness Q&A items
- Neighborhood data (60+ Poway neighborhoods)
- Admin account from env variables

To reset and re-seed:
```bash
rm instance/pnec.db
flask run --port 8425
```

## Directory Structure

```
app/
  __init__.py              # Application factory — create_app(), blueprint registration, seeding
  config.py                # Dev/prod configuration from environment variables
  models/
    user.py                # User model (roles: resident/coordinator/staff/admin)
    faq.py                 # FaqCategory, FaqItem, UserQuestion
    event.py               # Event model
    media.py               # MediaPost model
    neighborhood.py        # Neighborhood model
    game.py                # GameScore model
  routes/
    auth.py                # /api/auth — login, register, logout, me
    faq.py                 # /api/faq — categories, items, search, helpful, questions
    events.py              # /api/events — list, calendar, create
    media.py               # /api/media — list, upload
    neighborhoods.py       # /api/neighborhoods — list, detail
    risk.py                # /api/risk — live hazard assessment
    game.py                # /api/game — questions, scores
    admin.py               # /api/admin — user management
  services/
    auth_service.py        # Auth business logic (register, login, session)
    faq_service.py         # FAQ CRUD + seed_faq()
    events_service.py      # Events CRUD + get_events_for_month()
    media_service.py       # Media upload handling
    neighborhood_service.py # Neighborhood data + seed_neighborhoods()
    risk_service.py        # Weather-based risk scoring (Open-Meteo API, no key needed)
    game_service.py        # Game questions and scoring
  utils/
    errors.py              # error_response() helper
    auth_decorators.py     # @requires_role() decorator
```

## API Reference

### Auth — `/api/auth`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/login` | — | Log in with email + password |
| POST | `/register` | — | Create resident account |
| POST | `/logout` | Session | End session |
| GET | `/me` | Session | Get current user profile |

### FAQ — `/api`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/faq/categories` | — | All FAQ categories |
| GET | `/faq/items?category_id=` | — | Items in a category |
| GET | `/faq/search?q=` | — | Search FAQ |
| POST | `/faq/helpful/{id}` | — | Mark helpful |
| POST | `/questions/submit` | Optional | Submit question to staff |
| GET | `/questions` | staff+ | All questions (with ?status filter) |
| PATCH | `/questions/{id}/claim` | staff+ | Claim a question |
| PATCH | `/questions/{id}/answer` | staff+ | Answer a question |

### Events — `/api`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/events` | — | All upcoming events |
| GET | `/events/calendar?month=&year=` | — | Events for calendar month |
| POST | `/events` | coordinator+ | Create event |

### Media — `/api`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/media?page=` | — | Paginated media posts |
| POST | `/media` | coordinator+ | Upload media (multipart) |

### Risk — `/api`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/risk` | — | Live Poway hazard assessment (fire/flood/heat) |

### AI Helper — `/api`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/gemini` | — | Server-side Gemini proxy for the PNEC helper chatbot |

### Neighborhoods — `/api`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/neighborhoods` | — | All neighborhoods |
| GET | `/neighborhoods/{id}` | — | Neighborhood detail + coordinator info |

## Architecture Patterns

**SRP (Single Responsibility Principle):** Routes delegate all logic to services. Services call models. No business logic in routes.

**Orchestrator / Worker separation:** Routes are thin orchestrators that validate input and call service workers. Service functions do exactly one thing and return `(result, error_key)` tuples on failure.

**Role hierarchy:** `resident` < `coordinator` < `staff` < `admin`. Protected routes use the `@requires_role('staff', 'admin')` decorator from `utils/auth_decorators.py`.
