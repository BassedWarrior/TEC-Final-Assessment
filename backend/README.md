# Backend API

FastAPI application that handles authentication, player data, schedule proxying, and simulation orchestration for the MLB Baseball Game Simulator.

## Technology Stack

| Library | Purpose |
|---|---|
| **FastAPI** | Async web framework |
| **asyncpg** | Async PostgreSQL driver |
| **SQLAlchemy 2.0** (async) | ORM + query builder |
| **python-jose** | JWT creation and verification |
| **passlib + argon2-cffi** | Argon2 password hashing |
| **slowapi** | Rate limiting (wraps `limits`) |
| **httpx** | Async HTTP client — proxies to Model API and MLB Stats API |
| **pydantic v2** | Request/response schema validation |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                   # ASGI app, CORS, rate limiter, router registration
│   ├── config.py                 # Settings loaded from .env via pydantic-settings
│   ├── limiter.py                # slowapi limiter singleton
│   ├── db/
│   │   ├── base.py               # Async engine, AsyncSessionLocal, declarative Base
│   │   ├── session.py            # get_db() dependency
│   │   └── scripts/
│   │       ├── init_db.py        # One-time table creation
│   │       ├── drop_db.py        # Drop and recreate all tables
│   │       └── seed_players.py   # Load 2024 MLB player stats from CSV
│   ├── models/
│   │   ├── user.py               # User (UUID PK, email, argon2 hash, token_version)
│   │   ├── player.py             # Player (MLB stats seeded from 2024 data)
│   │   └── match.py              # Match, MatchInning, MatchLineup
│   ├── routes/
│   │   ├── auth.py               # /auth/*
│   │   ├── simulations.py        # /simulations/*
│   │   ├── players.py            # /players/*
│   │   └── schedule.py           # /schedule
│   ├── services/
│   │   ├── lineups.py            # Resolve player IDs → stat arrays for the Model API
│   │   └── results.py            # Aggregate raw simulation output → averages
│   └── utils/
│       ├── security.py           # Argon2 hashing, JWT creation
│       └── dependencies.py       # get_current_user (Bearer header + httpOnly cookie)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
# PostgreSQL connection string
DATABASE_URL=postgresql+asyncpg://itcdreamteam:<password>@localhost:5432/tec_final_assessment

# JWT
SECRET_KEY=<64-char random string>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Where the Model API is running
MODEL_API_URL=http://localhost:8001

# CORS: comma-separated list of allowed frontend origins
FRONTEND_URL=http://localhost:5173
```

---

## Database Setup

### Install PostgreSQL

**Ubuntu / Debian:**
```bash
sudo apt update && sudo apt install postgresql postgresql-contrib
```

**Fedora / RHEL:**
```bash
sudo dnf install postgresql postgresql-contrib
```

**macOS (Homebrew):**
```bash
brew install postgresql && brew services start postgresql
```

### Enable password authentication

PostgreSQL defaults to `peer`/`ident` auth on Linux. Change `pg_hba.conf` to allow password connections:

```bash
# Find the file location
sudo -u postgres psql -c "SHOW hba_file;"

# Edit it (adjust path to match your version)
sudo nano /etc/postgresql/15/main/pg_hba.conf
```

Change:
```
local   all   all               peer
host    all   all  127.0.0.1/32 ident
```

To:
```
local   all   all               scram-sha-256
host    all   all  127.0.0.1/32 scram-sha-256
host    all   all  ::1/128      scram-sha-256
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### Create role and database

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE itcdreamteam WITH LOGIN PASSWORD 'your_secure_password';
CREATE DATABASE tec_final_assessment OWNER itcdreamteam;
GRANT ALL PRIVILEGES ON DATABASE tec_final_assessment TO itcdreamteam;
SQL
```

---

## Installation

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then edit .env
```

### Initialize and seed the database

```bash
python -m app.db.scripts.init_db      # create tables
python -m app.db.scripts.seed_players # load 2024 MLB player stats
```

To start over:
```bash
python -m app.db.scripts.drop_db      # drop all tables
python -m app.db.scripts.init_db
python -m app.db.scripts.seed_players
```

### Start the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: **http://localhost:8000/docs**

---

## API Reference

### Authentication — `/auth`

All `/auth` routes are rate-limited to prevent brute-force attacks.

#### `POST /auth/register` — 10 req/min

Create a new user account. Sets an httpOnly cookie and also returns the token in the response body.

**Request body:**
```json
{ "email": "fan@example.com", "password": "baseball123" }
```

