"""
Analytics API routes.
Provides endpoints for querying historical analytics data.
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web.backend.schemas.analytics import (
    SummaryStats, SentimentDistribution, ResolutionStats, CSATStats,
    TopicItem, SentimentTrendPoint, CSATTrendPoint, ResolutionTrendPoint,
    TopicTrendPoint, PeriodComparison
)
from web.backend.api.deps import get_analytics_engine_dep

router = APIRouter()


@router.get("/summary", response_model=SummaryStats)
async def get_summary_stats(
    start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    analytics_engine=Depends(get_analytics_engine_dep)
):
    """
    Get comprehensive summary statistics for a date range.
    
    Returns ticket counts, sentiment distribution, resolution rate, CSAT stats,
    and top topics.
    """
    try:
        stats = analytics_engine.get_summary_stats(start_date, end_date)
        
        # Convert to response model
        return SummaryStats(
            date_range={
                "start": str(stats.get("date_range", {}).get("start")) if stats.get("date_range", {}).get("start") else None,
                "end": str(stats.get("date_range", {}).get("end")) if stats.get("date_range", {}).get("end") else None
            },
            ticket_count=stats.get("ticket_count", 0),
            sentiment=SentimentDistribution(**stats.get("sentiment", {})),
            resolution=ResolutionStats(**stats.get("resolution", {})),
            csat=CSATStats(**stats.get("csat", {})),
            top_topics=[TopicItem(**t) for t in stats.get("top_topics", [])],
            product_related=stats.get("product_related", 0),
            service_related=stats.get("service_related", 0),
            ai_feedback_count=stats.get("ai_feedback_count", 0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting summary stats: {str(e)}")


@router.get("/sentiment-distribution")
async def get_sentiment_distribution(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    analytics_engine=Depends(get_analytics_engine_dep)
):
    """Get sentiment distribution for a date range."""
    try:
        result = analytics_engine.get_sentiment_distribution(start_date, end_date)
        return SentimentDistribution(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment-trend", response_model=List[SentimentTrendPoint])
async def get_sentiment_trend(
    granularity: str = Query("week", regex="^(day|week|month)$"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    analytics_engine=Depends(get_analytics_engine_dep)
):
    """
    Get sentiment trend over time.
    
    Args:
        granularity: Time granularity - day, week, or month
    """
    try:
        df = analytics_engine.get_sentiment_trend(granularity, start_date, end_date)
        
        if df.empty:
            return []
        
        result = []
        for _, row in df.iterrows():
            result.append(SentimentTrendPoint(
                period=str(row.get("period", "")),
                positive=int(row.get("positive", 0)),
                neutral=int(row.get("neutral", 0)),
                negative=int(row.get("negative", 0)),
                total=int(row.get("total", 0)),
                positive_pct=float(row.get("positive_pct", 0)),
                neutral_pct=float(row.get("neutral_pct", 0)),
                negative_pct=float(row.get("negative_pct", 0))
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topic-distribution", response_model=List[TopicItem])
async def get_topic_distribution(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    top_n: int = Query(10, ge=1, le=50),
    analytics_engine=Depends(get_analytics_engine_dep)
):
    """Get distribution of main topics."""
    try:
        df = analytics_engine.get_topic_distribution(start_date, end_date, top_n)
        
        if df.empty:
            return []
        
        return [
            TopicItem(
                topic=row["topic"],
                count=int(row["count"]),
                percentage=float(row["percentage"])
            )
            for _, row in df.iterrows()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topic-trend", response_model=List[TopicTrendPoint])
async def get_topic_trend(
    topic: str = Query(..., description="Topic to track"),
    granularity: str = Query("week", regex="^(day|week|month)$"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    analytics_engine=Depends(get_analytics_engine_dep)
):
    """Get trend of a specific topic over time."""
    try:
        df = analytics_engine.get_topic_trend(topic, granularity, start_date, end_date)
        
        if df.empty:
            return []
        
        return [
            TopicTrendPoint(
                period=str(row["period"]),
                count=int(row["count"]),
                percentage=float(row["percentage"])
            )
            for _, row in df.iterrows()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/csat-distribution")
async def get_csat_distribution(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    analytics_engine=Depends(get_analytics_engine_dep)
):
    """Get CSAT distribution for a date range."""
    try:
        result = analytics_engine.get_csat_distribution(start_date, end_date)
        return CSATStats(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/csat-trend", response_model=List[CSATTrendPoint])
async def get_csat_trend(
    granularity: str = Query("week", regex="^(day|week|month)$"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    analytics_engine=Depends(get_analytics_engine_dep)
):
    """Get CSAT satisfaction trend over time."""
    try:
        df = analytics_engine.get_csat_trend(granularity, start_date, end_date)
        
        if df.empty:
            return []
        
        return [
            CSATTrendPoint(
                period=str(row["period"]),
                good=int(row.get("good", 0)),
                bad=int(row.get("bad", 0)),
                rated=int(row.get("rated", 0)),
                satisfaction_rate=float(row.get("satisfaction_rate", 0))
            )
            for _, row in df.iterrows()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resolution-rate")
async def get_resolution_rate(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    analytics_engine=Depends(get_analytics_engine_dep)
):
    """Get issue resolution rate for a date range."""
    try:
        result = analytics_engine.get_resolution_rate(start_date, end_date)
        return ResolutionStats(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resolution-trend", response_model=List[ResolutionTrendPoint])
async def get_resolution_trend(
    granularity: str = Query("week", regex="^(day|week|month)$"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    analytics_engine=Depends(get_analytics_engine_dep)
):
    """Get resolution rate trend over time."""
    try:
        df = analytics_engine.get_resolution_trend(granularity, start_date, end_date)
        
        if df.empty:
            return []
        
        return [
            ResolutionTrendPoint(
                period=str(row["period"]),
                resolved=int(row.get("resolved", 0)),
                total=int(row.get("total", 0)),
                unresolved=int(row.get("unresolved", 0)),
                resolution_rate=float(row.get("resolution_rate", 0))
            )
            for _, row in df.iterrows()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare-periods", response_model=PeriodComparison)
async def compare_periods(
    period1_start: date = Query(...),
    period1_end: date = Query(...),
    period2_start: date = Query(...),
    period2_end: date = Query(...),
    analytics_engine=Depends(get_analytics_engine_dep)
):
    """Compare metrics between two time periods."""
    try:
        result = analytics_engine.compare_periods(
            period1_start, period1_end,
            period2_start, period2_end
        )
        
        # Convert dates to strings for JSON serialization
        def serialize_period(period_data):
            serialized = {}
            for key, value in period_data.items():
                if isinstance(value, date):
                    serialized[key] = str(value)
                elif isinstance(value, dict):
                    serialized[key] = serialize_period(value)
                elif isinstance(value, list):
                    serialized[key] = value
                else:
                    serialized[key] = value
            return serialized
        
        return PeriodComparison(
            period1=serialize_period(result.get("period1", {})),
            period2=serialize_period(result.get("period2", {})),
            changes=result.get("changes", {})
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
