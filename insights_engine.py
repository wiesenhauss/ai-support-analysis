#!/usr/bin/env python3
"""
Insights Engine for AI Support Analyzer Historical Analytics

This module provides automated insight generation and anomaly detection
for historical support data. It identifies significant changes, emerging
topics, and generates actionable insights.

Key Features:
- Anomaly detection for sentiment, resolution rate, CSAT
- Emerging topic identification
- Week-over-week and month-over-month comparisons
- AI-powered insight summarization
"""

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Try to import analytics modules
try:
    from data_store import get_data_store, DataStore
    from analytics_engine import get_analytics_engine, AnalyticsEngine
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False


class InsightType(Enum):
    """Types of insights that can be generated."""
    SENTIMENT_CHANGE = "sentiment_change"
    RESOLUTION_CHANGE = "resolution_change"
    CSAT_CHANGE = "csat_change"
    EMERGING_TOPIC = "emerging_topic"
    DECLINING_TOPIC = "declining_topic"
    VOLUME_SPIKE = "volume_spike"
    AI_FEEDBACK_TREND = "ai_feedback_trend"
    PRODUCT_VS_SERVICE = "product_vs_service"


class InsightSeverity(Enum):
    """Severity levels for insights."""
    INFO = "info"       # Informational, no action needed
    WARNING = "warning"  # Worth monitoring
    CRITICAL = "critical"  # Requires attention


