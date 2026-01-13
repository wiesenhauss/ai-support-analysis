"""
Analysis API routes.
Provides endpoints for running analyses and tracking progress.
"""

import sys
import os
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web.backend.schemas.analysis import (
    AnalysisStatus, AnalysisOptions, AnalysisJobCreate,
    AnalysisJobStatus, AnalysisJobResponse
)
from web.backend.api.deps import require_api_key
from web.backend.core.config import get_settings
from web.backend.services.analysis_runner import get_job_manager, AnalysisJobManager

router = APIRouter()


@router.post("/start", response_model=AnalysisJobResponse)
async def start_analysis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    main_analysis: bool = Form(True),
    data_cleanup: bool = Form(True),
    predict_csat: bool = Form(True),
    topic_aggregator: bool = Form(True),
    csat_trends: bool = Form(True),
    product_feedback: bool = Form(True),
    goals_trends: bool = Form(True),
    custom_analysis: bool = Form(False),
    visualization: bool = Form(False),
    limit: Optional[int] = Form(None),
    threads: int = Form(50),
    api_key: str = Depends(require_api_key)
):
    """
    Start a new analysis job.
    
    Uploads a CSV file and starts processing it with the specified options.
    Returns a job_id that can be used to track progress.
    """
    settings = get_settings()
    
    # Validate file
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Create upload directory
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate job ID
    job_id = str(uuid.uuid4())[:8]
    
    # Save uploaded file
    file_path = upload_dir / f"{job_id}_{file.filename}"
    try:
        content = await file.read()
        
        # Check file size
        size_mb = len(content) / (1024 * 1024)
        if size_mb > settings.max_upload_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB"
            )
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Create options object
        options = AnalysisOptions(
            main_analysis=main_analysis,
            data_cleanup=data_cleanup,
            predict_csat=predict_csat,
            topic_aggregator=topic_aggregator,
            csat_trends=csat_trends,
            product_feedback=product_feedback,
            goals_trends=goals_trends,
            custom_analysis=custom_analysis,
            visualization=visualization,
            limit=limit,
            threads=threads
        )
        
        # Start analysis in background
        job_manager = get_job_manager()
        await job_manager.start_analysis(job_id, str(file_path), options, api_key)
        
        return AnalysisJobResponse(
            job_id=job_id,
            status=AnalysisStatus.PENDING,
            message=f"Analysis job {job_id} started"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")


@router.get("/{job_id}/status", response_model=AnalysisJobStatus)
async def get_job_status(job_id: str):
    """Get the status of an analysis job."""
    job_manager = get_job_manager()
    status = job_manager.get_job_status(job_id)
    
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return status


@router.delete("/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running analysis job."""
    job_manager = get_job_manager()
    success = await job_manager.cancel_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or already completed")
    
    return {"message": f"Job {job_id} cancelled"}


@router.get("/")
async def list_jobs():
    """List all analysis jobs."""
    job_manager = get_job_manager()
    jobs = job_manager.list_jobs()
    
    return {
        "jobs": [
            {
                "job_id": job.job_id,
                "status": job.status.value,
                "progress": job.progress,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
            for job in jobs
        ]
    }


@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    last_n: int = 100
):
    """Get the last N log lines for a job."""
    job_manager = get_job_manager()
    status = job_manager.get_job_status(job_id)
    
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job_id,
        "logs": status.logs[-last_n:] if status.logs else []
    }
