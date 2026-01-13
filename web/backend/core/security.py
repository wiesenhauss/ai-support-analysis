"""
Security utilities for API key validation.
"""

import os
import json
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, status

from .config import get_settings

# Settings file location (same as settings routes)
SETTINGS_DIR = Path.home() / ".ai_support_analyzer"
SETTINGS_FILE = SETTINGS_DIR / "web_settings.json"


def _load_settings_file() -> dict:
    """Load settings from file."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def get_openai_api_key() -> str:
    """
    Get the OpenAI API key from settings file, config, or environment.
    
    Priority:
    1. Settings file (~/.ai_support_analyzer/web_settings.json)
    2. Config settings (pydantic settings)
    3. Environment variable (OPENAI_API_KEY)
    
    Raises:
        HTTPException: If no API key is configured.
    """
    # First check settings file
    file_settings = _load_settings_file()
    if file_settings.get("openai_api_key"):
        return file_settings["openai_api_key"]
    
    # Then check pydantic settings
    settings = get_settings()
    if settings.openai_api_key:
        return settings.openai_api_key
    
    # Finally check environment
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key:
        return env_key
    
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="OpenAI API key not configured. Please add your API key in Settings."
    )


def validate_api_key(api_key: Optional[str]) -> bool:
    """
    Validate that an API key looks like a valid OpenAI key.
    
    Args:
        api_key: The API key to validate.
        
    Returns:
        True if the key appears valid.
    """
    if not api_key:
        return False
    
    # OpenAI keys typically start with 'sk-' and are fairly long
    return api_key.startswith("sk-") and len(api_key) > 20
