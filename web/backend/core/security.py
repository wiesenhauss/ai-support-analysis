"""
Security utilities for API key validation.
"""

import os
from typing import Optional
from fastapi import HTTPException, status

from .config import get_settings


def get_openai_api_key() -> str:
    """
    Get the OpenAI API key from settings or environment.
    
    Raises:
        HTTPException: If no API key is configured.
    """
    settings = get_settings()
    
    # Try settings first, then environment
    api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
        )
    
    return api_key


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
