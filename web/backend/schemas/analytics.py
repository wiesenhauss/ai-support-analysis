"""
Pydantic schemas for analytics endpoints.
"""

from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SentimentDistribution(BaseModel):
    """Sentiment distribution statistics."""
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    total: int = 0
    positive_pct: float = 0.0
    neutral_pct: float = 0.0
    negative_pct: float = 0.0


class ResolutionStats(BaseModel):
    """Issue resolution statistics."""
    total: int = 0
    resolved: int = 0
    unresolved: int = 0
    unknown: int = 0
    resolution_rate: float = 0.0


class CSATStats(BaseModel):
    """CSAT statistics."""
    good: int = 0
    bad: int = 0
    no_rating: int = 0
    total: int = 0
    response_rate: float = 0.0
    satisfaction_rate: float = 0.0


class TopicItem(BaseModel):
    """Single topic in distribution."""
    topic: str
    count: int
    percentage: float


class SummaryStats(BaseModel):
    """Comprehensive summary statistics."""
    date_range: Dict[str, Optional[str]] = Field(default_factory=dict)
    ticket_count: int = 0
    sentiment: SentimentDistribution = Field(default_factory=SentimentDistribution)
    resolution: ResolutionStats = Field(default_factory=ResolutionStats)
    csat: CSATStats = Field(default_factory=CSATStats)
    top_topics: List[TopicItem] = Field(default_factory=list)
    product_related: int = 0
    service_related: int = 0
    ai_feedback_count: int = 0


class TrendDataPoint(BaseModel):
    """Single data point in a trend."""
    period: str
    value: float
    count: Optional[int] = None


class SentimentTrendPoint(BaseModel):
    """Sentiment trend data point."""
    period: str
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    total: int = 0
    positive_pct: float = 0.0
    neutral_pct: float = 0.0
    negative_pct: float = 0.0


class CSATTrendPoint(BaseModel):
    """CSAT trend data point."""
    period: str
    good: int = 0
    bad: int = 0
    rated: int = 0
    satisfaction_rate: float = 0.0


class ResolutionTrendPoint(BaseModel):
    """Resolution trend data point."""
    period: str
    resolved: int = 0
    total: int = 0
    unresolved: int = 0
    resolution_rate: float = 0.0


class TopicTrendPoint(BaseModel):
    """Topic trend data point."""
    period: str
    count: int = 0
    percentage: float = 0.0


class PeriodComparison(BaseModel):
    """Period-over-period comparison results."""
    period1: Dict[str, Any]
    period2: Dict[str, Any]
    changes: Dict[str, float]
