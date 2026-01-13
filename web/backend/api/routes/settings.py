"""
Settings API routes.
Provides endpoints for managing application settings including API keys.
"""

import os
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Settings file location
SETTINGS_DIR = Path.home() / ".ai_support_analyzer"
SETTINGS_FILE = SETTINGS_DIR / "web_settings.json"


class APIKeyUpdate(BaseModel):
    """Request to update API key."""
    api_key: str


class APIKeyStatus(BaseModel):
    """API key status response."""
    configured: bool
    masked_key: Optional[str] = None
    source: str = "none"  # "settings_file", "environment", "none"


class SettingsResponse(BaseModel):
    """Full settings response."""
    api_key_status: APIKeyStatus


def _load_settings() -> dict:
    """Load settings from file."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_settings(settings: dict):
    """Save settings to file."""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)
    # Set restrictive permissions on the file (owner read/write only)
    os.chmod(SETTINGS_FILE, 0o600)


def _mask_api_key(key: str) -> str:
    """Mask an API key for display, showing only first and last 4 chars."""
    if len(key) <= 12:
        return "****"
    return f"{key[:7]}...{key[-4:]}"


def _get_current_api_key() -> tuple[Optional[str], str]:
    """
    Get the current API key and its source.
    
    Returns:
        Tuple of (api_key, source) where source is one of:
        - "settings_file": Key from web settings file
        - "environment": Key from OPENAI_API_KEY env var
        - "none": No key configured
    """
    # First check settings file
    settings = _load_settings()
    if settings.get("openai_api_key"):
        return settings["openai_api_key"], "settings_file"
    
    # Then check environment
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key:
        return env_key, "environment"
    
    return None, "none"


@router.get("/", response_model=SettingsResponse)
async def get_settings():
    """Get current settings."""
    api_key, source = _get_current_api_key()
    
    return SettingsResponse(
        api_key_status=APIKeyStatus(
            configured=api_key is not None,
            masked_key=_mask_api_key(api_key) if api_key else None,
            source=source
        )
    )


@router.get("/api-key/status", response_model=APIKeyStatus)
async def get_api_key_status():
    """Get the status of the OpenAI API key configuration."""
    api_key, source = _get_current_api_key()
    
    return APIKeyStatus(
        configured=api_key is not None,
        masked_key=_mask_api_key(api_key) if api_key else None,
        source=source
    )


@router.post("/api-key")
async def set_api_key(request: APIKeyUpdate):
    """
    Set the OpenAI API key.
    
    The key is stored in a local settings file with restricted permissions.
    """
    api_key = request.api_key.strip()
    
    # Validate the key format
    if not api_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty")
    
    if not api_key.startswith("sk-"):
        raise HTTPException(
            status_code=400, 
            detail="Invalid API key format. OpenAI keys should start with 'sk-'"
        )
    
    if len(api_key) < 20:
        raise HTTPException(
            status_code=400,
            detail="API key appears to be too short"
        )
    
    # Save to settings file
    settings = _load_settings()
    settings["openai_api_key"] = api_key
    _save_settings(settings)
    
    # Also set in environment for current session
    os.environ["OPENAI_API_KEY"] = api_key
    
    return {
        "message": "API key saved successfully",
        "masked_key": _mask_api_key(api_key)
    }


@router.delete("/api-key")
async def delete_api_key():
    """
    Remove the stored OpenAI API key.
    
    Note: This only removes the key from the settings file.
    If a key is set via environment variable, that will still be used.
    """
    settings = _load_settings()
    
    if "openai_api_key" in settings:
        del settings["openai_api_key"]
        _save_settings(settings)
    
    # Check if there's still an env var
    env_key = os.environ.get("OPENAI_API_KEY")
    
    return {
        "message": "API key removed from settings",
        "environment_key_exists": env_key is not None
    }


@router.post("/api-key/validate")
async def validate_api_key(request: APIKeyUpdate):
    """
    Validate an API key by making a test request to OpenAI.
    """
    import openai
    
    api_key = request.api_key.strip()
    
    if not api_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty")
    
    try:
        client = openai.OpenAI(api_key=api_key)
        # Make a minimal API call to validate the key
        client.models.list()
        
        return {
            "valid": True,
            "message": "API key is valid"
        }
    except openai.AuthenticationError:
        return {
            "valid": False,
            "message": "Invalid API key - authentication failed"
        }
    except openai.APIConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Could not connect to OpenAI API. Check your internet connection."
        )
    except Exception as e:
        return {
            "valid": False,
            "message": f"Validation failed: {str(e)}"
        }
