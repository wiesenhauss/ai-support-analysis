"""
Pydantic schemas for analysis endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class AnalysisStatus(str, Enum):
    """Status of an analysis job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisOptions(BaseModel):
    """Options for running an analysis."""
    main_analysis: bool = True
    data_cleanup: bool = True
    predict_csat: bool = True
    topic_aggregator: bool = True
    csat_trends: bool = True
    product_feedback: bool = True
    goals_trends: bool = True
    custom_analysis: bool = False
    custom_ticket_analysis: bool = False
    visualization: bool = False
    auto_import: bool = True  # Auto-import results to database after analysis
    custom_prompt: Optional[str] = None
    custom_columns: Optional[List[str]] = None
    limit: Optional[int] = None
    threads: int = 50


class AnalysisJobCreate(BaseModel):
    """Request to create a new analysis job."""
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)


class AnalysisJobStatus(BaseModel):
    """Status of an analysis job."""
    job_id: str
    status: AnalysisStatus
    progress: float = 0.0  # 0-100
    current_step: str = ""
    total_rows: Optional[int] = None
    processed_rows: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    output_file: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    import_stats: Optional[Dict[str, Any]] = None  # Auto-import results: imported, duplicates, period


class AnalysisJobResponse(BaseModel):
    """Response after starting an analysis."""
    job_id: str
    status: AnalysisStatus
    message: str


class AnalysisResultSummary(BaseModel):
    """Summary of analysis results."""
    total_analyzed: int = 0
    sentiment_distribution: Dict[str, int] = Field(default_factory=dict)
    top_topics: List[Dict[str, Any]] = Field(default_factory=list)
    resolution_rate: float = 0.0
    output_files: List[str] = Field(default_factory=list)
