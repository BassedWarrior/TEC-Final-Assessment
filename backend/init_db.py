"""One-Time DataBase initialization script.

This script is only meant to be run once to setup the Data Base for later use
with SQLAlchemy. It is not intended for anything else, and requires previous
configuration of a PostgreSQL server, with the right Data Base already created,
and the right PostgreSQL role (user) with appropriate password to be set up.
Both as part of PostgreSQL, and `.env` file with the DATABASE_URL variable.

Ensure that the `pg_hba.conf` file for client authentication methods allows the
selected PostgreSQL role (user) to authenticate using password (scram-sha-256).
Else it won't allow you to connect if the OS user name doesn't match the
PostgreSQL role name.

Creates all tables defined in SQLAlchemy models if they don't already exist.
"""

import asyncio
from app.db.base import engine, Base

# Import all models here so that Base knows about them
from app.models.user import User  # noqa: F401


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init())