**Response `201`:**
```json
{
  "id": "550e8400-...",
  "email": "fan@example.com",
  "created_at": "2026-06-12T10:00:00",
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

**Errors:** `400` email already registered · `422` password < 8 characters or invalid email.

---

#### `POST /auth/login` — 20 req/min

Accepts `application/x-www-form-urlencoded` (OAuth2 form). Sets httpOnly cookie and returns token body.

**Form fields:** `username` (email), `password`

**Response `200`:**
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

**Errors:** `401` incorrect credentials.

---

#### `POST /auth/logout`

Increments `token_version` in the database, immediately invalidating all existing JWTs for this user. Clears the httpOnly cookie.

**Response `200`:** `{ "message": "Logged out" }`

---

#### `GET /auth/me`

Returns the currently authenticated user's profile. Protected — requires a valid cookie or `Authorization: Bearer <token>` header.

**Response `200`:**
```json
{ "id": "550e8400-...", "email": "fan@example.com", "created_at": "2026-06-12T10:00:00" }
```

---

### Simulations — `/simulations`

#### `POST /simulations/simulate` — 30 req/min — requires auth

Submit two 9-player lineups (by player ID) and optional bullpens. The backend resolves IDs to stat arrays, forwards the request to the Model API, aggregates the N-simulation results, and persists the match.

**Request body:**
```json
{
  "home_batter_ids": [571771, 695238, 683227, 694224, 695731, 813841, 683021, 683734, 676369],
  "away_batter_ids": [571771, 695238, 683227, 694224, 695731, 813841, 683021, 683734, 676369],
  "home_pitcher_id": 695239,
  "away_pitcher_id": 695239,
  "home_bullpen_ids": [671106, 681084],
  "away_bullpen_ids": [671106, 681084],
  "reliever_entry_inning": 6,
  "n_sims": 500,
  "seed": 42,
  "home_team": "Red Sox",
  "away_team": "Yankees"
}
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `home/away_batter_ids` | `int[9]` | required | Exactly 9 MLB player IDs |
| `home/away_pitcher_id` | `int` | required | Starting pitcher ID |
| `home/away_bullpen_ids` | `int[]` | `null` | Relief pitchers (slot order) |
| `reliever_entry_inning` | `int` | `6` | Inning when reliever enters |
| `n_sims` | `int` | `500` | 1–2000 simulations |
| `seed` | `int` | `null` | Optional random seed |

**Response `201`:**
```json
{
  "match_id": 123,
  "created_at": "2026-06-12T10:00:00",
  "home_team": "Red Sox",
  "away_team": "Yankees",
  "n_sims": 500,
  "home_wp": 0.542,
  "away_wp": 0.458,
  "home_batter_ids": [...],
  "away_batter_ids": [...],
  "home_pitcher_ids": [...],
  "away_pitcher_ids": [...],
  "whole_game": {
    "avg_home_runs": 4.3,
    "avg_away_runs": 3.8,
    "avg_home_hits": 8.1,
    "avg_away_hits": 7.6,
    "avg_home_hr": 1.1,
    "avg_away_hr": 0.9,
    "avg_home_strikeouts": 7.2,
    "avg_away_strikeouts": 8.1
  },
  "innings": [
    { "inning_number": 1, "avg_home_runs": 0.5, ... },
    ...
  ]
}
```

---

#### `GET /simulations/history` — requires auth

Returns all simulations run by the authenticated user, including lineups and per-inning averages.

**Response `200`:** array of `MatchResponse` (same shape as simulate).

---

#### `GET /simulations/dashboard` — public

Returns pre-seeded "dashboard" matches (rows with `user_id = NULL`). Used for the public predictions dashboard.

**Response `200`:** array of `MatchResponse`.

---

### Players — `/players`

#### `GET /players/player-stats`

Returns the list of all seeded players. Filter by role with the `is_batter` query parameter.

| Query param | Type | Description |
|---|---|---|
| `is_batter` | `bool` (optional) | `true` = batters only · `false` = pitchers only |

**Response `200`:**
```json
[
  {
    "id": 571771,
    "name": "Shohei Ohtani",
    "hand": "L",
    "pa_count": 636,
    "avg": 0.310,
    "obp": 0.390,
    "slg": 0.646,
    "iso": 0.336,
    "k_rate": 0.162,
    "bb_rate": 0.125,
    "hr_rate": 0.085,
    "is_rookie": "False",
    "is_batter": true
  }
]
```

