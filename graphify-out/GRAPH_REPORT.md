# Graph Report - .  (2026-04-10)

## Corpus Check
- 56 files · ~120,893 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 378 nodes · 509 edges · 28 communities detected
- Extraction: 78% EXTRACTED · 22% INFERRED · 0% AMBIGUOUS · INFERRED: 110 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `User` - 57 edges
2. `main()` - 18 edges
3. `Beasts_Flask — PNEC Flask REST API` - 17 edges
4. `FaqCategory` - 15 edges
5. `FaqItem` - 15 edges
6. `UserQuestion` - 13 edges
7. `Neighborhood` - 11 edges
8. `Event` - 9 edges
9. `MediaPost` - 9 edges
10. `_assemble_risk_response()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `Initialize the posts table and sample data` --uses--> `User`  [INFERRED]
  scripts/init_posts.py → app/models/user.py
- `Check if required models exist` --uses--> `User`  [INFERRED]
  scripts/init_posts.py → app/models/user.py
- `Authenticate to production server and return session cookies.` --uses--> `User`  [INFERRED]
  scripts/db_restore-sqlite2prod.py → app/models/user.py
- `Read ALL data from the local SQLite database.` --uses--> `User`  [INFERRED]
  scripts/db_restore-sqlite2prod.py → app/models/user.py
- `Read data from local JSON file (legacy fallback).` --uses--> `User`  [INFERRED]
  scripts/db_restore-sqlite2prod.py → app/models/user.py

## Communities

### Community 0 - "C0"
Cohesion: 0.06
Nodes (45): authenticate(), backup_database(), create_database(), extract_all_data(), filter_default_data(), is_default_section(), is_default_topic(), is_default_user() (+37 more)

### Community 1 - "C1"
Cohesion: 0.1
Nodes (29): FaqCategory, FaqItem, A single FAQ question-answer pair belonging to a category., A question submitted by a resident, awaiting staff response., Groups of related FAQ questions (e.g. Wildfire, Earthquake)., answer_question(), claim_question(), get_all_categories() (+21 more)

### Community 2 - "C2"
Cohesion: 0.1
Nodes (21): Neighborhood, Return a JSON-serializable dict for API responses., A named Poway neighborhood with coordinator and map data., get_all_neighborhoods(), get_neighborhood_by_id(), lookup_neighborhood_by_name(), Purpose: Fetch a single neighborhood by primary key.     @param {int} neighborho, Purpose: Search neighborhoods by name or number (for address/name search bar). (+13 more)

### Community 3 - "C3"
Cohesion: 0.12
Nodes (20): backup_database(), main(), Backup the current database., authenticate(), filter_default_data(), import_all_data(), is_default_section(), is_default_topic() (+12 more)

### Community 4 - "C4"
Cohesion: 0.13
Nodes (16): get_media(), MediaPost, Return paginated media posts for the gallery. Public access., Upload a photo or video. Coordinator+ only.     Expects multipart/form-data with, A photo or video uploaded by a coordinator or staff member., allowed_file(), create_media_post(), determine_media_type() (+8 more)

### Community 5 - "C5"
Cohesion: 0.12
Nodes (16): EscapeRoomEntry, get_leaderboard(), get_rpg_leaderboard(), post_rpg_score(), post_score(), Return the top 10 escape room leaderboard scores., Submit a completed escape room score. No auth required — guests can play.     Ex, Submit a Poway Prepared RPG game score.     Expects JSON: { player_name, score, (+8 more)

### Community 6 - "C6"
Cohesion: 0.12
Nodes (18): Admin API (/api/admin) — user management, Auth API (/api/auth) — login, register, logout, profile, Events API (/api/events) — list, calendar view, create, FAQ API (/api/faq) — categories, items, search, helpful votes, user questions, Game API (/api/game) — preparedness quiz questions and scoring, Media API (/api/media) — paginated media posts, upload, Neighborhoods API (/api/neighborhoods) — 60+ Poway neighborhoods with coordinator info, Risk API (/api/risk) — live Poway hazard assessment (fire/flood/heat) via Open-Meteo (+10 more)

### Community 7 - "C7"
Cohesion: 0.12
Nodes (16): admin_accounts_page(), admin_login_page(), admin_logout_page(), admin_operations_data(), admin_operations_page(), deactivate_user(), list_users(), Render and process a minimal admin login form for the backend admin UI. (+8 more)

### Community 8 - "C8"
Cohesion: 0.12
Nodes (16): answer_question(), claim_question(), get_categories(), get_items(), get_questions(), mark_helpful(), Return all FAQ categories in display order., Return FAQ items filtered by category_id query param. (+8 more)

### Community 9 - "C9"
Cohesion: 0.15
Nodes (14): create_app(), load_user(), check_dependencies(), init_posts_table(), Initialize the posts table and sample data, Check if required models exist, Purpose: Bootstrap the Flask application with all extensions and blueprints., Purpose: Import and register every route blueprint onto the app.     @param {Fla (+6 more)

### Community 10 - "C10"
Cohesion: 0.15
Nodes (12): get_leaderboard(), LeaderboardEntry, post_score(), Return the top 10 leaderboard scores., Submit a completed game score. No auth required — guests can play.     Expects J, A single leaderboard score entry from the preparedness game., assign_badge(), get_top_scores() (+4 more)

### Community 11 - "C11"
Cohesion: 0.27
Nodes (13): _assemble_risk_response(), build_anomaly_alerts(), build_wildfire_forecast(), compute_fire_risk(), compute_flood_risk(), compute_heat_risk(), _fetch_air_quality(), _fetch_poway_weather() (+5 more)

### Community 12 - "C12"
Cohesion: 0.2
Nodes (8): Event, A PNEC community event (training, meeting, drill, etc.)., create_event(), get_events_for_month(), get_upcoming_events(), Purpose: Return all future events ordered by date ascending.     @param {int} li, Purpose: Return all events occurring within a specific calendar month.     @para, Purpose: Validate and create a new PNEC event.     @param {str}      title

### Community 13 - "C13"
Cohesion: 0.2
Nodes (10): build_new_db(), get_all_tables(), get_schema(), Get the schema for the specified tables from the SQLite database., Check if a table exists in the database., Update the schema of an existing table., Build a new SQLite database using the provided schema., Get the list of all tables in the SQLite database. (+2 more)

### Community 14 - "C14"
Cohesion: 0.22
Nodes (6): EscapeRoomScore, A single score entry from the Poway Prepared RPG game., get_top_rpg_scores(), Return top RPG leaderboard entries sorted by score descending., Persist a Poway Prepared RPG score. Returns (dict, None) or (None, err_key)., save_rpg_score()

### Community 15 - "C15"
Cohesion: 0.22
Nodes (8): Purpose: Return the numeric rank of a role for hierarchy comparison.     @param, Purpose: Require an authenticated session; reject anonymous requests.     @param, Purpose: Restrict a route to users whose role is in the allowed list.     @param, Purpose: Allow access to users with a role at or above the minimum in the hierar, requires_auth(), requires_min_role(), requires_role(), _role_rank()

### Community 16 - "C16"
Cohesion: 0.22
Nodes (8): login(), logout(), me(), Purpose: Create a new resident account and establish a session.     Algorithm:, Purpose: Authenticate and establish a session for an existing user.     Algorith, Purpose: End the current user's session.     Algorithm:     1. Call logout_user(, Purpose: Return the currently authenticated user's profile and role.     Algorit, register()

### Community 17 - "C17"
Cohesion: 0.32
Nodes (6): Config, DevelopmentConfig, get_config(), ProductionConfig, Base configuration shared by all environments., Return the correct Config class based on FLASK_ENV.

### Community 18 - "C18"
Cohesion: 0.29
Nodes (6): create_event(), get_calendar_events(), get_events(), Return upcoming events, sorted by date ascending., Return events for a specific month. Params: ?month=&year=, Create a new PNEC event. Coordinator+ only.

### Community 19 - "C19"
Cohesion: 0.29
Nodes (6): get_neighborhood(), get_neighborhoods(), lookup_neighborhood(), Return all neighborhoods for the map and registration dropdown., Return a single neighborhood by ID., Search neighborhoods by name or number. Used by map search bar.

### Community 20 - "C20"
Cohesion: 0.29
Nodes (6): authenticate_user(), create_user(), Purpose: Validate inputs and create a new resident user account.     @param {str, Purpose: Verify email + password and return the matching user.     @param {str}, Purpose: Change a user's role (admin-only action; caller must enforce permission, update_user_role()

### Community 21 - "C21"
Cohesion: 0.53
Nodes (5): _clamp_probability(), _normalize_inputs(), _predict_survival_probability(), predict_titanic(), Lightweight heuristic model tuned to Titanic-era signals.     Returns a probabil

### Community 22 - "C22"
Cohesion: 0.67
Nodes (2): error_response(), Purpose: Build a consistent JSON error response.     @param {str}  key         -

### Community 23 - "C23"
Cohesion: 0.67
Nodes (2): get_risk(), Purpose: Return the current risk assessment for Poway (fire, flood, heat).     R

### Community 24 - "C24"
Cohesion: 0.67
Nodes (2): create_legacy_user(), Purpose: Accept the older signup payload shape while creating a current PNEC acc

### Community 25 - "C25"
Cohesion: 1.0
Nodes (0): 

### Community 26 - "C26"
Cohesion: 1.0
Nodes (0): 

### Community 27 - "C27"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **71 isolated node(s):** `Base configuration shared by all environments.`, `Return the correct Config class based on FLASK_ENV.`, `Purpose: Build a consistent JSON error response.     @param {str}  key         -`, `Purpose: Return the numeric rank of a role for hierarchy comparison.     @param`, `Purpose: Require an authenticated session; reject anonymous requests.     @param` (+66 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `C25`** (1 nodes): `update_data.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `C26`** (1 nodes): `fetch_data.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `C27`** (1 nodes): `rds_init.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `User` connect `C0` to `C2`, `C3`, `C7`, `C9`, `C20`?**
  _High betweenness centrality (0.230) - this node is a cross-community bridge._
- **Why does `Neighborhood` connect `C2` to `C11`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `Purpose: Insert FAQ categories and items if the table is empty.     @returns {in` connect `C1` to `C12`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 47 inferred relationships involving `User` (e.g. with `Purpose: Bootstrap the Flask application with all extensions and blueprints.` and `Purpose: Import and register every route blueprint onto the app.     @param {Fla`) actually correct?**
  _`User` has 47 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `FaqCategory` (e.g. with `Purpose: Retrieve all FAQ categories ordered for display.     @returns {list} Li` and `Purpose: Retrieve all FAQ items belonging to a category.     @param {int} catego`) actually correct?**
  _`FaqCategory` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `FaqItem` (e.g. with `Purpose: Retrieve all FAQ categories ordered for display.     @returns {list} Li` and `Purpose: Retrieve all FAQ items belonging to a category.     @param {int} catego`) actually correct?**
  _`FaqItem` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Base configuration shared by all environments.`, `Return the correct Config class based on FLASK_ENV.`, `Purpose: Build a consistent JSON error response.     @param {str}  key         -` to the rest of the system?**
  _71 weakly-connected nodes found - possible documentation gaps or missing edges._