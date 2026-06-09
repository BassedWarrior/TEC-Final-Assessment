# Backend – Authentication Module

This is the authentication core of the Baseball Simulator Web App. It provides user registration, login, and JWT-based protected endpoints. The module is built with:

- **FastAPI** – async web framework
- **PostgreSQL** – database (via `asyncpg`)
- **SQLAlchemy 2.0** – async ORM
- **python-jose** – JWT handling
- **passlib[bcrypt]** – password hashing

The authentication system is fully functional and ready to be extended with player/lineup management and Monte Carlo simulation endpoints.

---

## Requirements

- Python 3.10 or higher
- PostgreSQL 12+
- `pip` and `virtualenv` (or `venv`)

---

## Database Setup (PostgreSQL)

### 1. Install PostgreSQL (if not already)

**Fedora / RHEL:**
```bash
sudo dnf update
sudo dnf install postgresql postgresql-contrib
```

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install postgresql
sudo apt install postgresql-contrib
```

**macOS (Homebrew)**:
```bash
brew install postgresql
brew services start postgresql
```

**Windows**: Use the official installer from [postgresql.org](postgresql.org) or use WSL2.

### 2. Configure password authentication

PostgreSQL on many Linux distributions uses peer or ident authentication for local connections by default. This forces the OS user to match the database user. To allow password‑based connections (required for our connection strings), edit `pg_hba.conf`:

- Locate the file:
    ```bash
    sudo -u postgres psql -c "SHOW hba_file;"
    ```
- Edit with `sudo nano` (or your editor):
    ```bash
    sudo nano /etc/postgresql/15/main/pg_hba.conf   # adjust version/path
    ```
- Find the lines:
    ```text
    local   all             all                                     peer
    host    all             all             127.0.0.1/32            ident
    ```
- Change peer and `ident` to `scram-sha-256`:
    ```text
    local   all             all                                     scram-sha-256
    host    all             all             127.0.0.1/32            scram-sha-256
    host    all             all             ::1/128                 scram-sha-256
    ```
- Save and restart PostgreSQL:
    ```bash
    sudo systemctl restart postgresql
    ```

### 3. Create the database role and database

We'll use a dedicated role `itcdreamteam` (instead of the default `postgres`
superuser) and a database named tec\_final\_assessment.
```bash
# Connect as the postgres superuser
sudo -u postgres psql
```

Inside the psql shell, run:
```sql
CREATE ROLE itcdreamteam WITH LOGIN PASSWORD 'your_secure_password';
CREATE DATABASE tec_final_assessment OWNER itcdreamteam;
GRANT ALL PRIVILEGES ON DATABASE tec_final_assessment TO itcdreamteam;
\q
```

### 4. Set the environment variables

Create a .env file inside the backend/ directory:
```env
# PostgreSQL connection – use the role and database you created
DATABASE_URL=postgresql+asyncpg://itcdreamteam:your_secure_password@localhost:5432/tec_final_assessment

# JWT settings
SECRET_KEY=your-super-secret-key-please-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Project Structure

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Loads .env
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py             # SQLAlchemy async engine + Base
│   │   └── session.py          # get_db() dependency
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py             # User SQLAlchemy model
│   ├── api/
│   │   ├── __init__.py
│   │   └── auth.py             # /auth/register, /auth/login, /auth/me
│   └── core/
│       ├── __init__.py
│       ├── security.py         # password hashing, JWT create
│       └── dependencies.py     # get_current_user
├── init_db.py                  # One‑time script to create tables
├── requirements.txt            # Dependencies
├── .gitignore                  # Ignore `.env` file, for example
├── .env                        # Environment Variable Secrets
├── .env.example                # Example File
└── README.md
```

## Installation & Running

### 1. Create virtual environment and install dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Contents of `requirements.txt`:
```text
fastapi
uvicorn[standard]
sqlalchemy
asyncpg
python-dotenv
python-jose[cryptography]
passlib
argon2-cffi
pydantic[email]
python-multipart
```

### 2. Create the database tables

Run the one‑time initialization script:
```bash
python init_db.py
```

This script connects to the database using the `DATABASE_URL` from `.env` and
creates the `users` table (and any other models you add later). It will not
drop existing tables – only create missing ones.

### 3. Start the FastAPI server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:

```text
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 4. Test the authentication endpoints

Open your browser at http://localhost:8000/docs – the interactive Swagger UI
will show:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

**Using `curl`**:

Register a user:

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"fan@example.com","password":"baseball123"}'
```

Login to get a JWT:

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=fan@example.com&password=baseball123"
```

Response:

```json
{"access_token":"eyJ...","token_type":"bearer"}
```

Get current user (protected):

```bash
TOKEN="eyJ..."
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

## Troubleshooting

**`Ident authentication failed for user "itcdreamteam"`**

- You forgot to change `pg_hba.conf` from `peer`/`ident` to `scram-sha-256`.
    Follow step 2 in Database Setup.

**`role "itcdreamteam" does not exist`**

- The PostgreSQL role was not created. Connect as `postgres` and run the
    `CREATE ROLE` command.

**`database "tec_final_assessment" does not exist`**

- Run `CREATE DATABASE` inside `psql` as shown above.

**`ModuleNotFoundError: No module named 'app'`**

- Make sure you run the scripts from the `backend/` directory (where `app/` is
    located). Or set `PYTHONPATH=..`

**`Permission denied when editing pg_hba.conf`**

- Use `sudo` with your editor. Example: `sudo nano /etc/postgresql/15/main/pg_hba.conf`

## Next Steps

Once authentication works, you can extend the backend with:

- Player management – CRUD endpoints for batters/pitchers
-   Lineup creation – user‑owned batting orders
-   Monte Carlo simulation – Celery + LightGBM model integration
-   Real‑time progress – WebSockets or polling

The existing `get_current_user` dependency will protect all new endpoints,
ensuring that lineups and simulations belong to the authenticated user.
