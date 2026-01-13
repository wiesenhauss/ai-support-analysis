"""
Pydantic schemas for data management endpoints.
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class BatchInfo(BaseModel):
    """Information about an import batch."""
    id: int
    import_date: datetime
    source_file: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    total_tickets: int = 0
    new_tickets: int = 0
    notes: Optional[str] = None


class BatchListResponse(BaseModel):
    """Response containing list of batches."""
    batches: List[BatchInfo] = Field(default_factory=list)
    total_count: int = 0


class ImportResult(BaseModel):
    """Result of CSV import operation."""
    batch_id: int
    total_rows: int
    imported: int
    duplicates: int
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class TicketInfo(BaseModel):
    """Information about a single ticket."""
    id: int
    ticket_id: Optional[str] = None
    created_date: Optional[date] = None
    csat_rating: Optional[str] = None
    sentiment: Optional[str] = None
    issue_resolved: Optional[bool] = None
    main_topic: Optional[str] = None
    customer_goal: Optional[str] = None
    detail_summary: Optional[str] = None
    product_area: Optional[str] = None


class TicketListResponse(BaseModel):
    """Response containing list of tickets."""
    tickets: List[TicketInfo] = Field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 50


class TicketFilters(BaseModel):
    """Filters for ticket queries."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    sentiment: Optional[str] = None
    csat_rating: Optional[str] = None
    main_topic: Optional[str] = None
    product_area: Optional[str] = None
    issue_resolved: Optional[bool] = None
    search: Optional[str] = None


class DatabaseStats(BaseModel):
    """Database statistics."""
    total_tickets: int = 0
    total_batches: int = 0
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    sentiment_distribution: Dict[str, int] = Field(default_factory=dict)
    resolution_rate: float = 0.0
    db_path: str = ""
    db_size_mb: float = 0.0


class TalkToDataQuestion(BaseModel):
    """Request for Talk to Data."""
    question: str
    columns: Optional[List[str]] = None
    is_follow_up: bool = False


class TalkToDataResponse(BaseModel):
    """Response from Talk to Data."""
    answer: str
    selected_columns: List[str] = Field(default_factory=list)
    token_count: int = 0
    conversation_id: Optional[str] = None
