#!/usr/bin/env python3
"""
Insight Extractor - AI-Powered Product Insight Extraction

This module processes analyzed support tickets to extract and cluster
similar feedback into actionable product insights.

Features:
- Extracts feature requests and pain points from ticket data
- Clusters similar feedback using AI
- Calculates impact scores for prioritization
- Detects trends and emerging issues
"""

import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Base, TicketAnalysis
from product_insights import (
    ProductInsight, ProductInsightsStore, InsightType, InsightStatus,
    PRODUCT_AREAS, insight_tickets
)
from data_store import get_data_store
from utils import get_openai_client


# AI prompt for clustering similar feedback into insights
CLUSTERING_PROMPT = """Analyze the following customer feedback items and group them into coherent product insights.

Feedback items:
{feedback_items}

For each distinct insight you identify, provide:
1. A concise title (max 100 chars)
2. The insight type: feature_request, pain_point, improvement, or bug
3. A detailed description explaining the insight
4. Keywords that characterize this insight (for future matching)
5. Which feedback item IDs belong to this insight

Respond in JSON format:
{{
    "insights": [
        {{
            "title": "...",
            "type": "feature_request|pain_point|improvement|bug",
            "description": "...",
            "keywords": ["keyword1", "keyword2"],
            "feedback_ids": [1, 2, 3]
        }}
    ]
}}

Group similar feedback together. Be specific and actionable in your titles and descriptions.
Focus on patterns - insights should represent issues mentioned by multiple users when possible."""


