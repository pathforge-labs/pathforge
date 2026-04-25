"""
PathForge — Auth Dependencies
==============================
Public auth dependency re-exports for route handlers.

This module provides a stable import path for authentication
dependencies. Internally delegates to app.core.security.

Usage:
    from app.core.auth import get_current_user
"""

from app.core.security import get_current_user

__all__ = ["get_current_user"]
