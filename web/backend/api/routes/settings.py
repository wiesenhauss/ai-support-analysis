"""
Settings API routes.
Provides endpoints for managing application settings including API keys,
custom per-ticket analyses, custom prompts, and advanced settings.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

# Settings file location
SETTINGS_DIR = Path.home() / ".ai_support_analyzer"
SETTINGS_FILE = SETTINGS_DIR / "web_settings.json"


# ============== API Key Models ==============

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


# ============== Custom Per-Ticket Analysis Models ==============

class CustomTicketAnalysis(BaseModel):
    """Single custom per-ticket analysis configuration."""
    name: str = Field(..., description="Column name suffix (e.g., 'IS_REFUND_REQUEST' -> 'CUSTOM_IS_REFUND_REQUEST')")
    prompt: str = Field(..., description="AI prompt to evaluate against each ticket")
    result_type: str = Field(default="boolean", description="'boolean' or 'string'")
    description: str = Field(default="", description="Optional description for UI display")
    columns: List[str] = Field(default_factory=list, description="CSV columns to include in AI context")
    enabled: bool = Field(default=True, description="Whether this analysis is enabled for execution")


class CustomTicketAnalysesRequest(BaseModel):
    """Request to save custom ticket analyses."""
    analyses: List[CustomTicketAnalysis]


class CustomTicketAnalysesResponse(BaseModel):
    """Response with custom ticket analyses."""
    analyses: List[CustomTicketAnalysis]


# ============== Custom Prompt Models ==============

class CustomPrompt(BaseModel):
    """Custom prompt template for aggregate analysis."""
    name: str
    prompt: str
    columns: List[str] = Field(default_factory=list)
    created: Optional[str] = None
    last_used: Optional[str] = None


class CustomPromptsResponse(BaseModel):
    """Response with all custom prompts."""
    prompts: Dict[str, CustomPrompt]


# ============== Advanced Settings Models ==============

class AdvancedSettings(BaseModel):
    """Advanced configuration settings."""
    api_timeout: int = Field(default=60, description="API timeout in seconds")
    max_retries: int = Field(default=3, description="Max API retry attempts")
    batch_size: int = Field(default=100, description="Records per processing batch")
    concurrent_threads: int = Field(default=50, ge=1, le=100, description="Parallel threads (1-100)")


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


# ============== Custom Per-Ticket Analysis Endpoints ==============

@router.get("/custom-ticket-analyses", response_model=CustomTicketAnalysesResponse)
async def get_custom_ticket_analyses():
    """Get all custom per-ticket analysis configurations."""
    settings = _load_settings()
    analyses_data = settings.get("custom_ticket_analyses", [])
    analyses = [CustomTicketAnalysis(**a) for a in analyses_data]
    return CustomTicketAnalysesResponse(analyses=analyses)


@router.post("/custom-ticket-analyses")
async def save_custom_ticket_analyses(request: CustomTicketAnalysesRequest):
    """Save all custom per-ticket analysis configurations."""
    settings = _load_settings()

    # Validate analyses
    for analysis in request.analyses:
        if not analysis.name:
            raise HTTPException(status_code=400, detail="Analysis name cannot be empty")
        if not analysis.prompt:
            raise HTTPException(status_code=400, detail=f"Prompt cannot be empty for analysis '{analysis.name}'")
        if analysis.result_type not in ("boolean", "string"):
            raise HTTPException(status_code=400, detail=f"Invalid result_type for '{analysis.name}': must be 'boolean' or 'string'")
        # Sanitize name - alphanumeric and underscores only
        if not all(c.isalnum() or c == '_' for c in analysis.name):
            raise HTTPException(status_code=400, detail=f"Analysis name '{analysis.name}' must contain only letters, numbers, and underscores")

    settings["custom_ticket_analyses"] = [a.dict() for a in request.analyses]
    _save_settings(settings)

    return {
        "message": f"Saved {len(request.analyses)} custom ticket analyses",
        "count": len(request.analyses)
    }


@router.delete("/custom-ticket-analyses/{name}")
async def delete_custom_ticket_analysis(name: str):
    """Delete a single custom per-ticket analysis by name."""
    settings = _load_settings()
    analyses = settings.get("custom_ticket_analyses", [])

    original_count = len(analyses)
    analyses = [a for a in analyses if a.get("name") != name]

    if len(analyses) == original_count:
        raise HTTPException(status_code=404, detail=f"Analysis '{name}' not found")

    settings["custom_ticket_analyses"] = analyses
    _save_settings(settings)

    return {"message": f"Deleted analysis '{name}'"}


# ============== Custom Prompts Endpoints ==============

@router.get("/custom-prompts", response_model=CustomPromptsResponse)
async def get_custom_prompts():
    """Get all saved custom prompt templates."""
    settings = _load_settings()
    prompts_data = settings.get("custom_prompts", {})
    prompts = {name: CustomPrompt(**data) for name, data in prompts_data.items()}
    return CustomPromptsResponse(prompts=prompts)


@router.post("/custom-prompts/{name}")
async def save_custom_prompt(name: str, prompt: CustomPrompt):
    """Save or update a custom prompt template."""
    if not name:
        raise HTTPException(status_code=400, detail="Prompt name cannot be empty")
    if not prompt.prompt:
        raise HTTPException(status_code=400, detail="Prompt text cannot be empty")

    settings = _load_settings()
    if "custom_prompts" not in settings:
        settings["custom_prompts"] = {}

    # Set metadata
    prompt.name = name
    if not prompt.created:
        prompt.created = datetime.now().isoformat()
    prompt.last_used = datetime.now().isoformat()

    settings["custom_prompts"][name] = prompt.dict()
    _save_settings(settings)

    return {"message": f"Saved prompt '{name}'"}


@router.delete("/custom-prompts/{name}")
async def delete_custom_prompt(name: str):
    """Delete a custom prompt template."""
    settings = _load_settings()
    prompts = settings.get("custom_prompts", {})

    if name not in prompts:
        raise HTTPException(status_code=404, detail=f"Prompt '{name}' not found")

    del prompts[name]
    settings["custom_prompts"] = prompts
    _save_settings(settings)

    return {"message": f"Deleted prompt '{name}'"}


# ============== Advanced Settings Endpoints ==============

@router.get("/advanced", response_model=AdvancedSettings)
async def get_advanced_settings():
    """Get advanced configuration settings."""
    settings = _load_settings()
    advanced = settings.get("advanced_settings", {})
    return AdvancedSettings(**advanced)


@router.post("/advanced")
async def save_advanced_settings(request: AdvancedSettings):
    """Save advanced configuration settings."""
    # Validate thread count range (already done by Pydantic ge/le, but double-check)
    if not 1 <= request.concurrent_threads <= 100:
        raise HTTPException(
            status_code=400,
            detail="concurrent_threads must be between 1 and 100"
        )

    if request.api_timeout < 1:
        raise HTTPException(status_code=400, detail="api_timeout must be at least 1 second")

    if request.max_retries < 0:
        raise HTTPException(status_code=400, detail="max_retries cannot be negative")

    if request.batch_size < 1:
        raise HTTPException(status_code=400, detail="batch_size must be at least 1")

    settings = _load_settings()
    settings["advanced_settings"] = request.dict()
    _save_settings(settings)

    return {
        "message": "Advanced settings saved successfully",
        "settings": request.dict()
    }