class InsightExtractor:
    """
    Extracts and clusters product insights from analyzed tickets.
    """
    
    def __init__(self, data_store=None, insights_store=None):
        """
        Initialize the extractor.
        
        Args:
            data_store: DataStore instance (uses global if not provided)
            insights_store: ProductInsightsStore instance (uses global if not provided)
        """
        self.data_store = data_store or get_data_store()
        if insights_store:
            self.insights_store = insights_store
        else:
            from product_insights import get_insights_store
            self.insights_store = get_insights_store()
    
    def extract_feedback_from_tickets(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        product_area: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Extract feature requests and pain points from tickets.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            product_area: Filter by product area
            limit: Maximum number of tickets to process
            
        Returns:
            List of feedback items with metadata
        """
        session = self.data_store._get_session()
        try:
            query = session.query(TicketAnalysis)
            
            # Apply filters
            if start_date:
                query = query.filter(TicketAnalysis.created_date >= start_date)
            if end_date:
                query = query.filter(TicketAnalysis.created_date <= end_date)
            if product_area:
                query = query.filter(TicketAnalysis.product_area == product_area)
            
            # Only get tickets with feedback
            query = query.filter(
                (TicketAnalysis.feature_requests.isnot(None)) |
                (TicketAnalysis.pain_points.isnot(None)) |
                (TicketAnalysis.product_feedback.isnot(None))
            )
            
            query = query.order_by(TicketAnalysis.created_date.desc())
            
            if limit:
                query = query.limit(limit)
            
            tickets = query.all()
            
            feedback_items = []
            for ticket in tickets:
                # Parse feature requests
                feature_requests = self._parse_json_array(ticket.feature_requests)
                for fr in feature_requests:
                    if fr and fr.strip():
                        feedback_items.append({
                            'id': len(feedback_items) + 1,
                            'ticket_id': ticket.id,
                            'type': 'feature_request',
                            'content': fr.strip(),
                            'product_area': ticket.product_area or 'Other',
                            'sentiment': ticket.sentiment,
                            'resolved': ticket.issue_resolved,
                            'date': ticket.created_date
                        })
                
                # Parse pain points
                pain_points = self._parse_json_array(ticket.pain_points)
                for pp in pain_points:
                    if pp and pp.strip():
                        feedback_items.append({
                            'id': len(feedback_items) + 1,
                            'ticket_id': ticket.id,
                            'type': 'pain_point',
                            'content': pp.strip(),
                            'product_area': ticket.product_area or 'Other',
                            'sentiment': ticket.sentiment,
                            'resolved': ticket.issue_resolved,
                            'date': ticket.created_date
                        })
                
                # Also consider product feedback text
                if ticket.product_feedback and ticket.product_feedback != 'NONE':
                    # Determine type based on sentiment
                    fb_type = 'pain_point' if ticket.sentiment == 'Negative' else 'improvement'
                    feedback_items.append({
                        'id': len(feedback_items) + 1,
                        'ticket_id': ticket.id,
                        'type': fb_type,
                        'content': ticket.product_feedback[:500],  # Truncate long feedback
                        'product_area': ticket.product_area or 'Other',
                        'sentiment': ticket.sentiment,
                        'resolved': ticket.issue_resolved,
                        'date': ticket.created_date
                    })
            
            return feedback_items
        finally:
            session.close()
    
    def _parse_json_array(self, value: Optional[str]) -> List[str]:
        """Parse a JSON array string into a list."""
        if not value:
            return []
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if item]
            return []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def cluster_feedback_with_ai(
        self,
        feedback_items: List[Dict[str, Any]],
        api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Use AI to cluster similar feedback into coherent insights.
        
        Args:
            feedback_items: List of feedback items to cluster
            api_key: OpenAI API key (uses env if not provided)
            
        Returns:
            List of clustered insights
        """
        if not feedback_items:
            return []
        
        # Format feedback for the AI prompt
        feedback_text = "\n".join([
            f"[{item['id']}] ({item['type']}) {item['content']}"
            for item in feedback_items[:100]  # Limit to avoid token limits
        ])
        
        prompt = CLUSTERING_PROMPT.format(feedback_items=feedback_text)
        
        try:
            client = get_openai_client(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a product analyst clustering customer feedback into actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=2000
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get('insights', [])
            
        except Exception as e:
            print(f"Error clustering feedback with AI: {e}")
            # Fallback: Create insights from individual high-impact items
            return self._fallback_clustering(feedback_items)
    
    def _fallback_clustering(self, feedback_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Simple clustering fallback when AI is unavailable.
        Groups by product area and type.
        """
        clusters = defaultdict(list)
        
        for item in feedback_items:
            key = (item['product_area'], item['type'])
            clusters[key].append(item)
        
        insights = []
        for (area, fb_type), items in clusters.items():
            if len(items) >= 2:  # Only create insights for patterns
                # Use the most common content as the title
                contents = [item['content'] for item in items]
                title = contents[0][:100] if contents else f"{fb_type.replace('_', ' ').title()} in {area}"
                
                insights.append({
                    'title': title,
                    'type': fb_type,
                    'description': f"Multiple users reported: {'; '.join(contents[:3])}",
                    'keywords': [area.lower(), fb_type],
                    'feedback_ids': [item['id'] for item in items]
                })
        
        return insights
    
    def create_insights_from_clusters(
        self,
        clusters: List[Dict[str, Any]],
        feedback_items: List[Dict[str, Any]]
    ) -> List[ProductInsight]:
        """
        Create ProductInsight records from clustered feedback.
        
        Args:
            clusters: Clustered insight data from AI
            feedback_items: Original feedback items for linking
            
        Returns:
            List of created ProductInsight instances
        """
        # Build a mapping from feedback ID to item
        feedback_map = {item['id']: item for item in feedback_items}
        
        created_insights = []
        
        for cluster in clusters:
            # Get the feedback items for this cluster
            cluster_items = [
                feedback_map.get(fid) 
                for fid in cluster.get('feedback_ids', [])
                if fid in feedback_map
            ]
            
            if not cluster_items:
                continue
            
            # Determine product area (most common among items)
            area_counts = defaultdict(int)
            for item in cluster_items:
                if item:
                    area_counts[item.get('product_area', 'Other')] += 1
            product_area = max(area_counts, key=area_counts.get) if area_counts else 'Other'
            
            # Get ticket IDs
            ticket_ids = list(set(item['ticket_id'] for item in cluster_items if item))
            
            # Create the insight
            try:
                insight = self.insights_store.create_insight(
                    title=cluster['title'],
                    insight_type=InsightType(cluster['type']),
                    product_area=product_area,
                    description=cluster.get('description'),
                    keywords=cluster.get('keywords', [])
                )
                
                # Link tickets
                if ticket_ids:
                    self.insights_store.link_tickets_to_insight(insight.id, ticket_ids)
                
                created_insights.append(insight)
                
            except Exception as e:
                print(f"Error creating insight: {e}")
                continue
        
        return created_insights
    
    def extract_insights_from_batch(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        product_area: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Full pipeline: Extract feedback, cluster, and create insights.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            product_area: Filter by product area
            api_key: OpenAI API key
            
        Returns:
            Summary of extraction results
        """
        print("📊 Extracting feedback from tickets...")
        feedback_items = self.extract_feedback_from_tickets(
            start_date=start_date,
            end_date=end_date,
            product_area=product_area
        )
        
        if not feedback_items:
            return {
                'success': True,
                'feedback_count': 0,
                'insights_created': 0,
                'message': 'No feedback found in the specified range'
            }
        
        print(f"📝 Found {len(feedback_items)} feedback items")
        print("🤖 Clustering feedback with AI...")
        
        clusters = self.cluster_feedback_with_ai(feedback_items, api_key)
        
        print(f"✨ Identified {len(clusters)} potential insights")
        print("💾 Creating insight records...")
        
        created_insights = self.create_insights_from_clusters(clusters, feedback_items)
        
        return {
            'success': True,
            'feedback_count': len(feedback_items),
            'clusters_found': len(clusters),
            'insights_created': len(created_insights),
            'insights': [i.to_dict() for i in created_insights]
        }
    
    def update_insight_trends(self) -> int:
        """
        Update trend direction and percentage for all insights.
        Compares current week's ticket count vs previous week.
        
        Returns:
            Number of insights updated
        """
        session = self.data_store._get_session()
        try:
            insights = session.query(ProductInsight).all()
            updated = 0
            
            today = date.today()
            week_ago = today - timedelta(days=7)
            two_weeks_ago = today - timedelta(days=14)
            
            for insight in insights:
                # Count tickets in each period
                current_week = session.query(func.count(TicketAnalysis.id)).filter(
                    TicketAnalysis.id.in_([t.id for t in insight.tickets]),
                    TicketAnalysis.created_date >= week_ago
                ).scalar() or 0
                
                previous_week = session.query(func.count(TicketAnalysis.id)).filter(
                    TicketAnalysis.id.in_([t.id for t in insight.tickets]),
                    TicketAnalysis.created_date >= two_weeks_ago,
                    TicketAnalysis.created_date < week_ago
                ).scalar() or 0
                
                # Calculate trend
                if previous_week > 0:
                    change_pct = ((current_week - previous_week) / previous_week) * 100
                    if change_pct > 10:
                        insight.trend_direction = 'increasing'
                    elif change_pct < -10:
                        insight.trend_direction = 'decreasing'
                    else:
                        insight.trend_direction = 'stable'
                    insight.trend_pct = change_pct
                else:
                    insight.trend_direction = 'new' if current_week > 0 else 'stable'
                    insight.trend_pct = 0
                
                # Recalculate impact score
                insight.calculate_impact_score()
                updated += 1
            
            session.commit()
            return updated
        finally:
            session.close()
    
    def get_emerging_issues(
        self,
        min_growth_pct: float = 50.0,
        min_tickets: int = 3
    ) -> List[ProductInsight]:
        """
        Find insights that are growing rapidly.
        
        Args:
            min_growth_pct: Minimum week-over-week growth percentage
            min_tickets: Minimum number of tickets to consider
            
        Returns:
            List of emerging insights
        """
        session = self.data_store._get_session()
        try:
            insights = session.query(ProductInsight).filter(
                ProductInsight.trend_direction == 'increasing',
                ProductInsight.trend_pct >= min_growth_pct,
                ProductInsight.ticket_count >= min_tickets,
                ProductInsight.status.in_([InsightStatus.NEW.value, InsightStatus.ACKNOWLEDGED.value])
            ).order_by(ProductInsight.trend_pct.desc()).limit(10).all()
            
            return insights
        finally:
            session.close()


# Singleton instance
_extractor = None

def get_insight_extractor() -> InsightExtractor:
    """Get the global InsightExtractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = InsightExtractor()
    return _extractor


def extract_insights_cli():
    """Command-line interface for insight extraction."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Extract product insights from analyzed tickets')
    parser.add_argument('--days', type=int, default=30, help='Number of days to analyze')
    parser.add_argument('--area', type=str, help='Product area to focus on')
    args = parser.parse_args()
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return
    
    extractor = get_insight_extractor()
    
    end_date = date.today()
    start_date = end_date - timedelta(days=args.days)
    
    print(f"\n🔍 Extracting insights from {start_date} to {end_date}")
    if args.area:
        print(f"   Filtering by product area: {args.area}")
    
    result = extractor.extract_insights_from_batch(
        start_date=start_date,
        end_date=end_date,
        product_area=args.area,
        api_key=api_key
    )
    
    print(f"\n✅ Extraction complete!")
    print(f"   Feedback items processed: {result['feedback_count']}")
    print(f"   Clusters identified: {result.get('clusters_found', 0)}")
    print(f"   Insights created: {result['insights_created']}")
    
    if result.get('insights'):
        print("\n📋 Top insights:")
        for insight in result['insights'][:5]:
            print(f"   [{insight['type']}] {insight['title']}")
            print(f"      Impact: {insight['impact_score']:.1f} | Tickets: {insight['ticket_count']}")


if __name__ == '__main__':
    extract_insights_cli()
