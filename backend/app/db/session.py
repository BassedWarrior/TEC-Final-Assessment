"""
Database session re-export.

Simplifies imports: 'from app.db.session import get_db'.
"""

from app.db.base import get_db

__all__ = ["get_db"]
