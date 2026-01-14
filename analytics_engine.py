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
import threading
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from collections import defaultdict
from sqlalchemy import func, and_, or_, case

from models import AnalysisBatch, TicketAnalysis, TrendSnapshot, get_engine
from data_store import get_data_store


class QueryCache:
    """
    Thread-safe TTL cache for database query results.
    
    Provides in-memory caching with automatic expiration to reduce
    database load for frequently accessed data.
    """
    
    def __init__(self, ttl_seconds: int = 60):
        """
        Initialize the query cache.
        
        Args:
            ttl_seconds: Time-to-live in seconds for cached values (default: 60)
        """
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a cached value if it exists and hasn't expired.
        
        Args:
            key: Cache key to look up
            
        Returns:
            Cached value if valid, None otherwise
        """
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if datetime.now() - timestamp < self._ttl:
                    return value
                # Expired, remove it
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Store a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            self._cache[key] = (value, datetime.now())
    
    def invalidate(self, pattern: Optional[str] = None) -> None:
        """
        Invalidate cached entries.
        
        Args:
            pattern: If provided, only invalidate keys containing this pattern.
                    If None, clear the entire cache.
        """
        with self._lock:
            if pattern:
                self._cache = {k: v for k, v in self._cache.items() if pattern not in k}
            else:
                self._cache.clear()
    
    def _make_key(self, method_name: str, *args, **kwargs) -> str:
        """
        Generate a cache key from method name and arguments.
        
        Args:
            method_name: Name of the method being cached
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            String cache key
        """
        parts = [method_name]
        parts.extend(str(arg) for arg in args)
        parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return ":".join(parts)


class AnalyticsEngine:
    """
    Analytics engine for historical support data analysis.
    
    Provides methods for trend analysis, comparisons, and aggregations
    that power the dashboard visualizations and insights.
    
    Features:
    - Query caching with TTL for improved performance
    - Optimized aggregation queries
    - Thread-safe operations
    """
    
    def __init__(self, data_store=None, cache_ttl: int = 60):
        """
        Initialize the analytics engine.
        
        Args:
            data_store: Optional DataStore instance. If None, uses singleton.
            cache_ttl: Cache time-to-live in seconds (default: 60)
        """
        self.data_store = data_store or get_data_store()
        self.engine = self.data_store.engine
        self._cache = QueryCache(ttl_seconds=cache_ttl)
    
    def _get_session(self):
        """Get a thread-local database session from the data store."""
        return self.data_store._get_session()
    
    def invalidate_cache(self, pattern: Optional[str] = None) -> None:
        """
        Invalidate the query cache.
        
        Call this after data imports or modifications to ensure
        fresh data is returned.
        
        Args:
            pattern: If provided, only invalidate keys containing this pattern
        """
        self._cache.invalidate(pattern)
    
    # ==================== Topic Analysis ====================
    
    def get_topic_distribution(
        self, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Get distribution of main topics within a date range.
        
        Results are cached for improved performance on repeated calls.
        
        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            top_n: Number of top topics to return
            
        Returns:
            DataFrame with columns: topic, count, percentage
        """
        # Check cache first
        cache_key = self._cache._make_key('topic_distribution', start_date, end_date, top_n=top_n)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
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
            
            result = pd.DataFrame(data)
            self._cache.set(cache_key, result)
            return result
        finally:
            pass  # Session managed by scoped_session
    
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
        
        Results are cached for improved performance on repeated calls.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary with sentiment counts and percentages
        """
        # Check cache first
        cache_key = self._cache._make_key('sentiment_distribution', start_date, end_date)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
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
            
            result = {
                'positive': results.get('Positive', 0),
                'neutral': results.get('Neutral', 0),
                'negative': results.get('Negative', 0),
                'total': total,
                'positive_pct': results.get('Positive', 0) / total * 100 if total > 0 else 0,
                'neutral_pct': results.get('Neutral', 0) / total * 100 if total > 0 else 0,
                'negative_pct': results.get('Negative', 0) / total * 100 if total > 0 else 0,
            }
            self._cache.set(cache_key, result)
            return result
        finally:
            pass  # Session managed by scoped_session
    
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
        
        Results are cached for improved performance on repeated calls.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary with resolution statistics
        """
        # Check cache first
        cache_key = self._cache._make_key('resolution_rate', start_date, end_date)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
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
            
            result = {
                'total': total,
                'resolved': resolved,
                'unresolved': unresolved,
                'unknown': unknown,
                'resolution_rate': resolved / total * 100 if total > 0 else 0
            }
            self._cache.set(cache_key, result)
            return result
        finally:
            pass  # Session managed by scoped_session
    
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
        
        Results are cached for improved performance on repeated calls.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary with CSAT statistics
        """
        # Check cache first
        cache_key = self._cache._make_key('csat_distribution', start_date, end_date)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        session = self._get_session()
        try:
            query = session.query(
                TicketAnalysis.csat_rating,
                func.count(TicketAnalysis.id).label('count')
            )
            
            if start_date:
                query = query.filter(TicketAnalysis.created_date >= start_date)
            if end_date:
                query = query.filter(TicketAnalysis.created_date <= end_date)
            
            query = query.group_by(TicketAnalysis.csat_rating)
            
            results = dict(query.all())
            
            good = results.get('good', 0) + results.get('Good', 0)
            bad = results.get('bad', 0) + results.get('Bad', 0)
            no_rating = sum(v for k, v in results.items() if k not in ['good', 'Good', 'bad', 'Bad'])
            total = good + bad + no_rating
            rated = good + bad
            
            result = {
                'good': good,
                'bad': bad,
                'no_rating': no_rating,
                'total': total,
                'response_rate': rated / total * 100 if total > 0 else 0,
                'satisfaction_rate': good / rated * 100 if rated > 0 else 0
            }
            self._cache.set(cache_key, result)
            return result
        finally:
            pass  # Session managed by scoped_session
    
    def get_csat_trend(
        self,
        granularity: str = 'week',
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        Get CSAT trend over time.
        
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
            # Build date grouping expression based on granularity
            if granularity == 'day':
                period_expr = func.date(TicketAnalysis.created_date)
            elif granularity == 'week':
                period_expr = func.strftime('%Y-%W', TicketAnalysis.created_date)
            else:  # month
                period_expr = func.strftime('%Y-%m', TicketAnalysis.created_date)
            
            # Normalize csat_rating to lowercase for comparison
            csat_lower = func.lower(TicketAnalysis.csat_rating)
            
            # Query for CSAT counts per period
            query = session.query(
                period_expr.label('period'),
                func.sum(case((csat_lower == 'good', 1), else_=0)).label('good'),
                func.sum(case((csat_lower == 'bad', 1), else_=0)).label('bad')
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
        
        OPTIMIZED: Combines multiple queries into a single database call
        for much faster performance. Reduces ~7 queries to 1 query.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary with all key metrics
        """
        session = self._get_session()
        try:
            # Normalize csat_rating to lowercase for comparison
            csat_lower = func.lower(TicketAnalysis.csat_rating)
            
            # Single optimized query with all aggregations
            query = session.query(
                # Total count
                func.count(TicketAnalysis.id).label('total'),
                # Sentiment counts
                func.sum(case((TicketAnalysis.sentiment == 'Positive', 1), else_=0)).label('positive'),
                func.sum(case((TicketAnalysis.sentiment == 'Neutral', 1), else_=0)).label('neutral'),
                func.sum(case((TicketAnalysis.sentiment == 'Negative', 1), else_=0)).label('negative'),
                # Sentiment with non-null values for percentage calculation
                func.sum(case((TicketAnalysis.sentiment.isnot(None), 1), else_=0)).label('sentiment_total'),
                # Resolution counts
                func.sum(case((TicketAnalysis.issue_resolved == True, 1), else_=0)).label('resolved'),
                func.sum(case((TicketAnalysis.issue_resolved == False, 1), else_=0)).label('unresolved'),
                # CSAT counts
                func.sum(case((csat_lower == 'good', 1), else_=0)).label('csat_good'),
                func.sum(case((csat_lower == 'bad', 1), else_=0)).label('csat_bad'),
                # Related counts
                func.sum(case((TicketAnalysis.related_to_product == True, 1), else_=0)).label('product_related'),
                func.sum(case((TicketAnalysis.related_to_service == True, 1), else_=0)).label('service_related'),
                func.sum(case((TicketAnalysis.ai_feedback == True, 1), else_=0)).label('ai_feedback'),
            )
            
            if start_date:
                query = query.filter(TicketAnalysis.created_date >= start_date)
            if end_date:
                query = query.filter(TicketAnalysis.created_date <= end_date)
            
            result = query.first()
            
            # Extract values with defaults
            total = result.total or 0
            positive = result.positive or 0
            neutral = result.neutral or 0
            negative = result.negative or 0
            sentiment_total = result.sentiment_total or 0
            resolved = result.resolved or 0
            unresolved = result.unresolved or 0
            csat_good = result.csat_good or 0
            csat_bad = result.csat_bad or 0
            product_related = result.product_related or 0
            service_related = result.service_related or 0
            ai_feedback_count = result.ai_feedback or 0
            
            # Calculate derived values
            csat_rated = csat_good + csat_bad
            csat_no_rating = total - csat_rated
            resolution_unknown = total - resolved - unresolved
            
            # Build response matching the original format
            sentiment_data = {
                'positive': positive,
                'neutral': neutral,
                'negative': negative,
                'total': sentiment_total,
                'positive_pct': (positive / sentiment_total * 100) if sentiment_total > 0 else 0,
                'neutral_pct': (neutral / sentiment_total * 100) if sentiment_total > 0 else 0,
                'negative_pct': (negative / sentiment_total * 100) if sentiment_total > 0 else 0,
            }
            
            resolution_data = {
                'total': total,
                'resolved': resolved,
                'unresolved': unresolved,
                'unknown': resolution_unknown,
                'resolution_rate': (resolved / total * 100) if total > 0 else 0
            }
            
            csat_data = {
                'good': csat_good,
                'bad': csat_bad,
                'no_rating': csat_no_rating,
                'total': total,
                'response_rate': (csat_rated / total * 100) if total > 0 else 0,
                'satisfaction_rate': (csat_good / csat_rated * 100) if csat_rated > 0 else 0
            }
            
        finally:
            pass  # Session managed by scoped_session
        
        # Get topic distribution (still needs separate query for GROUP BY)
        topics = self.get_topic_distribution(start_date, end_date, top_n=10)
        
        return {
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'ticket_count': total,
            'sentiment': sentiment_data,
            'resolution': resolution_data,
            'csat': csat_data,
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
    session = data_store._get_session()
    
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
        
        # Calculate CSAT
        good_count = sum(1 for t in tickets if t.csat_rating and t.csat_rating.lower() == 'good')
        bad_count = sum(1 for t in tickets if t.csat_rating and t.csat_rating.lower() == 'bad')
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