---

### Schedule — `/schedule`

#### `GET /schedule`

Proxies the official MLB Stats API for the weekly schedule. Defaults to today through today + 6 days.

| Query param | Type | Default |
|---|---|---|
| `start_date` | `YYYY-MM-DD` | today |
| `end_date` | `YYYY-MM-DD` | today + 6 |

**Response `200`:**
```json
{
  "totalGames": 15,
  "games": [
    {
      "gameDate": "2026-06-12",
      "gameTime": "19:10",
      "isLive": false,
      "awayTeamId": 111,
      "awayTeamName": "Boston Red Sox",
      "homeTeamId": 147,
      "homeTeamName": "New York Yankees"
    }
  ]
}
```

---

## Authentication System

### Token lifecycle

1. On login or register, the backend creates a JWT containing `sub` (user UUID), `email`, and `ver` (current `token_version` from the DB).
2. The token is stored in an **httpOnly cookie** (sent automatically by the browser) and also returned in the JSON body (for Swagger / API clients).
3. `get_current_user` checks the `Authorization: Bearer` header first, then falls back to the `access_token` cookie. It validates the signature, expiry, and that `ver` matches the current `token_version` in the database.
4. On **logout**, `token_version` is incremented. Any token with the old `ver` is immediately rejected by `get_current_user`, even if it hasn't expired.

### Password hashing

Passwords are hashed with **Argon2** via `passlib[argon2]`. Argon2id is the winner of the Password Hashing Competition and is resistant to GPU brute-force attacks.

---

## Database Models

### `User`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | `uuid_generate_v4()` default |
| `email` | VARCHAR (unique) | validated as email |
| `password_hash` | VARCHAR | Argon2id hash |
| `token_version` | INTEGER | incremented on logout |
| `created_at` | TIMESTAMP | server default |

### `Player`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER (PK) | MLB MLBAM player ID |
| `name` | VARCHAR | player name |
| `hand` | VARCHAR | `L` / `R` / `S` |
| `pa_count` | FLOAT | plate appearances in 2024 |
| `avg` / `obp` / `slg` / `iso` | FLOAT | 2024 batting stats |
| `k_rate` / `bb_rate` / `hr_rate` | FLOAT | per-PA rates |
| `is_rookie` | VARCHAR | "True" if no 2024 data |
| `is_batter` | BOOLEAN | `true` = batter, `false` = pitcher |

### `Match`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER (PK, autoincrement) | |
| `user_id` | UUID (FK → User, nullable) | `NULL` = dashboard/public record |
| `home_team` / `away_team` | VARCHAR | team labels |
| `n_sims` | INTEGER | simulations run |
| `home_wp` / `away_wp` | FLOAT | win probabilities |
| `avg_home_runs` … `avg_away_strikeouts` | FLOAT | 8 whole-game averages |
| `created_at` | TIMESTAMP | server default |
| `match_date` / `match_time` | DATE / TIME | optional real-game metadata |

`Match` has two relationships:
- `innings` → list of `MatchInning` (per-inning averages, same 8 stat columns + `inning_number`)
- `lineup_slots` → list of `MatchLineup` (player_id, side `home`/`away`, `is_batter`, `slot_order`)

---

## Rate Limiting

Managed by **slowapi** (Starlette/FastAPI adapter for `limits`). The shared limiter singleton lives in `app/limiter.py` and is registered on `app.state.limiter`. Endpoints opt in individually:

| Endpoint | Limit |
|---|---|
| `POST /auth/register` | 10/minute |
| `POST /auth/login` | 20/minute |
| `POST /simulations/simulate` | 30/minute |

Rate-limited endpoints must include `request: Request` as their first argument.

---

## Troubleshooting

**`Ident authentication failed for user "itcdreamteam"`**
Change `pg_hba.conf` from `peer`/`ident` to `scram-sha-256` and restart PostgreSQL.

**`role "itcdreamteam" does not exist`**
Run the `CREATE ROLE` command inside `psql` as the `postgres` superuser.

**`Could not reach model API at http://localhost:8001`**
Start the Model API first: `cd model/model_api && uvicorn main:app --port 8001`.

**`ModuleNotFoundError: No module named 'app'`**
Run all scripts from inside the `backend/` directory with the virtualenv activated.

**Simulation returns `500 — Model artifact not found`**
The Model API requires `model/simulation/models/pa_model.txt` and `model/simulation/data/feature_names.csv`. See `model/README.md` for how to train the model or obtain these files.
