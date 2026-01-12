#!/usr/bin/env python3
"""
Product Insights Models and Data Store

This module provides data models and storage for aggregated product insights
extracted from support ticket analyses. It enables product teams to see
prioritized, actionable feedback.

Tables:
- product_insights: Aggregated insights with impact scoring
- insight_tickets: Links insights to source tickets
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
import json

from sqlalchemy import (
    Column, Integer, String, Text, Float, Date, DateTime,
    ForeignKey, Index, Table, Enum as SQLEnum, func
)
from sqlalchemy.orm import relationship, Session, joinedload
import pandas as pd

from models import Base, TicketAnalysis


class InsightType(str, Enum):
    """Types of product insights."""
    FEATURE_REQUEST = "feature_request"
    PAIN_POINT = "pain_point"
    IMPROVEMENT = "improvement"
    BUG = "bug"
    PRAISE = "praise"


class InsightStatus(str, Enum):
    """Status of a product insight."""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


# Predefined product areas for categorization
PRODUCT_AREAS = [
    "Domains",
    "Email",
    "Themes",
    "Plugins",
    "Billing",
    "Plans",
    "Editor",
    "Media",
    "SEO",
    "Security",
    "Performance",
    "Migration",
    "Support",
    "Account",
    "AI Features",
    "Mobile",
    "Other"
]


# Association table for many-to-many relationship
insight_tickets = Table(
    'insight_tickets',
    Base.metadata,
    Column('insight_id', Integer, ForeignKey('product_insights.id'), primary_key=True),
    Column('ticket_id', Integer, ForeignKey('ticket_analyses.id'), primary_key=True),
    Column('relevance_score', Float, default=1.0),  # How relevant this ticket is to the insight
    Column('linked_at', DateTime, default=datetime.utcnow)
)


class ProductInsight(Base):
    """
    Represents an aggregated product insight extracted from multiple tickets.
    
    Insights are created by clustering similar feedback from tickets and
    calculating an impact score for prioritization.
    """
    __tablename__ = 'product_insights'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Classification
    insight_type = Column(String(50), nullable=False, default=InsightType.PAIN_POINT.value)
    product_area = Column(String(100), nullable=False, default="Other")
    
    # Content
    title = Column(String(300), nullable=False)  # AI-generated summary
    description = Column(Text, nullable=True)     # Detailed explanation
    keywords = Column(Text, nullable=True)        # JSON array of related keywords
    
    # Metrics
    ticket_count = Column(Integer, default=0)     # Number of tickets mentioning this
    impact_score = Column(Float, default=0.0)     # Calculated priority score
    
    # Sentiment breakdown (percentages)
    positive_pct = Column(Float, default=0.0)
    neutral_pct = Column(Float, default=0.0)
    negative_pct = Column(Float, default=0.0)
    
    # Resolution metrics
    resolved_pct = Column(Float, default=0.0)     # % of related tickets resolved
    
    # Temporal tracking
    first_seen = Column(Date, nullable=True)      # Earliest ticket date
    last_seen = Column(Date, nullable=True)       # Most recent ticket date
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Trend data
    trend_direction = Column(String(20), default="stable")  # 'increasing', 'decreasing', 'stable'
    trend_pct = Column(Float, default=0.0)        # Week-over-week change percentage
    
    # Status tracking
    status = Column(String(50), default=InsightStatus.NEW.value)
    status_updated_at = Column(DateTime, nullable=True)
    status_notes = Column(Text, nullable=True)
    
    # Relationship to source tickets
    tickets = relationship(
        "TicketAnalysis",
        secondary=insight_tickets,
        backref="insights"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_insight_type', 'insight_type'),
        Index('idx_insight_product_area', 'product_area'),
        Index('idx_insight_impact', 'impact_score'),
        Index('idx_insight_status', 'status'),
        Index('idx_insight_last_seen', 'last_seen'),
    )
    
    def __repr__(self):
        return f"<ProductInsight(id={self.id}, type='{self.insight_type}', title='{self.title[:50]}...', impact={self.impact_score:.1f})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert insight to dictionary for export."""
        return {
            'id': self.id,
            'type': self.insight_type,
            'product_area': self.product_area,
            'title': self.title,
            'description': self.description,
            'ticket_count': self.ticket_count,
            'impact_score': self.impact_score,
            'sentiment': {
                'positive': self.positive_pct,
                'neutral': self.neutral_pct,
                'negative': self.negative_pct
            },
            'resolved_pct': self.resolved_pct,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'trend': {
                'direction': self.trend_direction,
                'change_pct': self.trend_pct
            },
            'status': self.status,
            'keywords': json.loads(self.keywords) if self.keywords else []
        }
    
    def calculate_impact_score(self) -> float:
        """
        Calculate the impact score for prioritization.
        
        Formula:
        - Base: ticket_count * 10
        - Sentiment weight: negative_pct * 0.5
        - Resolution penalty: (100 - resolved_pct) * 0.3
        - Recency boost: Higher if last_seen is recent
        - Status decay: Lower if already resolved
        """
        base_score = self.ticket_count * 10
        
        # Negative sentiment increases priority
        sentiment_weight = self.negative_pct * 0.5
        
        # Unresolved issues are more important
        resolution_penalty = (100 - self.resolved_pct) * 0.3
        
        # Recency boost (0-20 points based on how recent)
        recency_boost = 0
        if self.last_seen:
            days_ago = (date.today() - self.last_seen).days
            if days_ago <= 7:
                recency_boost = 20
            elif days_ago <= 30:
                recency_boost = 10
            elif days_ago <= 90:
                recency_boost = 5
        
        # Status decay
        status_decay = 0
        if self.status == InsightStatus.RESOLVED.value:
            status_decay = 50
        elif self.status == InsightStatus.WONT_FIX.value:
            status_decay = 40
        elif self.status == InsightStatus.IN_PROGRESS.value:
            status_decay = 10
        
        self.impact_score = max(0, base_score + sentiment_weight + resolution_penalty + recency_boost - status_decay)
        return self.impact_score


