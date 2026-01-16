"""
Analysis API routes.
Provides endpoints for running analyses and tracking progress.
"""

import sys
import os
import uuid
import glob
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse

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
    custom_ticket_analysis: bool = Form(False),
    visualization: bool = Form(False),
    custom_prompt: Optional[str] = Form(None),
    custom_columns: Optional[str] = Form(None),
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
        
        # Parse custom_columns if provided (comma-separated string)
        parsed_custom_columns = None
        if custom_columns:
            parsed_custom_columns = [c.strip() for c in custom_columns.split(',') if c.strip()]

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
            custom_ticket_analysis=custom_ticket_analysis,
            visualization=visualization,
            custom_prompt=custom_prompt,
            custom_columns=parsed_custom_columns,
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


# ============== File Management ==============

@router.get("/{job_id}/files")
async def list_job_files(job_id: str):
    """
    List output files from a completed analysis.

    Returns a list of files generated by the analysis job.
    """
    job_manager = get_job_manager()
    status = job_manager.get_job_status(job_id)

    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get the upload directory to search for output files
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)

    if not upload_dir.exists():
        return {"files": []}

    # Find output files by looking for files with the job_id prefix or common output patterns
    files = []

    # Search patterns for output files
    patterns = [
        f"{job_id}_*support-analysis-output*.csv",
        f"{job_id}_*-clean*.csv",
        f"{job_id}_*-preclean*.csv",
        f"{job_id}_*predictive-csat*.csv",
        f"{job_id}_*custom-ticket-analysis-output*.csv",
        f"*support-analysis-output*.csv",
        f"*-clean*.csv",
        f"*predictive-csat*.csv",
        f"*custom-ticket-analysis-output*.csv",
        f"*-trends*.txt",
        f"*-topics*.txt",
        f"*-feedback*.txt",
    ]

    found_files = set()
    for pattern in patterns:
        matches = glob.glob(str(upload_dir / pattern))
        for match in matches:
            found_files.add(match)

    # Also check the output_file from job status
    if status.output_file and os.path.exists(status.output_file):
        found_files.add(status.output_file)
        # Also check the directory of the output file
        output_dir = os.path.dirname(status.output_file)
        if output_dir != str(upload_dir):
            for pattern in patterns:
                matches = glob.glob(os.path.join(output_dir, pattern))
                for match in matches:
                    found_files.add(match)

    for file_path in found_files:
        if os.path.exists(file_path):
            stat = os.stat(file_path)
            files.append({
                "name": os.path.basename(file_path),
                "path": file_path,
                "size_mb": stat.st_size / (1024 * 1024),
                "modified": stat.st_mtime,
                "modified_date": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })

    # Sort by modification time, newest first
    files.sort(key=lambda x: x["modified"], reverse=True)

    return {"files": files}


@router.get("/{job_id}/files/{filename}")
async def download_job_file(job_id: str, filename: str):
    """
    Download a specific output file from an analysis job.
    """
    job_manager = get_job_manager()
    status = job_manager.get_job_status(job_id)

    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Security: validate filename doesn't contain path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Search for the file in possible locations
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)

    possible_paths = [
        upload_dir / filename,
    ]

    # Also check the directory of the output file
    if status.output_file:
        output_dir = os.path.dirname(status.output_file)
        possible_paths.append(Path(output_dir) / filename)

    for file_path in possible_paths:
        if file_path.exists():
            return FileResponse(
                path=str(file_path),
                filename=filename,
                media_type="application/octet-stream"
            )

    raise HTTPException(status_code=404, detail="File not found")
