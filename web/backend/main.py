"""
AI Support Analyzer - Web Backend
FastAPI application for the web UI.
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Add project root to path for importing existing modules
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web.backend.core.config import get_settings
from web.backend.api.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name} Web Backend v{settings.app_version}")
    print(f"Debug mode: {settings.debug}")
    
    yield
    
    # Shutdown
    print("Shutting down...")
    
    # Cleanup job manager
    from web.backend.services.analysis_runner import get_job_manager
    job_manager = get_job_manager()
    job_manager.cleanup_old_jobs(max_age_hours=0)  # Clean all on shutdown


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Web API for AI Support Analyzer - analyze customer support data with AI",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API router
    app.include_router(api_router, prefix="/api")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": settings.app_version}
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle uncaught exceptions."""
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc) if settings.debug else "Internal server error",
                "type": type(exc).__name__
            }
        )
    
    # Serve static frontend files (built React app)
    frontend_dist = PROJECT_ROOT / "web" / "frontend" / "dist"
    if frontend_dist.exists():
        index_html = frontend_dist / "index.html"
        
        # Mount static assets directory
        assets_dir = frontend_dist / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static-assets")
        
        # Serve favicon
        favicon_path = frontend_dist / "favicon.svg"
        
        @app.get("/favicon.svg")
        async def serve_favicon():
            """Serve the favicon."""
            if favicon_path.exists():
                return FileResponse(favicon_path, media_type="image/svg+xml")
            return JSONResponse(status_code=404, content={"detail": "Favicon not found"})
        
        # Serve index.html at root
        @app.get("/")
        async def serve_root():
            """Serve the React SPA at root."""
            if index_html.exists():
                return FileResponse(index_html, media_type="text/html")
            return JSONResponse(status_code=404, content={"detail": "Frontend not built"})
        
        # Serve index.html for SPA routing (catch-all for non-API routes)
        @app.get("/{path:path}")
        async def serve_spa(path: str):
            """Serve the React SPA for any non-API route."""
            # Skip if path starts with 'api' (handled by API router)
            if path.startswith("api"):
                return JSONResponse(status_code=404, content={"detail": "Not found"})
            
            # Serve index.html for SPA client-side routing
            if index_html.exists():
                return FileResponse(index_html, media_type="text/html")
            return JSONResponse(status_code=404, content={"detail": "Frontend not built"})
    else:
        # No frontend built - serve API info at root
        @app.get("/")
        async def root():
            """Root endpoint with API information."""
            return {
                "name": settings.app_name,
                "version": settings.app_version,
                "docs": "/api/docs",
                "health": "/health",
                "note": "Frontend not built. Run 'npm run build' in web/frontend/"
            }
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
