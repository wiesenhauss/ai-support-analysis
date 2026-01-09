#!/usr/bin/env python3
"""
Database Models for AI Support Analyzer Historical Analytics

This module defines the SQLAlchemy ORM models for storing and querying
historical support analysis data.

Tables:
- analysis_batches: Metadata about each CSV import
- ticket_analyses: Individual ticket analysis results
- trend_snapshots: Pre-computed aggregations for fast trending
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean, 
    Float, Date, DateTime, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class AnalysisBatch(Base):
    """
    Represents a single CSV import/analysis session.
    
    Each time a user imports analyzed data, a new batch is created
    to track the source and metadata.
    """
    __tablename__ = 'analysis_batches'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    import_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    source_file = Column(String(500), nullable=False)
    period_start = Column(Date, nullable=True)  # Earliest ticket date in batch
    period_end = Column(Date, nullable=True)    # Latest ticket date in batch
    total_tickets = Column(Integer, default=0)
    new_tickets = Column(Integer, default=0)    # Tickets not seen before
    duplicate_tickets = Column(Integer, default=0)  # Tickets already in DB
    notes = Column(Text, nullable=True)
    
    # Relationship to tickets
    tickets = relationship("TicketAnalysis", back_populates="batch", cascade="all, delete-orphan")
    # Relationship to trend snapshots
    snapshots = relationship("TrendSnapshot", back_populates="batch", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AnalysisBatch(id={self.id}, file='{self.source_file}', tickets={self.total_tickets})>"


class TicketAnalysis(Base):
    """
    Stores the analysis results for an individual support ticket.
    
    Denormalized for query performance - contains all analysis fields
    directly rather than in separate related tables.
    """
    __tablename__ = 'ticket_analyses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey('analysis_batches.id'), nullable=False)
    
    # Ticket identification
    ticket_id = Column(String(100), nullable=True)  # Zendesk ticket ID or URL
    ticket_hash = Column(String(64), nullable=False)  # SHA256 hash for deduplication
    
    # Temporal data
    created_date = Column(Date, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow)
    
    # CSAT data
    csat_rating = Column(String(20), nullable=True)  # 'good', 'bad', or null
    csat_reason = Column(Text, nullable=True)
    csat_comment = Column(Text, nullable=True)
    
    # AI Analysis results
    sentiment = Column(String(20), nullable=True)  # 'Positive', 'Neutral', 'Negative'
    issue_resolved = Column(Boolean, nullable=True)
    main_topic = Column(String(200), nullable=True)
    interaction_topics = Column(Text, nullable=True)  # Comma-separated list
    customer_goal = Column(Text, nullable=True)
    detail_summary = Column(Text, nullable=True)
    what_happened = Column(Text, nullable=True)
    product_feedback = Column(Text, nullable=True)
    related_to_product = Column(Boolean, nullable=True)
    related_to_service = Column(Boolean, nullable=True)
    ai_feedback = Column(Boolean, nullable=True)
    
    # Predictive CSAT (if available)
    predicted_csat = Column(String(20), nullable=True)
    prediction_confidence = Column(Float, nullable=True)
    
    # Relationship to batch
    batch = relationship("AnalysisBatch", back_populates="tickets")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_ticket_hash', 'ticket_hash'),
        Index('idx_created_date', 'created_date'),
        Index('idx_sentiment', 'sentiment'),
        Index('idx_main_topic', 'main_topic'),
        Index('idx_csat_rating', 'csat_rating'),
        UniqueConstraint('ticket_hash', name='uq_ticket_hash'),
    )
    
    def __repr__(self):
        return f"<TicketAnalysis(id={self.id}, topic='{self.main_topic}', sentiment='{self.sentiment}')>"


class TrendSnapshot(Base):
    """
    Pre-computed aggregations for fast trend queries.
    
    Stores metrics like topic distribution, sentiment breakdown, etc.
    aggregated at the batch level for efficient historical analysis.
    """
    __tablename__ = 'trend_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey('analysis_batches.id'), nullable=False)
    
    # Time period this snapshot represents
    period_date = Column(Date, nullable=False)
    period_granularity = Column(String(20), default='batch')  # 'daily', 'weekly', 'monthly', 'batch'
    
    # Metric identification
    metric_type = Column(String(50), nullable=False)  # 'topic', 'sentiment', 'resolution_rate', etc.
    metric_key = Column(String(200), nullable=True)   # Specific value (e.g., topic name, 'Positive')
    
    # Metric values
    metric_value = Column(Float, nullable=True)       # Percentage or rate
    ticket_count = Column(Integer, default=0)         # Absolute count
    
    # Relationship to batch
    batch = relationship("AnalysisBatch", back_populates="snapshots")
    
    # Indexes for trend queries
    __table_args__ = (
        Index('idx_period_date', 'period_date'),
        Index('idx_metric_type', 'metric_type'),
        Index('idx_metric_type_key', 'metric_type', 'metric_key'),
    )
    
    def __repr__(self):
        return f"<TrendSnapshot(type='{self.metric_type}', key='{self.metric_key}', value={self.metric_value})>"


# Utility function to create all tables
def create_tables(engine):
    """Create all database tables."""
    Base.metadata.create_all(engine)


def get_engine(db_path: str = "support_analytics.db"):
    """
    Create and return a SQLAlchemy engine.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        SQLAlchemy engine instance
    """
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session(engine):
    """
    Create and return a new database session.
    
    Args:
        engine: SQLAlchemy engine instance
        
    Returns:
        SQLAlchemy session instance
    """
    Session = sessionmaker(bind=engine)
    return Session()