@dataclass
class Insight:
    """Represents a single insight or anomaly."""
    type: InsightType
    severity: InsightSeverity
    title: str
    description: str
    metric_name: str
    current_value: float
    previous_value: float
    change_percent: float
    period_start: date
    period_end: date
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert insight to dictionary."""
        return {
            'type': self.type.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'metric_name': self.metric_name,
            'current_value': self.current_value,
            'previous_value': self.previous_value,
            'change_percent': self.change_percent,
            'period_start': str(self.period_start),
            'period_end': str(self.period_end),
            'recommendations': self.recommendations
        }


class InsightsEngine:
    """
    Engine for generating automated insights and detecting anomalies.
    
    Analyzes historical data to identify significant changes and
    generate actionable recommendations.
    """
    
    # Thresholds for anomaly detection
    THRESHOLDS = {
        'sentiment_change_warning': 5.0,    # 5% change triggers warning
        'sentiment_change_critical': 10.0,  # 10% change triggers critical
        'resolution_change_warning': 5.0,
        'resolution_change_critical': 10.0,
        'csat_change_warning': 5.0,
        'csat_change_critical': 10.0,
        'volume_spike_warning': 25.0,       # 25% volume increase
        'volume_spike_critical': 50.0,      # 50% volume increase
        'emerging_topic_threshold': 3.0,    # 3% increase in topic share
        'declining_topic_threshold': -3.0,  # 3% decrease in topic share
    }
    
    def __init__(self, analytics_engine: Optional[AnalyticsEngine] = None):
        """
        Initialize the insights engine.
        
        Args:
            analytics_engine: Optional AnalyticsEngine instance. If None, uses singleton.
        """
        self.analytics_engine = analytics_engine or get_analytics_engine()
    
    def _calculate_change(self, current: float, previous: float) -> float:
        """Calculate percentage change between two values."""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - previous) / previous) * 100
    
    def _get_severity(self, change: float, warning_threshold: float, critical_threshold: float) -> InsightSeverity:
        """Determine severity based on change magnitude."""
        abs_change = abs(change)
        if abs_change >= critical_threshold:
            return InsightSeverity.CRITICAL
        elif abs_change >= warning_threshold:
            return InsightSeverity.WARNING
        return InsightSeverity.INFO
    
    def detect_sentiment_anomalies(
        self,
        current_start: date,
        current_end: date,
        previous_start: date,
        previous_end: date
    ) -> List[Insight]:
        """
        Detect significant changes in sentiment distribution.
        
        Args:
            current_start: Start of current period
            current_end: End of current period
            previous_start: Start of comparison period
            previous_end: End of comparison period
            
        Returns:
            List of sentiment-related insights
        """
        insights = []
        
        current = self.analytics_engine.get_sentiment_distribution(current_start, current_end)
        previous = self.analytics_engine.get_sentiment_distribution(previous_start, previous_end)
        
        if current['total'] == 0 or previous['total'] == 0:
            return insights
        
        # Check negative sentiment change
        neg_change = self._calculate_change(current['negative_pct'], previous['negative_pct'])
        if abs(neg_change) >= self.THRESHOLDS['sentiment_change_warning']:
            severity = self._get_severity(
                neg_change,
                self.THRESHOLDS['sentiment_change_warning'],
                self.THRESHOLDS['sentiment_change_critical']
            )
            
            direction = "increased" if neg_change > 0 else "decreased"
            insights.append(Insight(
                type=InsightType.SENTIMENT_CHANGE,
                severity=severity,
                title=f"Negative Sentiment {direction.title()}",
                description=f"Negative sentiment has {direction} by {abs(neg_change):.1f}% compared to the previous period.",
                metric_name="Negative Sentiment %",
                current_value=current['negative_pct'],
                previous_value=previous['negative_pct'],
                change_percent=neg_change,
                period_start=current_start,
                period_end=current_end,
                recommendations=self._get_sentiment_recommendations(neg_change, current)
            ))
        
        # Check positive sentiment change
        pos_change = self._calculate_change(current['positive_pct'], previous['positive_pct'])
        if abs(pos_change) >= self.THRESHOLDS['sentiment_change_warning']:
            severity = self._get_severity(
                -pos_change,  # Negative change in positive sentiment is bad
                self.THRESHOLDS['sentiment_change_warning'],
                self.THRESHOLDS['sentiment_change_critical']
            )
            
            direction = "increased" if pos_change > 0 else "decreased"
            insights.append(Insight(
                type=InsightType.SENTIMENT_CHANGE,
                severity=severity if pos_change < 0 else InsightSeverity.INFO,
                title=f"Positive Sentiment {direction.title()}",
                description=f"Positive sentiment has {direction} by {abs(pos_change):.1f}% compared to the previous period.",
                metric_name="Positive Sentiment %",
                current_value=current['positive_pct'],
                previous_value=previous['positive_pct'],
                change_percent=pos_change,
                period_start=current_start,
                period_end=current_end,
                recommendations=[] if pos_change > 0 else self._get_sentiment_recommendations(-pos_change, current)
            ))
        
        return insights
    
    def _get_sentiment_recommendations(self, change: float, current_data: Dict) -> List[str]:
        """Generate recommendations based on sentiment changes."""
        recommendations = []
        
        if change > 0:  # Negative sentiment increased
            recommendations.append("Review recent tickets with negative sentiment to identify common issues")
            recommendations.append("Check if there are product-related problems causing frustration")
            
            if current_data.get('negative_pct', 0) > 30:
                recommendations.append("Consider escalating to product team for immediate attention")
        else:  # Negative sentiment decreased (good)
            recommendations.append("Document successful practices that led to improvement")
        
        return recommendations
    
    def detect_resolution_anomalies(
        self,
        current_start: date,
        current_end: date,
        previous_start: date,
        previous_end: date
    ) -> List[Insight]:
        """Detect significant changes in issue resolution rate."""
        insights = []
        
        current = self.analytics_engine.get_resolution_rate(current_start, current_end)
        previous = self.analytics_engine.get_resolution_rate(previous_start, previous_end)
        
        if current['total'] == 0 or previous['total'] == 0:
            return insights
        
        change = self._calculate_change(
            current['resolution_rate'],
            previous['resolution_rate']
        )
        
        if abs(change) >= self.THRESHOLDS['resolution_change_warning']:
            severity = self._get_severity(
                -change,  # Decrease in resolution is bad
                self.THRESHOLDS['resolution_change_warning'],
                self.THRESHOLDS['resolution_change_critical']
            )
            
            direction = "improved" if change > 0 else "declined"
            insights.append(Insight(
                type=InsightType.RESOLUTION_CHANGE,
                severity=severity if change < 0 else InsightSeverity.INFO,
                title=f"Resolution Rate {direction.title()}",
                description=f"Issue resolution rate has {direction} by {abs(change):.1f}%.",
                metric_name="Resolution Rate %",
                current_value=current['resolution_rate'],
                previous_value=previous['resolution_rate'],
                change_percent=change,
                period_start=current_start,
                period_end=current_end,
                recommendations=self._get_resolution_recommendations(change, current)
            ))
        
        return insights
    
    def _get_resolution_recommendations(self, change: float, current_data: Dict) -> List[str]:
        """Generate recommendations based on resolution rate changes."""
        recommendations = []
        
        if change < 0:  # Resolution rate decreased
            recommendations.append("Analyze unresolved tickets to identify common blockers")
            recommendations.append("Review agent training needs for problematic issue types")
            
            if current_data.get('resolution_rate', 0) < 60:
                recommendations.append("Consider process improvements for complex ticket handling")
        else:
            recommendations.append("Continue current practices that are driving improvements")
        
        return recommendations
    
    def detect_csat_anomalies(
        self,
        current_start: date,
        current_end: date,
        previous_start: date,
        previous_end: date
    ) -> List[Insight]:
        """Detect significant changes in CSAT satisfaction rate."""
        insights = []
        
        current = self.analytics_engine.get_csat_distribution(current_start, current_end)
        previous = self.analytics_engine.get_csat_distribution(previous_start, previous_end)
        
        if (current['good'] + current['bad']) == 0 or (previous['good'] + previous['bad']) == 0:
            return insights
        
        change = self._calculate_change(
            current['satisfaction_rate'],
            previous['satisfaction_rate']
        )
        
        if abs(change) >= self.THRESHOLDS['csat_change_warning']:
            severity = self._get_severity(
                -change,  # Decrease in satisfaction is bad
                self.THRESHOLDS['csat_change_warning'],
                self.THRESHOLDS['csat_change_critical']
            )
            
            direction = "improved" if change > 0 else "declined"
            insights.append(Insight(
                type=InsightType.CSAT_CHANGE,
                severity=severity if change < 0 else InsightSeverity.INFO,
                title=f"Customer Satisfaction {direction.title()}",
                description=f"CSAT satisfaction rate has {direction} by {abs(change):.1f}%.",
                metric_name="CSAT Satisfaction Rate %",
                current_value=current['satisfaction_rate'],
                previous_value=previous['satisfaction_rate'],
                change_percent=change,
                period_start=current_start,
                period_end=current_end,
                recommendations=self._get_csat_recommendations(change, current)
            ))
        
        return insights
    
    def _get_csat_recommendations(self, change: float, current_data: Dict) -> List[str]:
        """Generate recommendations based on CSAT changes."""
        recommendations = []
        
        if change < 0:
            recommendations.append("Review recent bad CSAT comments to understand customer pain points")
            recommendations.append("Consider follow-up surveys to gather more detailed feedback")
            
            if current_data.get('satisfaction_rate', 0) < 70:
                recommendations.append("Immediate attention needed: satisfaction below target threshold")
        else:
            recommendations.append("Share positive feedback with team to reinforce good practices")
        
        return recommendations
    
    def detect_topic_trends(
        self,
        current_start: date,
        current_end: date,
        previous_start: date,
        previous_end: date
    ) -> List[Insight]:
        """Detect emerging and declining topics."""
        insights = []
        
        current_topics = self.analytics_engine.get_topic_distribution(current_start, current_end, top_n=20)
        previous_topics = self.analytics_engine.get_topic_distribution(previous_start, previous_end, top_n=20)
        
        if current_topics.empty or previous_topics.empty:
            return insights
        
        # Create dictionaries for comparison
        current_dict = dict(zip(current_topics['topic'], current_topics['percentage']))
        previous_dict = dict(zip(previous_topics['topic'], previous_topics['percentage']))
        
        # Find emerging topics (significantly higher in current period)
        for topic, current_pct in current_dict.items():
            previous_pct = previous_dict.get(topic, 0)
            change = current_pct - previous_pct
            
            if change >= self.THRESHOLDS['emerging_topic_threshold']:
                insights.append(Insight(
                    type=InsightType.EMERGING_TOPIC,
                    severity=InsightSeverity.WARNING if change > 5 else InsightSeverity.INFO,
                    title=f"Emerging Topic: {topic}",
                    description=f"'{topic}' has increased by {change:.1f} percentage points.",
                    metric_name=f"Topic Share: {topic}",
                    current_value=current_pct,
                    previous_value=previous_pct,
                    change_percent=change,
                    period_start=current_start,
                    period_end=current_end,
                    recommendations=[
                        f"Investigate why '{topic}' issues are increasing",
                        "Consider creating documentation or FAQs for this topic",
                        "Check if there are product changes related to this area"
                    ]
                ))
            
            elif change <= self.THRESHOLDS['declining_topic_threshold']:
                insights.append(Insight(
                    type=InsightType.DECLINING_TOPIC,
                    severity=InsightSeverity.INFO,
                    title=f"Declining Topic: {topic}",
                    description=f"'{topic}' has decreased by {abs(change):.1f} percentage points.",
                    metric_name=f"Topic Share: {topic}",
                    current_value=current_pct,
                    previous_value=previous_pct,
                    change_percent=change,
                    period_start=current_start,
                    period_end=current_end,
                    recommendations=[
                        f"Document what led to reduction in '{topic}' issues",
                        "Apply similar strategies to other problem areas"
                    ]
                ))
        
        return insights
    
    def generate_weekly_insights(self) -> List[Insight]:
        """
        Generate insights comparing current week to previous week.
        
        Returns:
            List of insights for week-over-week comparison
        """
        today = date.today()
        current_end = today
        current_start = today - timedelta(days=7)
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=6)
        
        all_insights = []
        
        all_insights.extend(self.detect_sentiment_anomalies(
            current_start, current_end, previous_start, previous_end
        ))
        all_insights.extend(self.detect_resolution_anomalies(
            current_start, current_end, previous_start, previous_end
        ))
        all_insights.extend(self.detect_csat_anomalies(
            current_start, current_end, previous_start, previous_end
        ))
        all_insights.extend(self.detect_topic_trends(
            current_start, current_end, previous_start, previous_end
        ))
        
        # Sort by severity (critical first)
        severity_order = {
            InsightSeverity.CRITICAL: 0,
            InsightSeverity.WARNING: 1,
            InsightSeverity.INFO: 2
        }
        all_insights.sort(key=lambda x: severity_order[x.severity])
        
        return all_insights
    
    def generate_monthly_insights(self) -> List[Insight]:
        """
        Generate insights comparing current month to previous month.
        
        Returns:
            List of insights for month-over-month comparison
        """
        today = date.today()
        current_end = today
        current_start = today - timedelta(days=30)
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=29)
        
        all_insights = []
        
        all_insights.extend(self.detect_sentiment_anomalies(
            current_start, current_end, previous_start, previous_end
        ))
        all_insights.extend(self.detect_resolution_anomalies(
            current_start, current_end, previous_start, previous_end
        ))
        all_insights.extend(self.detect_csat_anomalies(
            current_start, current_end, previous_start, previous_end
        ))
        all_insights.extend(self.detect_topic_trends(
            current_start, current_end, previous_start, previous_end
        ))
        
        # Sort by severity
        severity_order = {
            InsightSeverity.CRITICAL: 0,
            InsightSeverity.WARNING: 1,
            InsightSeverity.INFO: 2
        }
        all_insights.sort(key=lambda x: severity_order[x.severity])
        
        return all_insights
    
    def compare_periods(
        self,
        period1_start: date,
        period1_end: date,
        period2_start: date,
        period2_end: date
    ) -> Dict[str, Any]:
        """
        Compare two time periods across all metrics.
        
        Useful for before/after analysis of releases or changes.
        
        Args:
            period1_start: Start of first period (usually "before")
            period1_end: End of first period
            period2_start: Start of second period (usually "after")
            period2_end: End of second period
            
        Returns:
            Dictionary with comparison data for each metric
        """
        comparison = {
            'period1': {'start': str(period1_start), 'end': str(period1_end)},
            'period2': {'start': str(period2_start), 'end': str(period2_end)},
            'metrics': {}
        }
        
        # Sentiment comparison
        sent1 = self.analytics_engine.get_sentiment_distribution(period1_start, period1_end)
        sent2 = self.analytics_engine.get_sentiment_distribution(period2_start, period2_end)
        
        comparison['metrics']['sentiment'] = {
            'period1': sent1,
            'period2': sent2,
            'changes': {
                'positive': self._calculate_change(sent2['positive_pct'], sent1['positive_pct']),
                'neutral': self._calculate_change(sent2['neutral_pct'], sent1['neutral_pct']),
                'negative': self._calculate_change(sent2['negative_pct'], sent1['negative_pct'])
            }
        }
        
        # Resolution comparison
        res1 = self.analytics_engine.get_resolution_rate(period1_start, period1_end)
        res2 = self.analytics_engine.get_resolution_rate(period2_start, period2_end)
        
        comparison['metrics']['resolution'] = {
            'period1': res1,
            'period2': res2,
            'change': self._calculate_change(res2['resolution_rate'], res1['resolution_rate'])
        }
        
        # CSAT comparison
        csat1 = self.analytics_engine.get_csat_distribution(period1_start, period1_end)
        csat2 = self.analytics_engine.get_csat_distribution(period2_start, period2_end)
        
        comparison['metrics']['csat'] = {
            'period1': csat1,
            'period2': csat2,
            'change': self._calculate_change(csat2['satisfaction_rate'], csat1['satisfaction_rate'])
        }
        
        # Topic comparison
        topics1 = self.analytics_engine.get_topic_distribution(period1_start, period1_end, top_n=10)
        topics2 = self.analytics_engine.get_topic_distribution(period2_start, period2_end, top_n=10)
        
        topics1_dict = dict(zip(topics1['topic'], topics1['percentage'])) if not topics1.empty else {}
        topics2_dict = dict(zip(topics2['topic'], topics2['percentage'])) if not topics2.empty else {}
        
        all_topics = set(topics1_dict.keys()) | set(topics2_dict.keys())
        topic_changes = {}
        for topic in all_topics:
            p1_val = topics1_dict.get(topic, 0)
            p2_val = topics2_dict.get(topic, 0)
            topic_changes[topic] = {
                'period1': p1_val,
                'period2': p2_val,
                'change': p2_val - p1_val
            }
        
        # Sort by absolute change
        sorted_topics = sorted(topic_changes.items(), key=lambda x: abs(x[1]['change']), reverse=True)
        comparison['metrics']['topics'] = dict(sorted_topics[:10])
        
        # Volume comparison
        comparison['metrics']['volume'] = {
            'period1': sent1.get('total', 0),
            'period2': sent2.get('total', 0),
            'change': self._calculate_change(sent2.get('total', 0), sent1.get('total', 0))
        }
        
        return comparison
    
    def detect_emerging_product_insights(
        self,
        days: int = 14
    ) -> List[Dict[str, Any]]:
        """
        Detect emerging product insights based on recent ticket patterns.
        
        Analyzes product_area and pain_points to identify growing issues.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            List of emerging insights with impact scores
        """
        from data_store import get_data_store
        
        end_date = date.today()
        mid_date = end_date - timedelta(days=days//2)
        start_date = end_date - timedelta(days=days)
        
        data_store = get_data_store()
        
        # Get tickets from both periods
        session = data_store._get_session()
        try:
            from models import TicketAnalysis
            from sqlalchemy import func
            
            # Product area distribution - recent vs earlier
            recent_areas = session.query(
                TicketAnalysis.product_area,
                func.count(TicketAnalysis.id).label('count')
            ).filter(
                TicketAnalysis.created_date >= mid_date,
                TicketAnalysis.created_date <= end_date,
                TicketAnalysis.product_area.isnot(None)
            ).group_by(TicketAnalysis.product_area).all()
            
            earlier_areas = session.query(
                TicketAnalysis.product_area,
                func.count(TicketAnalysis.id).label('count')
            ).filter(
                TicketAnalysis.created_date >= start_date,
                TicketAnalysis.created_date < mid_date,
                TicketAnalysis.product_area.isnot(None)
            ).group_by(TicketAnalysis.product_area).all()
            
            recent_dict = {area: count for area, count in recent_areas}
            earlier_dict = {area: count for area, count in earlier_areas}
            
            recent_total = sum(recent_dict.values()) or 1
            earlier_total = sum(earlier_dict.values()) or 1
            
            emerging = []
            for area in set(recent_dict.keys()) | set(earlier_dict.keys()):
                recent_pct = (recent_dict.get(area, 0) / recent_total) * 100
                earlier_pct = (earlier_dict.get(area, 0) / earlier_total) * 100
                change = recent_pct - earlier_pct
                
                if change > 2:  # At least 2% increase
                    # Get negative sentiment rate for this area recently
                    neg_count = session.query(func.count(TicketAnalysis.id)).filter(
                        TicketAnalysis.created_date >= mid_date,
                        TicketAnalysis.product_area == area,
                        TicketAnalysis.sentiment == 'Negative'
                    ).scalar() or 0
                    
                    total_area = recent_dict.get(area, 1)
                    neg_pct = (neg_count / total_area) * 100 if total_area > 0 else 0
                    
                    emerging.append({
                        'product_area': area,
                        'growth_pct': change,
                        'ticket_count': recent_dict.get(area, 0),
                        'negative_pct': neg_pct,
                        'impact_score': change * 10 + neg_pct * 0.5
                    })
            
            # Sort by impact score
            emerging.sort(key=lambda x: x['impact_score'], reverse=True)
            return emerging[:10]
            
        finally:
            session.close()
    
    def get_insights_summary(self, insights: List[Insight]) -> Dict[str, Any]:
        """
        Generate a summary of insights.
        
        Args:
            insights: List of Insight objects
            
        Returns:
            Dictionary with summary statistics
        """
        if not insights:
            return {
                'total': 0,
                'critical': 0,
                'warning': 0,
                'info': 0,
                'top_concerns': [],
                'positive_trends': []
            }
        
        critical = [i for i in insights if i.severity == InsightSeverity.CRITICAL]
        warning = [i for i in insights if i.severity == InsightSeverity.WARNING]
        info = [i for i in insights if i.severity == InsightSeverity.INFO]
        
        # Identify top concerns (critical + warning with negative impact)
        top_concerns = [
            {'title': i.title, 'severity': i.severity.value, 'change': i.change_percent}
            for i in insights
            if i.severity in [InsightSeverity.CRITICAL, InsightSeverity.WARNING]
            and i.change_percent != 0
        ][:5]
        
        # Identify positive trends
        positive_trends = [
            {'title': i.title, 'change': i.change_percent}
            for i in insights
            if (i.type in [InsightType.DECLINING_TOPIC] or 
                (i.type == InsightType.SENTIMENT_CHANGE and i.metric_name == "Positive Sentiment %" and i.change_percent > 0) or
                (i.type == InsightType.RESOLUTION_CHANGE and i.change_percent > 0) or
                (i.type == InsightType.CSAT_CHANGE and i.change_percent > 0))
        ][:5]
        
        return {
            'total': len(insights),
            'critical': len(critical),
            'warning': len(warning),
            'info': len(info),
            'top_concerns': top_concerns,
            'positive_trends': positive_trends
        }


# Singleton instance
_insights_engine_instance: Optional[InsightsEngine] = None


def get_insights_engine() -> InsightsEngine:
    """Get the singleton InsightsEngine instance."""
    global _insights_engine_instance
    
    if _insights_engine_instance is None:
        _insights_engine_instance = InsightsEngine()
    
    return _insights_engine_instance
