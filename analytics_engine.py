#!/usr/bin/env python3
"""
Analytics Engine for AI Support Analyzer Historical Analytics

This module provides analytical functions for querying and analyzing
historical support data. It enables trend analysis, period comparisons,
and statistical insights across time.

Key Features:
- Topic distribution analysis over time
- Sentiment trend tracking
- Period-over-period comparisons
- Resolution rate calculations
- Anomaly detection helpers
"""

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from collections import defaultdict
from sqlalchemy import func, and_, or_

from models import AnalysisBatch, TicketAnalysis, TrendSnapshot, get_engine, get_session
from data_store import get_data_store


class AnalyticsEngine:
    """
    Analytics engine for historical support data analysis.
    
    Provides methods for trend analysis, comparisons, and aggregations
    that power the dashboard visualizations and insights.
    """
    
    def __init__(self, data_store=None):
        """
        Initialize the analytics engine.
        
        Args:
            data_store: Optional DataStore instance. If None, uses singleton.
        """
        self.data_store = data_store or get_data_store()
        self.engine = self.data_store.engine
    
    def _get_session(self):
        """Get a new database session."""
        return get_session(self.engine)
    
    # ==================== Topic Analysis ====================
    
    def get_topic_distribution(
        self, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Get distribution of main topics within a date range.
        
        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            top_n: Number of top topics to return
            
        Returns:
            DataFrame with columns: topic, count, percentage
        """
        session = self._get_session()
        try:
            query = session.query(
                TicketAnalysis.main_topic,
                func.count(TicketAnalysis.id).label('count')
            )
            
            if start_date:
                query = query.filter(TicketAnalysis.created_date >= start_date)
            if end_date:
                query = query.filter(TicketAnalysis.created_date <= end_date)
            
            query = query.filter(TicketAnalysis.main_topic.isnot(None))
            query = query.group_by(TicketAnalysis.main_topic)
            query = query.order_by(func.count(TicketAnalysis.id).desc())
            
            if top_n:
                query = query.limit(top_n)
            
            results = query.all()
            
            # Calculate total for percentages
            total = sum(r[1] for r in results)
            
            data = []
            for topic, count in results:
                # Handle comma-separated topics by taking the first one
                primary_topic = topic.split(',')[0].strip() if topic else 'Unknown'
                data.append({
                    'topic': primary_topic,
                    'count': count,
                    'percentage': (count / total * 100) if total > 0 else 0
                })
            
            return pd.DataFrame(data)
        finally:
            session.close()
    
    def get_topic_trend(
        self,
        topic: str,
        granularity: str = 'week',
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        Get trend of a specific topic over time.
        
        Optimized to use SQL aggregations instead of loading full DataFrame.
        
        Args:
            topic: Topic to track
            granularity: Time granularity ('day', 'week', 'month')
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            DataFrame with columns: period, count, percentage
        """
        session = self._get_session()
        try:
            from sqlalchemy import case
            
            # Build date grouping expression based on granularity
            if granularity == 'day':
                period_expr = func.date(TicketAnalysis.created_date)
            elif granularity == 'week':
                period_expr = func.strftime('%Y-%W', TicketAnalysis.created_date)
            else:  # month
                period_expr = func.strftime('%Y-%m', TicketAnalysis.created_date)
            
            # Query for topic counts and total counts per period
            topic_pattern = f'%{topic}%'
            
            query = session.query(
                period_expr.label('period'),
                func.sum(
                    case(
                        (TicketAnalysis.main_topic.like(topic_pattern), 1),
                        else_=0
                    )
                ).label('topic_count'),
                func.count(TicketAnalysis.id).label('total_count')
            )
            
            if start_date:
                query = query.filter(TicketAnalysis.created_date >= start_date)
            if end_date:
                query = query.filter(TicketAnalysis.created_date <= end_date)
            
            query = query.filter(TicketAnalysis.created_date.isnot(None))
            query = query.group_by(period_expr)
            query = query.order_by(period_expr)
            
            results = query.all()
            
            if not results:
                return pd.DataFrame(columns=['period', 'count', 'percentage'])
            
            # Convert to DataFrame
            data = []
            for period_val, topic_count, total_count in results:
                # Convert period string back to date for week/month granularity
                if granularity == 'week' and period_val:
                    try:
                        year, week = period_val.split('-')
                        # %W expects Monday as first day of week
                        period_date = datetime.strptime(f'{year}-W{week}-1', '%Y-W%W-%w').date()
                    except (ValueError, AttributeError):
                        period_date = period_val
                elif granularity == 'month' and period_val:
                    try:
                        period_date = datetime.strptime(period_val, '%Y-%m').date()
                    except (ValueError, AttributeError):
                        period_date = period_val
                else:
                    period_date = period_val
                
                data.append({
                    'period': period_date,
                    'count': topic_count or 0,
                    'percentage': (topic_count / total_count * 100) if total_count > 0 else 0
                })
            
            return pd.DataFrame(data)
        finally:
            session.close()
    
    # ==================== Sentiment Analysis ====================
    
    def get_sentiment_distribution(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get sentiment distribution within a date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary with sentiment counts and percentages
        """
        session = self._get_session()
        try:
            query = session.query(
                TicketAnalysis.sentiment,
                func.count(TicketAnalysis.id).label('count')
            )
            
            if start_date:
                query = query.filter(TicketAnalysis.created_date >= start_date)
            if end_date:
                query = query.filter(TicketAnalysis.created_date <= end_date)
            
            query = query.filter(TicketAnalysis.sentiment.isnot(None))
            query = query.group_by(TicketAnalysis.sentiment)
            
            results = dict(query.all())
            total = sum(results.values())
            
            return {
                'positive': results.get('Positive', 0),
                'neutral': results.get('Neutral', 0),
                'negative': results.get('Negative', 0),
                'total': total,
                'positive_pct': results.get('Positive', 0) / total * 100 if total > 0 else 0,
                'neutral_pct': results.get('Neutral', 0) / total * 100 if total > 0 else 0,
                'negative_pct': results.get('Negative', 0) / total * 100 if total > 0 else 0,
            }
        finally:
            session.close()
    
    def get_sentiment_trend(
        self,
        granularity: str = 'week',
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        Get sentiment trend over time.
        
        Optimized to use SQL aggregations instead of loading full DataFrame.
        
        Args:
            granularity: Time granularity ('day', 'week', 'month')
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            DataFrame with columns: period, positive, neutral, negative, 
                                   positive_pct, neutral_pct, negative_pct
        """
        session = self._get_session()
        try:
            from sqlalchemy import case
            
            # Build date grouping expression based on granularity
            if granularity == 'day':
                period_expr = func.date(TicketAnalysis.created_date)
            elif granularity == 'week':
                period_expr = func.strftime('%Y-%W', TicketAnalysis.created_date)
            else:  # month
                period_expr = func.strftime('%Y-%m', TicketAnalysis.created_date)
            
            # Query for sentiment counts per period using SQL CASE expressions
            query = session.query(
                period_expr.label('period'),
                func.sum(case((TicketAnalysis.sentiment == 'Positive', 1), else_=0)).label('positive'),
                func.sum(case((TicketAnalysis.sentiment == 'Neutral', 1), else_=0)).label('neutral'),
                func.sum(case((TicketAnalysis.sentiment == 'Negative', 1), else_=0)).label('negative'),
                func.count(TicketAnalysis.id).label('total')
            )
            
            if start_date:
                query = query.filter(TicketAnalysis.created_date >= start_date)
            if end_date:
                query = query.filter(TicketAnalysis.created_date <= end_date)
            
            query = query.filter(TicketAnalysis.created_date.isnot(None))
            query = query.group_by(period_expr)
            query = query.order_by(period_expr)
            
            results = query.all()
            
            if not results:
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = []
            for period_val, positive, neutral, negative, total in results:
                # Convert period string back to date for week/month granularity
                if granularity == 'week' and period_val:
                    try:
                        year, week = period_val.split('-')
                        period_date = datetime.strptime(f'{year}-W{week}-1', '%Y-W%W-%w').date()
                    except (ValueError, AttributeError):
                        period_date = period_val
                elif granularity == 'month' and period_val:
                    try:
                        period_date = datetime.strptime(period_val, '%Y-%m').date()
                    except (ValueError, AttributeError):
                        period_date = period_val
                else:
                    period_date = period_val
                
                total = total or 1  # Avoid division by zero
                data.append({
                    'period': period_date,
                    'positive': positive or 0,
                    'neutral': neutral or 0,
                    'negative': negative or 0,
                    'total': total,
                    'positive_pct': (positive or 0) / total * 100,
                    'neutral_pct': (neutral or 0) / total * 100,
                    'negative_pct': (negative or 0) / total * 100
                })
            
            return pd.DataFrame(data).sort_values('period')
        finally:
            session.close()
    
    # ==================== Resolution Analysis ====================
    
    def get_resolution_rate(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get issue resolution rate within a date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary with resolution statistics
        """
        session = self._get_session()
        try:
            query = session.query(TicketAnalysis)
            
            if start_date:
                query = query.filter(TicketAnalysis.created_date >= start_date)
            if end_date:
                query = query.filter(TicketAnalysis.created_date <= end_date)
            
            total = query.count()
            resolved = query.filter(TicketAnalysis.issue_resolved == True).count()
            unresolved = query.filter(TicketAnalysis.issue_resolved == False).count()
            unknown = total - resolved - unresolved
            
            return {
                'total': total,
                'resolved': resolved,
                'unresolved': unresolved,
                'unknown': unknown,
                'resolution_rate': resolved / total * 100 if total > 0 else 0
            }
        finally:
            session.close()
    
    def get_resolution_trend(
        self,
        granularity: str = 'week',
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        Get resolution rate trend over time.
        
        Optimized to use SQL aggregations instead of loading full DataFrame.
        
        Args:
            granularity: Time granularity ('day', 'week', 'month')
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            DataFrame with columns: period, resolved, unresolved, resolution_rate
        """
        session = self._get_session()
        try:
            from sqlalchemy import case
            
            # Build date grouping expression based on granularity
            if granularity == 'day':
                period_expr = func.date(TicketAnalysis.created_date)
            elif granularity == 'week':
                period_expr = func.strftime('%Y-%W', TicketAnalysis.created_date)
            else:  # month
                period_expr = func.strftime('%Y-%m', TicketAnalysis.created_date)
            
            # Query for resolution counts per period
            query = session.query(
                period_expr.label('period'),
                func.sum(case((TicketAnalysis.issue_resolved == True, 1), else_=0)).label('resolved'),
                func.count(TicketAnalysis.id).label('total')
            )
            
            if start_date:
                query = query.filter(TicketAnalysis.created_date >= start_date)
            if end_date:
                query = query.filter(TicketAnalysis.created_date <= end_date)
            
            query = query.filter(TicketAnalysis.created_date.isnot(None))
            query = query.group_by(period_expr)
            query = query.order_by(period_expr)
            
            results = query.all()
            
            if not results:
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = []
            for period_val, resolved, total in results:
                # Convert period string back to date for week/month granularity
                if granularity == 'week' and period_val:
                    try:
                        year, week = period_val.split('-')
                        period_date = datetime.strptime(f'{year}-W{week}-1', '%Y-W%W-%w').date()
                    except (ValueError, AttributeError):
                        period_date = period_val
                elif granularity == 'month' and period_val:
                    try:
                        period_date = datetime.strptime(period_val, '%Y-%m').date()
                    except (ValueError, AttributeError):
                        period_date = period_val
                else:
                    period_date = period_val
                
                resolved = resolved or 0
                total = total or 1
                unresolved = total - resolved
                
                data.append({
                    'period': period_date,
                    'resolved': resolved,
                    'total': total,
                    'unresolved': unresolved,
                    'resolution_rate': resolved / total * 100
                })
            
            return pd.DataFrame(data).sort_values('period')
        finally:
            session.close()
    
    # ==================== CSAT Analysis ====================
    
    def get_csat_distribution(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get CSAT rating distribution within a date range.
        
        Handles Zendesk CSAT values that contain 'good' or 'bad' (e.g., "Offered, Good").
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary with CSAT statistics
        """
        session = self._get_session()
        try:
            from sqlalchemy import case
            
            # Build base query with date filters
            base_query = session.query(TicketAnalysis)
            
            if start_date:
                base_query = base_query.filter(TicketAnalysis.created_date >= start_date)
            if end_date:
                base_query = base_query.filter(TicketAnalysis.created_date <= end_date)
            
            # Count total tickets
            total = base_query.count()
            
            # Count 'good' ratings (contains 'good', case-insensitive)
            good = base_query.filter(
                TicketAnalysis.csat_rating.ilike('%good%')
            ).count()
            
            # Count 'bad' ratings (contains 'bad', case-insensitive)
            bad = base_query.filter(
                TicketAnalysis.csat_rating.ilike('%bad%')
            ).count()
            
            no_rating = total - good - bad
            rated = good + bad
            
            return {
                'good': good,
                'bad': bad,
                'no_rating': no_rating,
                'total': total,
                'response_rate': rated / total * 100 if total > 0 else 0,
                'satisfaction_rate': good / rated * 100 if rated > 0 else 0
            }
        finally:
            session.close()
    
    def get_csat_trend(
        self,
        granularity: str = 'week',
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        Get CSAT trend over time.
        
        Handles Zendesk CSAT values that contain 'good' or 'bad' (e.g., "Offered, Good").
        Optimized to use SQL aggregations instead of loading full DataFrame.
        
        Args:
            granularity: Time granularity ('day', 'week', 'month')
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            DataFrame with columns: period, good, bad, satisfaction_rate
        """
        session = self._get_session()
        try:
            from sqlalchemy import case
            
            # Build date grouping expression based on granularity
            if granularity == 'day':
                period_expr = func.date(TicketAnalysis.created_date)
            elif granularity == 'week':
                period_expr = func.strftime('%Y-%W', TicketAnalysis.created_date)
            else:  # month
                period_expr = func.strftime('%Y-%m', TicketAnalysis.created_date)
            
            # Query for CSAT counts per period using case-insensitive LIKE patterns
            # This handles values like "Good", "good", "Offered, Good", etc.
            query = session.query(
                period_expr.label('period'),
                func.sum(case((TicketAnalysis.csat_rating.ilike('%good%'), 1), else_=0)).label('good'),
                func.sum(case((TicketAnalysis.csat_rating.ilike('%bad%'), 1), else_=0)).label('bad')
            )
            
            if start_date:
                query = query.filter(TicketAnalysis.created_date >= start_date)
            if end_date:
                query = query.filter(TicketAnalysis.created_date <= end_date)
            
            query = query.filter(TicketAnalysis.created_date.isnot(None))
            query = query.group_by(period_expr)
            query = query.order_by(period_expr)
            
            results = query.all()
            
            if not results:
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = []
            for period_val, good, bad in results:
                # Convert period string back to date for week/month granularity
                if granularity == 'week' and period_val:
                    try:
                        year, week = period_val.split('-')
                        period_date = datetime.strptime(f'{year}-W{week}-1', '%Y-W%W-%w').date()
                    except (ValueError, AttributeError):
                        period_date = period_val
                elif granularity == 'month' and period_val:
                    try:
                        period_date = datetime.strptime(period_val, '%Y-%m').date()
                    except (ValueError, AttributeError):
                        period_date = period_val
                else:
                    period_date = period_val
                
                good = good or 0
                bad = bad or 0
                rated = good + bad
                
                data.append({
                    'period': period_date,
                    'good': good,
                    'bad': bad,
                    'rated': rated,
                    'satisfaction_rate': good / rated * 100 if rated > 0 else 0
                })
            
            return pd.DataFrame(data).sort_values('period')
        finally:
            session.close()
    
    # ==================== Period Comparison ====================
    
    def compare_periods(
        self,
        period1_start: date,
        period1_end: date,
        period2_start: date,
        period2_end: date
    ) -> Dict[str, Any]:
        """
        Compare metrics between two time periods.
        
        Args:
            period1_start: Start of first period
            period1_end: End of first period
            period2_start: Start of second period
            period2_end: End of second period
            
        Returns:
            Dictionary with comparison metrics and percentage changes
        """
        # Get metrics for each period
        p1_sentiment = self.get_sentiment_distribution(period1_start, period1_end)
        p2_sentiment = self.get_sentiment_distribution(period2_start, period2_end)
        
        p1_resolution = self.get_resolution_rate(period1_start, period1_end)
        p2_resolution = self.get_resolution_rate(period2_start, period2_end)
        
        p1_csat = self.get_csat_distribution(period1_start, period1_end)
        p2_csat = self.get_csat_distribution(period2_start, period2_end)
        
        p1_topics = self.get_topic_distribution(period1_start, period1_end, top_n=5)
        p2_topics = self.get_topic_distribution(period2_start, period2_end, top_n=5)
        
        def pct_change(old, new):
            if old == 0:
                return 100 if new > 0 else 0
            return ((new - old) / old) * 100
        
        return {
            'period1': {
                'start': period1_start,
                'end': period1_end,
                'ticket_count': p1_sentiment['total'],
                'sentiment': p1_sentiment,
                'resolution': p1_resolution,
                'csat': p1_csat,
                'top_topics': p1_topics.to_dict('records') if not p1_topics.empty else []
            },
            'period2': {
                'start': period2_start,
                'end': period2_end,
                'ticket_count': p2_sentiment['total'],
                'sentiment': p2_sentiment,
                'resolution': p2_resolution,
                'csat': p2_csat,
                'top_topics': p2_topics.to_dict('records') if not p2_topics.empty else []
            },
            'changes': {
                'ticket_volume': pct_change(p1_sentiment['total'], p2_sentiment['total']),
                'positive_sentiment': pct_change(p1_sentiment['positive_pct'], p2_sentiment['positive_pct']),
                'negative_sentiment': pct_change(p1_sentiment['negative_pct'], p2_sentiment['negative_pct']),
                'resolution_rate': pct_change(p1_resolution['resolution_rate'], p2_resolution['resolution_rate']),
                'satisfaction_rate': pct_change(p1_csat['satisfaction_rate'], p2_csat['satisfaction_rate'])
            }
        }
    
    # ==================== Aggregation Helpers ====================
    
    def get_summary_stats(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive summary statistics for a date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary with all key metrics
        """
        sentiment = self.get_sentiment_distribution(start_date, end_date)
        resolution = self.get_resolution_rate(start_date, end_date)
        csat = self.get_csat_distribution(start_date, end_date)
        topics = self.get_topic_distribution(start_date, end_date, top_n=10)
        
        # Get product vs service related counts
        session = self._get_session()
        try:
            query = session.query(TicketAnalysis)
            
            if start_date:
                query = query.filter(TicketAnalysis.created_date >= start_date)
            if end_date:
                query = query.filter(TicketAnalysis.created_date <= end_date)
            
            product_related = query.filter(TicketAnalysis.related_to_product == True).count()
            service_related = query.filter(TicketAnalysis.related_to_service == True).count()
            ai_feedback_count = query.filter(TicketAnalysis.ai_feedback == True).count()
            
        finally:
            session.close()
        
        return {
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'ticket_count': sentiment['total'],
            'sentiment': sentiment,
            'resolution': resolution,
            'csat': csat,
            'top_topics': topics.to_dict('records') if not topics.empty else [],
            'product_related': product_related,
            'service_related': service_related,
            'ai_feedback_count': ai_feedback_count
        }


# ==================== Trend Snapshot Generation ====================

def generate_trend_snapshots(data_store, batch_id: int):
    """
    Generate trend snapshots for a specific batch.
    
    This pre-computes aggregated metrics for fast dashboard rendering.
    
    Args:
        data_store: DataStore instance
        batch_id: ID of the batch to generate snapshots for
    """
    session = get_session(data_store.engine)
    
    try:
        # Get batch info
        batch = session.query(AnalysisBatch).filter_by(id=batch_id).first()
        if not batch:
            return
        
        # Delete existing snapshots for this batch
        session.query(TrendSnapshot).filter_by(batch_id=batch_id).delete()
        
        # Get tickets for this batch
        tickets = session.query(TicketAnalysis).filter_by(batch_id=batch_id).all()
        
        if not tickets:
            session.commit()
            return
        
        # Calculate sentiment distribution
        sentiment_counts = defaultdict(int)
        for t in tickets:
            if t.sentiment:
                sentiment_counts[t.sentiment] += 1
        
        total_tickets = len(tickets)
        
        for sentiment, count in sentiment_counts.items():
            snapshot = TrendSnapshot(
                batch_id=batch_id,
                period_date=batch.period_end or batch.import_date.date(),
                metric_type='sentiment',
                metric_key=sentiment,
                metric_value=count / total_tickets * 100,
                ticket_count=count
            )
            session.add(snapshot)
        
        # Calculate topic distribution
        topic_counts = defaultdict(int)
        for t in tickets:
            if t.main_topic:
                # Take primary topic
                primary = t.main_topic.split(',')[0].strip()
                topic_counts[primary] += 1
        
        for topic, count in topic_counts.items():
            snapshot = TrendSnapshot(
                batch_id=batch_id,
                period_date=batch.period_end or batch.import_date.date(),
                metric_type='topic',
                metric_key=topic,
                metric_value=count / total_tickets * 100,
                ticket_count=count
            )
            session.add(snapshot)
        
        # Calculate resolution rate
        resolved_count = sum(1 for t in tickets if t.issue_resolved is True)
        snapshot = TrendSnapshot(
            batch_id=batch_id,
            period_date=batch.period_end or batch.import_date.date(),
            metric_type='resolution_rate',
            metric_key='resolved',
            metric_value=resolved_count / total_tickets * 100,
            ticket_count=resolved_count
        )
        session.add(snapshot)
        
        # Calculate CSAT (handles values like "Offered, Good" by checking if 'good'/'bad' is contained)
        good_count = sum(1 for t in tickets if t.csat_rating and 'good' in t.csat_rating.lower())
        bad_count = sum(1 for t in tickets if t.csat_rating and 'bad' in t.csat_rating.lower())
        rated_count = good_count + bad_count
        
        if rated_count > 0:
            snapshot = TrendSnapshot(
                batch_id=batch_id,
                period_date=batch.period_end or batch.import_date.date(),
                metric_type='csat',
                metric_key='satisfaction_rate',
                metric_value=good_count / rated_count * 100,
                ticket_count=rated_count
            )
            session.add(snapshot)
        
        session.commit()
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# Singleton analytics engine
_analytics_engine_instance: Optional[AnalyticsEngine] = None


def get_analytics_engine() -> AnalyticsEngine:
    """Get the singleton AnalyticsEngine instance."""
    global _analytics_engine_instance
    
    if _analytics_engine_instance is None:
        _analytics_engine_instance = AnalyticsEngine()
    
    return _analytics_engine_instance
