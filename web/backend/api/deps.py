"""
FastAPI dependencies for routes.
"""

import sys
from pathlib import Path
from typing import Generator

# Add project root to path for importing existing modules
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import Depends, HTTPException, status

from web.backend.core.config import get_settings, Settings
from web.backend.core.security import get_openai_api_key


def get_analytics_engine_dep():
    """
    Dependency to get the analytics engine.
    Lazily imports to avoid circular imports.
    """
    from analytics_engine import get_analytics_engine
    return get_analytics_engine()


def get_insights_engine_dep():
    """
    Dependency to get the insights engine.
    Lazily imports to avoid circular imports.
    """
    from insights_engine import get_insights_engine
    return get_insights_engine()


def get_data_store_dep():
    """
    Dependency to get the data store.
    Lazily imports to avoid circular imports.
    """
    from data_store import get_data_store
    settings = get_settings()
    return get_data_store(settings.db_path)


def require_api_key() -> str:
    """
    Dependency that requires a valid OpenAI API key.
    Use this for endpoints that need to make OpenAI API calls.
    """
    return get_openai_api_key()
