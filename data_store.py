#!/usr/bin/env python3
"""
Data Store Module for AI Support Analyzer Historical Analytics

This module provides the interface for storing and retrieving analysis data
from the SQLite database. It handles CSV imports, deduplication, and
provides query methods for historical analysis.

Key Features:
- Import analyzed CSVs into SQLite with automatic deduplication
- Query historical data across time periods
- Generate trend snapshots for fast dashboard rendering
"""

import os
import hashlib
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from models import (
    Base, AnalysisBatch, TicketAnalysis, TrendSnapshot,
    create_tables, get_engine, get_session
)


class DataStore:
    """
    Main interface for historical data storage and retrieval.
    
    Provides methods for importing CSV data, querying historical analyses,
    and managing the database.
    """
    
    # Default database location in user's app data directory
    DEFAULT_DB_PATH = os.path.join(
        os.path.expanduser("~"), 
        ".ai_support_analyzer", 
        "analytics.db"
    )
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the data store.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self.engine = get_engine(self.db_path)
        create_tables(self.engine)
        
        # Run migrations for new columns
        self._run_migrations()
        
    def _run_migrations(self):
        """
        Run database migrations to add new columns.
        
        This handles adding columns that were added to the model after
        the database was originally created.
        """
        from sqlalchemy import text, inspect
        
        inspector = inspect(self.engine)
        
        # Get existing columns in ticket_analyses table
        if 'ticket_analyses' in inspector.get_table_names():
            existing_columns = {col['name'] for col in inspector.get_columns('ticket_analyses')}
            
            # Columns to add if missing (column_name, column_type, default)
            migrations = [
                ('product_area', 'VARCHAR(100)', None),
                ('feature_requests', 'TEXT', None),
                ('pain_points', 'TEXT', None),
            ]
            
            with self.engine.connect() as conn:
                for col_name, col_type, default in migrations:
                    if col_name not in existing_columns:
                        default_clause = f" DEFAULT {default}" if default else ""
                        sql = f"ALTER TABLE ticket_analyses ADD COLUMN {col_name} {col_type}{default_clause}"
                        try:
                            conn.execute(text(sql))
                            conn.commit()
                            print(f"Migration: Added column '{col_name}' to ticket_analyses")
                        except Exception as e:
                            # Column might already exist or other error
                            print(f"Migration note: {col_name} - {e}")
        
        # Also check product_insights table
        if 'product_insights' not in inspector.get_table_names():
            # Import and create the ProductInsight table
            try:
                from product_insights import ProductInsight, insight_tickets
                ProductInsight.__table__.create(self.engine, checkfirst=True)
                insight_tickets.create(self.engine, checkfirst=True)
                print("Migration: Created product_insights and insight_tickets tables")
            except Exception as e:
                print(f"Migration note: product_insights - {e}")
        
    def _get_session(self):
        """Get a new database session."""
        return get_session(self.engine)
    
    def _compute_ticket_hash(self, row: pd.Series) -> str:
        """
        Compute a unique hash for a ticket based on its content.
        
        Uses multiple fields to create a stable identifier that will
        detect duplicate tickets across imports.
        
        Args:
            row: Pandas Series containing ticket data
            
        Returns:
            SHA256 hash string
        """
        # Combine key fields for hashing
        hash_fields = []
        
        # Priority: Use Zendesk URL if available (most reliable identifier)
        for col in ['Zendesk Ticket URL', 'zendesk_ticket_url', 'Ticket URL']:
            if col in row.index and pd.notna(row.get(col)):
                hash_fields.append(str(row[col]))
                break
        
        # Fallback: Use combination of date + summary + customer goal
        if not hash_fields:
            for col in ['Created Date', 'created_date', 'CREATED_DATE']:
                if col in row.index and pd.notna(row.get(col)):
                    hash_fields.append(str(row[col]))
                    break
            
            for col in ['DETAIL_SUMMARY', 'detail_summary']:
                if col in row.index and pd.notna(row.get(col)):
                    # Use first 200 chars of summary
                    hash_fields.append(str(row[col])[:200])
                    break
            
            for col in ['CUSTOMER_GOAL', 'customer_goal']:
                if col in row.index and pd.notna(row.get(col)):
                    hash_fields.append(str(row[col]))
                    break
        
        # Create hash
        content = "|".join(hash_fields)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _find_column(self, df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """Find a column by checking multiple possible names."""
        for name in possible_names:
            # Exact match
            if name in df.columns:
                return name
            # Case-insensitive match
            for col in df.columns:
                if col.lower() == name.lower():
                    return col
        return None
    
    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse a date value from various formats."""
        if pd.isna(value):
            return None
        
        if isinstance(value, (datetime, date)):
            return value.date() if isinstance(value, datetime) else value
        
        # Convert to string and clean
        str_value = str(value).strip()
        if not str_value or str_value.lower() in ['nan', 'none', 'nat']:
            return None
        
        # Try pandas to_datetime first (handles many formats)
        try:
            parsed = pd.to_datetime(str_value, errors='coerce')
            if pd.notna(parsed):
                return parsed.date()
        except Exception:
            pass
        
        # Try common date formats manually
        formats = [
            '%m/%d/%y',           # 10/31/25 (2-digit year) - MOST COMMON IN YOUR DATA
            '%m/%d/%Y',           # 10/31/2025 (4-digit year)
            '%m/%d/%y %H:%M:%S',  # With time
            '%m/%d/%Y %H:%M:%S',
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%d/%m/%Y',
            '%d/%m/%Y %H:%M:%S',
            '%b %d, %Y',
            '%B %d, %Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(str_value[:26], fmt).date()
            except ValueError:
                continue
        
        return None
    
    def _parse_boolean(self, value: Any) -> Optional[bool]:
        """Parse a boolean value from various formats."""
        if pd.isna(value):
            return None
        
        if isinstance(value, bool):
            return value
        
        str_val = str(value).lower().strip()
        if str_val in ['true', 'yes', '1', 't']:
            return True
        elif str_val in ['false', 'no', '0', 'f']:
            return False
        
        return None
    
    def import_csv(self, csv_path: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Import an analyzed CSV file into the database.
        
        Handles deduplication by checking ticket hashes against existing records.
        
        Args:
            csv_path: Path to the CSV file to import
            notes: Optional notes about this import
            
        Returns:
            Dictionary with import statistics:
            - batch_id: ID of the created batch
            - total_rows: Total rows in CSV
            - imported: Number of new tickets imported
            - duplicates: Number of duplicate tickets skipped
            - period_start: Earliest ticket date
            - period_end: Latest ticket date
        """
        # Read CSV
        df = pd.read_csv(csv_path)
        
        session = self._get_session()
        
        try:
            # Create batch record
            batch = AnalysisBatch(
                source_file=os.path.basename(csv_path),
                notes=notes
            )
            session.add(batch)
            session.flush()  # Get batch ID
            
            # Get existing ticket hashes for deduplication
            existing_hashes = set(
                row[0] for row in 
                session.query(TicketAnalysis.ticket_hash).all()
            )
            
            # Column mappings (CSV column name -> model field)
            column_map = {
                'ticket_id': ['Zendesk Ticket URL', 'Ticket ID', 'ticket_id'],
                'created_date': ['Created Date', 'created_date', 'CREATED_DATE'],
                'csat_rating': ['CSAT Rating', 'csat_rating'],
                'csat_reason': ['CSAT Reason', 'csat_reason'],
                'csat_comment': ['CSAT Comment', 'csat_comment'],
                'sentiment': ['SENTIMENT_ANALYSIS', 'sentiment_analysis', 'Sentiment'],
                'issue_resolved': ['ISSUE_RESOLVED', 'issue_resolved'],
                'main_topic': ['MAIN_TOPIC', 'main_topic'],
                'interaction_topics': ['INTERACTION_TOPICS', 'interaction_topics'],
                'customer_goal': ['CUSTOMER_GOAL', 'customer_goal'],
                'detail_summary': ['DETAIL_SUMMARY', 'detail_summary'],
                'what_happened': ['WHAT_HAPPENED', 'what_happened'],
                'product_feedback': ['PRODUCT_FEEDBACK', 'product_feedback'],
                'related_to_product': ['RELATED_TO_PRODUCT', 'related_to_product'],
                'related_to_service': ['RELATED_TO_SERVICE', 'related_to_service'],
                'ai_feedback': ['AI_FEEDBACK', 'ai_feedback'],
                'predicted_csat': ['PREDICTED_CSAT', 'predicted_csat'],
                'prediction_confidence': ['PREDICTION_CONFIDENCE', 'prediction_confidence'],
                # Product insights fields
                'product_area': ['PRODUCT_AREA', 'product_area'],
                'feature_requests': ['FEATURE_REQUESTS', 'feature_requests'],
                'pain_points': ['PAIN_POINTS', 'pain_points'],
            }
            
            # Resolve column names
            resolved_columns = {}
            for field, possible_names in column_map.items():
                resolved_columns[field] = self._find_column(df, possible_names)
            
            # Process rows
            imported_count = 0
            duplicate_count = 0
            dates = []
            
            for idx, row in df.iterrows():
                # Compute hash for deduplication
                ticket_hash = self._compute_ticket_hash(row)
                
                if ticket_hash in existing_hashes:
                    duplicate_count += 1
                    continue
                
                # Create ticket analysis record
                ticket = TicketAnalysis(
                    batch_id=batch.id,
                    ticket_hash=ticket_hash
                )
                
                # Populate fields from CSV
                if resolved_columns['ticket_id']:
                    ticket.ticket_id = str(row.get(resolved_columns['ticket_id'], ''))[:100]
                
                if resolved_columns['created_date']:
                    ticket.created_date = self._parse_date(row.get(resolved_columns['created_date']))
                    if ticket.created_date:
                        dates.append(ticket.created_date)
                
                if resolved_columns['csat_rating']:
                    ticket.csat_rating = str(row.get(resolved_columns['csat_rating'], ''))[:20] or None
                
                if resolved_columns['csat_reason']:
                    val = row.get(resolved_columns['csat_reason'])
                    ticket.csat_reason = str(val) if pd.notna(val) else None
                
                if resolved_columns['csat_comment']:
                    val = row.get(resolved_columns['csat_comment'])
                    ticket.csat_comment = str(val) if pd.notna(val) else None
                
                if resolved_columns['sentiment']:
                    val = row.get(resolved_columns['sentiment'])
                    ticket.sentiment = str(val)[:20] if pd.notna(val) else None
                
                if resolved_columns['issue_resolved']:
                    ticket.issue_resolved = self._parse_boolean(row.get(resolved_columns['issue_resolved']))
                
                if resolved_columns['main_topic']:
                    val = row.get(resolved_columns['main_topic'])
                    ticket.main_topic = str(val)[:200] if pd.notna(val) else None
                
                if resolved_columns['interaction_topics']:
                    val = row.get(resolved_columns['interaction_topics'])
                    ticket.interaction_topics = str(val) if pd.notna(val) else None
                
                if resolved_columns['customer_goal']:
                    val = row.get(resolved_columns['customer_goal'])
                    ticket.customer_goal = str(val) if pd.notna(val) else None
                
                if resolved_columns['detail_summary']:
                    val = row.get(resolved_columns['detail_summary'])
                    ticket.detail_summary = str(val) if pd.notna(val) else None
                
                if resolved_columns['what_happened']:
                    val = row.get(resolved_columns['what_happened'])
                    ticket.what_happened = str(val) if pd.notna(val) else None
                
                if resolved_columns['product_feedback']:
                    val = row.get(resolved_columns['product_feedback'])
                    ticket.product_feedback = str(val) if pd.notna(val) else None
                
                if resolved_columns['related_to_product']:
                    ticket.related_to_product = self._parse_boolean(row.get(resolved_columns['related_to_product']))
                
                if resolved_columns['related_to_service']:
                    ticket.related_to_service = self._parse_boolean(row.get(resolved_columns['related_to_service']))
                
                if resolved_columns['ai_feedback']:
                    ticket.ai_feedback = self._parse_boolean(row.get(resolved_columns['ai_feedback']))
                
                if resolved_columns['predicted_csat']:
                    val = row.get(resolved_columns['predicted_csat'])
                    ticket.predicted_csat = str(val)[:20] if pd.notna(val) else None
                
                if resolved_columns['prediction_confidence']:
                    val = row.get(resolved_columns['prediction_confidence'])
                    if pd.notna(val):
                        try:
                            ticket.prediction_confidence = float(val)
                        except (ValueError, TypeError):
                            pass
                
                # Product insights fields
                if resolved_columns['product_area']:
                    val = row.get(resolved_columns['product_area'])
                    ticket.product_area = str(val)[:100] if pd.notna(val) else None
                
                if resolved_columns['feature_requests']:
                    val = row.get(resolved_columns['feature_requests'])
                    ticket.feature_requests = str(val) if pd.notna(val) else None
                
                if resolved_columns['pain_points']:
                    val = row.get(resolved_columns['pain_points'])
                    ticket.pain_points = str(val) if pd.notna(val) else None
                
                session.add(ticket)
                existing_hashes.add(ticket_hash)  # Prevent duplicates within same import
                imported_count += 1
            
            # Update batch metadata
            batch.total_tickets = len(df)
            batch.new_tickets = imported_count
            batch.duplicate_tickets = duplicate_count
            
            if dates:
                batch.period_start = min(dates)
                batch.period_end = max(dates)
            
            session.commit()
            
            # Generate trend snapshots for this batch
            try:
                from analytics_engine import generate_trend_snapshots
                generate_trend_snapshots(self, batch.id)
            except ImportError:
                pass  # Analytics engine not available
            
            return {
                'batch_id': batch.id,
                'total_rows': len(df),
                'imported': imported_count,
                'duplicates': duplicate_count,
                'period_start': batch.period_start,
                'period_end': batch.period_end
            }
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_all_batches(self) -> List[Dict[str, Any]]:
        """
        Get all import batches.
        
        Returns:
            List of batch dictionaries with metadata
        """
        session = self._get_session()
        try:
            batches = session.query(AnalysisBatch).order_by(
                AnalysisBatch.import_date.desc()
            ).all()
            
            return [
                {
                    'id': b.id,
                    'import_date': b.import_date,
                    'source_file': b.source_file,
                    'period_start': b.period_start,
                    'period_end': b.period_end,
                    'total_tickets': b.total_tickets,
                    'new_tickets': b.new_tickets,
                    'notes': b.notes
                }
                for b in batches
            ]
        finally:
            session.close()
    
    def get_total_tickets(self) -> int:
        """Get total number of unique tickets in database."""
        session = self._get_session()
        try:
            return session.query(TicketAnalysis).count()
        finally:
            session.close()
    
    def get_date_range(self) -> Tuple[Optional[date], Optional[date]]:
        """Get the date range of all tickets in database."""
        session = self._get_session()
        try:
            from sqlalchemy import func
            result = session.query(
                func.min(TicketAnalysis.created_date),
                func.max(TicketAnalysis.created_date)
            ).first()
            return result[0], result[1]
        finally:
            session.close()
    
    def get_tickets_dataframe(
        self, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get tickets as a pandas DataFrame for analysis.
        
        Args:
            start_date: Filter tickets from this date
            end_date: Filter tickets until this date
            limit: Maximum number of tickets to return
            
        Returns:
            DataFrame with ticket analysis data
        """
        session = self._get_session()
        try:
            query = session.query(TicketAnalysis)
            
            if start_date:
                query = query.filter(TicketAnalysis.created_date >= start_date)
            if end_date:
                query = query.filter(TicketAnalysis.created_date <= end_date)
            
            query = query.order_by(TicketAnalysis.created_date.desc())
            
            if limit:
                query = query.limit(limit)
            
            tickets = query.all()
            
            # Convert to DataFrame
            data = []
            for t in tickets:
                data.append({
                    'id': t.id,
                    'batch_id': t.batch_id,
                    'ticket_id': t.ticket_id,
                    'created_date': t.created_date,
                    'csat_rating': t.csat_rating,
                    'sentiment': t.sentiment,
                    'issue_resolved': t.issue_resolved,
                    'main_topic': t.main_topic,
                    'interaction_topics': t.interaction_topics,
                    'customer_goal': t.customer_goal,
                    'detail_summary': t.detail_summary,
                    'what_happened': t.what_happened,
                    'product_feedback': t.product_feedback,
                    'related_to_product': t.related_to_product,
                    'related_to_service': t.related_to_service,
                    'ai_feedback': t.ai_feedback,
                    'predicted_csat': t.predicted_csat,
                    'prediction_confidence': t.prediction_confidence,
                })
            
            return pd.DataFrame(data)
        finally:
            session.close()
    
    def delete_batch(self, batch_id: int) -> bool:
        """
        Delete a batch and all its associated tickets.
        
        Args:
            batch_id: ID of the batch to delete
            
        Returns:
            True if deleted, False if not found
        """
        session = self._get_session()
        try:
            batch = session.query(AnalysisBatch).filter_by(id=batch_id).first()
            if batch:
                session.delete(batch)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get overall database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        session = self._get_session()
        try:
            from sqlalchemy import func
            
            total_tickets = session.query(TicketAnalysis).count()
            total_batches = session.query(AnalysisBatch).count()
            
            date_range = session.query(
                func.min(TicketAnalysis.created_date),
                func.max(TicketAnalysis.created_date)
            ).first()
            
            # Sentiment distribution
            sentiment_counts = dict(
                session.query(
                    TicketAnalysis.sentiment,
                    func.count(TicketAnalysis.id)
                ).group_by(TicketAnalysis.sentiment).all()
            )
            
            # Resolution rate
            resolved = session.query(TicketAnalysis).filter(
                TicketAnalysis.issue_resolved == True
            ).count()
            
            return {
                'total_tickets': total_tickets,
                'total_batches': total_batches,
                'date_range_start': date_range[0],
                'date_range_end': date_range[1],
                'sentiment_distribution': sentiment_counts,
                'resolution_rate': resolved / total_tickets if total_tickets > 0 else 0,
                'db_path': self.db_path,
                'db_size_mb': os.path.getsize(self.db_path) / (1024 * 1024) if os.path.exists(self.db_path) else 0
            }
        finally:
            session.close()


# Singleton instance for easy access
_data_store_instance: Optional[DataStore] = None


def get_data_store(db_path: Optional[str] = None) -> DataStore:
    """
    Get the singleton DataStore instance.
    
    Args:
        db_path: Optional custom database path (only used on first call)
        
    Returns:
        DataStore instance
    """
    global _data_store_instance
    
    if _data_store_instance is None:
        _data_store_instance = DataStore(db_path)
    
    return _data_store_instance


def reset_data_store():
    """Reset the singleton instance (useful for testing)."""
    global _data_store_instance
    _data_store_instance = None
