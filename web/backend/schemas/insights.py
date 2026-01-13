"""
Pydantic schemas for insights endpoints.
"""

from datetime import date
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class InsightType(str, Enum):
    """Types of insights."""
    SENTIMENT_CHANGE = "sentiment_change"
    RESOLUTION_CHANGE = "resolution_change"
    CSAT_CHANGE = "csat_change"
    EMERGING_TOPIC = "emerging_topic"
    DECLINING_TOPIC = "declining_topic"
    VOLUME_SPIKE = "volume_spike"
    AI_FEEDBACK_TREND = "ai_feedback_trend"
    PRODUCT_VS_SERVICE = "product_vs_service"


class InsightSeverity(str, Enum):
    """Severity levels for insights."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class InsightResponse(BaseModel):
    """Single insight response."""
    type: str
    severity: str
    title: str
    description: str
    metric_name: str
    current_value: float
    previous_value: float
    change_percent: float
    period_start: str
    period_end: str
    recommendations: List[str] = Field(default_factory=list)


class InsightsSummary(BaseModel):
    """Summary of multiple insights."""
    total: int = 0
    critical: int = 0
    warning: int = 0
    info: int = 0
    top_concerns: List[Dict[str, Any]] = Field(default_factory=list)
    positive_trends: List[Dict[str, Any]] = Field(default_factory=list)


class InsightsListResponse(BaseModel):
    """Response containing list of insights with summary."""
    insights: List[InsightResponse] = Field(default_factory=list)
    summary: InsightsSummary = Field(default_factory=InsightsSummary)


class EmergingProductInsight(BaseModel):
    """Emerging product insight."""
    product_area: str
    growth_pct: float
    ticket_count: int
    negative_pct: float
    impact_score: float


class PeriodComparisonRequest(BaseModel):
    """Request for period comparison."""
    period1_start: date
    period1_end: date
    period2_start: date
    period2_end: date


class PeriodComparisonResponse(BaseModel):
    """Response for period comparison."""
    period1: Dict[str, Any]
    period2: Dict[str, Any]
    metrics: Dict[str, Any]