class ProductInsightsStore:
    """
    Data store for managing product insights.
    
    Provides methods for creating, querying, and updating insights.
    """
    
    def __init__(self, session_factory):
        """
        Initialize the store.
        
        Args:
            session_factory: SQLAlchemy session factory (from data_store)
        """
        self.Session = session_factory
    
    def _get_session(self) -> Session:
        """Get a new database session."""
        return self.Session()
    
    def create_insight(
        self,
        title: str,
        insight_type: InsightType,
        product_area: str,
        description: str = None,
        keywords: List[str] = None
    ) -> ProductInsight:
        """
        Create a new product insight.
        
        Args:
            title: AI-generated summary title
            insight_type: Type of insight
            product_area: Product area category
            description: Detailed explanation
            keywords: Related keywords for matching
            
        Returns:
            Created ProductInsight instance
        """
        session = self._get_session()
        try:
            insight = ProductInsight(
                title=title,
                insight_type=insight_type.value if isinstance(insight_type, InsightType) else insight_type,
                product_area=product_area,
                description=description,
                keywords=json.dumps(keywords) if keywords else None
            )
            session.add(insight)
            session.commit()
            session.refresh(insight)
            return insight
        finally:
            session.close()
    
    def link_tickets_to_insight(
        self,
        insight_id: int,
        ticket_ids: List[int],
        recalculate: bool = True
    ) -> ProductInsight:
        """
        Link tickets to an insight and recalculate metrics.
        
        Args:
            insight_id: ID of the insight
            ticket_ids: List of ticket IDs to link
            recalculate: Whether to recalculate metrics
            
        Returns:
            Updated ProductInsight instance
        """
        session = self._get_session()
        try:
            insight = session.query(ProductInsight).get(insight_id)
            if not insight:
                raise ValueError(f"Insight {insight_id} not found")
            
            # Get tickets
            tickets = session.query(TicketAnalysis).filter(
                TicketAnalysis.id.in_(ticket_ids)
            ).all()
            
            # Link tickets
            for ticket in tickets:
                if ticket not in insight.tickets:
                    insight.tickets.append(ticket)
            
            if recalculate:
                self._recalculate_insight_metrics(insight, session)
            
            session.commit()
            session.refresh(insight)
            return insight
        finally:
            session.close()
    
    def _recalculate_insight_metrics(self, insight: ProductInsight, session: Session):
        """Recalculate all metrics for an insight based on linked tickets."""
        tickets = insight.tickets
        
        if not tickets:
            insight.ticket_count = 0
            return
        
        insight.ticket_count = len(tickets)
        
        # Sentiment breakdown
        sentiments = {'Positive': 0, 'Neutral': 0, 'Negative': 0}
        resolved_count = 0
        dates = []
        
        for ticket in tickets:
            if ticket.sentiment in sentiments:
                sentiments[ticket.sentiment] += 1
            if ticket.issue_resolved:
                resolved_count += 1
            if ticket.created_date:
                dates.append(ticket.created_date)
        
        total = len(tickets)
        insight.positive_pct = (sentiments['Positive'] / total * 100) if total else 0
        insight.neutral_pct = (sentiments['Neutral'] / total * 100) if total else 0
        insight.negative_pct = (sentiments['Negative'] / total * 100) if total else 0
        insight.resolved_pct = (resolved_count / total * 100) if total else 0
        
        if dates:
            insight.first_seen = min(dates)
            insight.last_seen = max(dates)
        
        # Calculate impact score
        insight.calculate_impact_score()
    
    def get_insights(
        self,
        insight_type: InsightType = None,
        product_area: str = None,
        status: InsightStatus = None,
        min_impact: float = None,
        order_by: str = 'impact_score',
        limit: int = 50
    ) -> List[ProductInsight]:
        """
        Query insights with filters.
        
        Args:
            insight_type: Filter by type
            product_area: Filter by product area
            status: Filter by status
            min_impact: Minimum impact score
            order_by: Field to order by
            limit: Maximum number of results
            
        Returns:
            List of ProductInsight instances
        """
        session = self._get_session()
        try:
            query = session.query(ProductInsight)
            
            if insight_type:
                type_value = insight_type.value if isinstance(insight_type, InsightType) else insight_type
                query = query.filter(ProductInsight.insight_type == type_value)
            
            if product_area:
                query = query.filter(ProductInsight.product_area == product_area)
            
            if status:
                status_value = status.value if isinstance(status, InsightStatus) else status
                query = query.filter(ProductInsight.status == status_value)
            
            if min_impact is not None:
                query = query.filter(ProductInsight.impact_score >= min_impact)
            
            # Ordering
            if order_by == 'impact_score':
                query = query.order_by(ProductInsight.impact_score.desc())
            elif order_by == 'ticket_count':
                query = query.order_by(ProductInsight.ticket_count.desc())
            elif order_by == 'last_seen':
                query = query.order_by(ProductInsight.last_seen.desc())
            elif order_by == 'created_at':
                query = query.order_by(ProductInsight.created_at.desc())
            
            if limit:
                query = query.limit(limit)
            
            insights = query.all()
            
            # Detach from session so they can be used after session closes
            for insight in insights:
                session.expunge(insight)
            
            return insights
        finally:
            session.close()
    
    def get_insight_by_id(self, insight_id: int) -> Optional[ProductInsight]:
        """Get a single insight by ID with eagerly loaded tickets."""
        session = self._get_session()
        try:
            insight = session.query(ProductInsight).options(
                joinedload(ProductInsight.tickets)
            ).filter(ProductInsight.id == insight_id).first()
            
            # Detach from session so it can be used after session closes
            if insight:
                session.expunge(insight)
                # Also expunge tickets to avoid DetachedInstanceError
                for ticket in insight.tickets:
                    session.expunge(ticket)
            
            return insight
        finally:
            session.close()
    
    def update_insight_status(
        self,
        insight_id: int,
        status: InsightStatus,
        notes: str = None
    ) -> ProductInsight:
        """
        Update the status of an insight.
        
        Args:
            insight_id: ID of the insight
            status: New status
            notes: Optional notes about the status change
            
        Returns:
            Updated ProductInsight instance
        """
        session = self._get_session()
        try:
            insight = session.query(ProductInsight).get(insight_id)
            if not insight:
                raise ValueError(f"Insight {insight_id} not found")
            
            insight.status = status.value if isinstance(status, InsightStatus) else status
            insight.status_updated_at = datetime.utcnow()
            if notes:
                insight.status_notes = notes
            
            # Recalculate impact score (status affects it)
            insight.calculate_impact_score()
            
            session.commit()
            session.refresh(insight)
            return insight
        finally:
            session.close()
    
    def get_insights_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about all insights.
        
        Returns:
            Dictionary with summary stats
        """
        session = self._get_session()
        try:
            total = session.query(func.count(ProductInsight.id)).scalar() or 0
            
            # By type
            by_type = dict(
                session.query(
                    ProductInsight.insight_type,
                    func.count(ProductInsight.id)
                ).group_by(ProductInsight.insight_type).all()
            )
            
            # By product area
            by_area = dict(
                session.query(
                    ProductInsight.product_area,
                    func.count(ProductInsight.id)
                ).group_by(ProductInsight.product_area).all()
            )
            
            # By status
            by_status = dict(
                session.query(
                    ProductInsight.status,
                    func.count(ProductInsight.id)
                ).group_by(ProductInsight.status).all()
            )
            
            # Top insights by impact
            top_insights = session.query(ProductInsight).order_by(
                ProductInsight.impact_score.desc()
            ).limit(5).all()
            
            return {
                'total_insights': total,
                'by_type': by_type,
                'by_product_area': by_area,
                'by_status': by_status,
                'top_insights': [i.to_dict() for i in top_insights]
            }
        finally:
            session.close()
    
    def get_insights_dataframe(
        self,
        insight_type: InsightType = None,
        product_area: str = None
    ) -> pd.DataFrame:
        """
        Get insights as a pandas DataFrame.
        
        Args:
            insight_type: Optional filter by type
            product_area: Optional filter by area
            
        Returns:
            DataFrame with insight data
        """
        insights = self.get_insights(
            insight_type=insight_type,
            product_area=product_area,
            limit=None
        )
        
        if not insights:
            return pd.DataFrame()
        
        data = [i.to_dict() for i in insights]
        df = pd.DataFrame(data)
        
        # Flatten nested dicts
        if 'sentiment' in df.columns:
            df['positive_pct'] = df['sentiment'].apply(lambda x: x.get('positive', 0) if x else 0)
            df['neutral_pct'] = df['sentiment'].apply(lambda x: x.get('neutral', 0) if x else 0)
            df['negative_pct'] = df['sentiment'].apply(lambda x: x.get('negative', 0) if x else 0)
            df = df.drop(columns=['sentiment'])
        
        if 'trend' in df.columns:
            df['trend_direction'] = df['trend'].apply(lambda x: x.get('direction', 'stable') if x else 'stable')
            df['trend_change_pct'] = df['trend'].apply(lambda x: x.get('change_pct', 0) if x else 0)
            df = df.drop(columns=['trend'])
        
        return df


# Singleton instance getter
_insights_store = None

def get_insights_store() -> ProductInsightsStore:
    """Get the global ProductInsightsStore instance."""
    global _insights_store
    if _insights_store is None:
        from data_store import get_data_store
        from sqlalchemy.orm import sessionmaker
        ds = get_data_store()
        # Create a session factory bound to the same engine
        Session = sessionmaker(bind=ds.engine)
        _insights_store = ProductInsightsStore(Session)
    return _insights_store
