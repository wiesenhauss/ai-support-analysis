"""API routes for the web backend."""

from fastapi import APIRouter

from . import analytics, insights, data, analysis, talk, settings

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(insights.router, prefix="/insights", tags=["Insights"])
api_router.include_router(data.router, prefix="/data", tags=["Data Management"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
api_router.include_router(talk.router, prefix="/talk", tags=["Talk to Data"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
