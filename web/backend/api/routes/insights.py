"""
Insights API routes.
Provides endpoints for automated insights and anomaly detection.
"""

import sys
from pathlib import Path
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web.backend.schemas.insights import (
    InsightResponse, InsightsSummary, InsightsListResponse,
    EmergingProductInsight, PeriodComparisonRequest, PeriodComparisonResponse
)
from web.backend.api.deps import get_insights_engine_dep

router = APIRouter()


def insight_to_response(insight) -> InsightResponse:
    """Convert an Insight dataclass to response model."""
    return InsightResponse(
        type=insight.type.value,
        severity=insight.severity.value,
        title=insight.title,
        description=insight.description,
        metric_name=insight.metric_name,
        current_value=insight.current_value,
        previous_value=insight.previous_value,
        change_percent=insight.change_percent,
        period_start=str(insight.period_start),
        period_end=str(insight.period_end),
        recommendations=insight.recommendations
    )


@router.get("/weekly", response_model=InsightsListResponse)
async def get_weekly_insights(
    insights_engine=Depends(get_insights_engine_dep)
):
    """
    Get week-over-week insights.
    
    Compares the current week to the previous week and identifies
    significant changes in sentiment, resolution rate, CSAT, and topics.
    """
    try:
        insights = insights_engine.generate_weekly_insights()
        summary = insights_engine.get_insights_summary(insights)
        
        return InsightsListResponse(
            insights=[insight_to_response(i) for i in insights],
            summary=InsightsSummary(**summary)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating weekly insights: {str(e)}")


@router.get("/monthly", response_model=InsightsListResponse)
async def get_monthly_insights(
    insights_engine=Depends(get_insights_engine_dep)
):
    """
    Get month-over-month insights.
    
    Compares the current month to the previous month and identifies
    significant changes across all metrics.
    """
    try:
        insights = insights_engine.generate_monthly_insights()
        summary = insights_engine.get_insights_summary(insights)
        
        return InsightsListResponse(
            insights=[insight_to_response(i) for i in insights],
            summary=InsightsSummary(**summary)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating monthly insights: {str(e)}")


@router.get("/emerging-topics", response_model=List[EmergingProductInsight])
async def get_emerging_product_insights(
    days: int = Query(14, ge=7, le=90, description="Number of days to analyze"),
    insights_engine=Depends(get_insights_engine_dep)
):
    """
    Get emerging product area insights.
    
    Analyzes recent ticket patterns to identify product areas with
    growing issues.
    """
    try:
        emerging = insights_engine.detect_emerging_product_insights(days)
        return [EmergingProductInsight(**item) for item in emerging]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting emerging insights: {str(e)}")


@router.post("/compare", response_model=PeriodComparisonResponse)
async def compare_custom_periods(
    request: PeriodComparisonRequest,
    insights_engine=Depends(get_insights_engine_dep)
):
    """
    Compare two custom time periods.
    
    Useful for before/after analysis of releases or changes.
    """
    try:
        result = insights_engine.compare_periods(
            request.period1_start,
            request.period1_end,
            request.period2_start,
            request.period2_end
        )
        
        return PeriodComparisonResponse(
            period1=result.get("period1", {}),
            period2=result.get("period2", {}),
            metrics=result.get("metrics", {})
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing periods: {str(e)}")


@router.get("/anomalies")
async def detect_anomalies(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    insights_engine=Depends(get_insights_engine_dep)
):
    """
    Detect anomalies in the specified date range.
    
    Returns all detected anomalies sorted by severity.
    """
    try:
        from datetime import timedelta
        
        # Default to last 14 days if no dates provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=14)
        
        # Calculate comparison period (same duration before start_date)
        period_length = (end_date - start_date).days
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_length - 1)
        
        # Collect all anomalies
        all_insights = []
        
        all_insights.extend(insights_engine.detect_sentiment_anomalies(
            start_date, end_date, prev_start, prev_end
        ))
        all_insights.extend(insights_engine.detect_resolution_anomalies(
            start_date, end_date, prev_start, prev_end
        ))
        all_insights.extend(insights_engine.detect_csat_anomalies(
            start_date, end_date, prev_start, prev_end
        ))
        all_insights.extend(insights_engine.detect_topic_trends(
            start_date, end_date, prev_start, prev_end
        ))
        
        # Filter to only warning and critical
        anomalies = [
            i for i in all_insights 
            if i.severity.value in ["warning", "critical"]
        ]
        
        return {
            "anomalies": [insight_to_response(i) for i in anomalies],
            "period": {
                "start": str(start_date),
                "end": str(end_date)
            },
            "comparison_period": {
                "start": str(prev_start),
                "end": str(prev_end)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting anomalies: {str(e)}")
