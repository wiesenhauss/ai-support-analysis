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


EXPECTED_COLUMNS = [
    {"name": "Interaction Message Body", "aliases": ["Ticket Message Body"], "required": True,
     "description": "Full conversation text of the support ticket"},
    {"name": "Created Date", "aliases": [], "required": True,
     "description": "Ticket creation timestamp"},
    {"name": "CSAT Rating", "aliases": [], "required": False,
     "description": "Customer satisfaction rating (good/bad)"},
    {"name": "CSAT Reason", "aliases": [], "required": False,
     "description": "Reason for the satisfaction rating"},
    {"name": "CSAT Comment", "aliases": [], "required": False,
     "description": "Customer's comment about their experience"},
    {"name": "Tags", "aliases": [], "required": False,
     "description": "Zendesk tags (used for filtering)"},
]


class ValidateColumnsRequest(BaseModel):
    """Request to validate CSV columns against expected columns."""
    columns: List[str]


class ColumnMatchInfo(BaseModel):
    """Info about a single expected column's match status."""
    expected_name: str
    matched_column: Optional[str] = None
    required: bool = False
    description: str = ""


class ValidateColumnsResponse(BaseModel):
    """Response from column validation."""
    all_required_matched: bool
    columns: List[ColumnMatchInfo]
    available_columns: List[str]


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
    column_mapping: Optional[Dict[str, str]] = None
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
