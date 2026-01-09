#!/usr/bin/env python3
"""
Insight Exporter - Export Product Insights to Various Formats

This module provides export functionality for product insights to:
- CSV for spreadsheet analysis
- Markdown for Notion/documentation
- JSON for Jira/API integration
- Weekly digest reports

Author: AI Support Analyzer Team
"""

import json
import csv
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import os

from product_insights import (
    ProductInsight, ProductInsightsStore, InsightType, InsightStatus,
    get_insights_store
)


class InsightExporter:
    """
    Exports product insights to various formats for team workflows.
    """
    
    def __init__(self, insights_store: Optional[ProductInsightsStore] = None):
        """
        Initialize the exporter.
        
        Args:
            insights_store: ProductInsightsStore instance (uses global if not provided)
        """
        self.insights_store = insights_store or get_insights_store()
    
    def export_to_csv(
        self,
        output_path: str,
        insight_type: Optional[InsightType] = None,
        product_area: Optional[str] = None,
        status: Optional[InsightStatus] = None,
        min_impact: float = 0
    ) -> str:
        """
        Export insights to CSV format.
        
        Args:
            output_path: Path to save the CSV file
            insight_type: Filter by type
            product_area: Filter by product area
            status: Filter by status
            min_impact: Minimum impact score
            
        Returns:
            Path to the created file
        """
        insights = self.insights_store.get_insights(
            insight_type=insight_type,
            product_area=product_area,
            status=status,
            min_impact=min_impact,
            limit=None
        )
        
        headers = [
            'ID', 'Type', 'Product Area', 'Title', 'Description',
            'Impact Score', 'Ticket Count', 'Negative %', 'Resolved %',
            'Trend', 'Trend %', 'Status', 'First Seen', 'Last Seen',
            'Keywords'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for insight in insights:
                keywords = json.loads(insight.keywords) if insight.keywords else []
                writer.writerow([
                    insight.id,
                    insight.insight_type,
                    insight.product_area,
                    insight.title,
                    insight.description or '',
                    f"{insight.impact_score:.1f}",
                    insight.ticket_count,
                    f"{insight.negative_pct:.1f}",
                    f"{insight.resolved_pct:.1f}",
                    insight.trend_direction,
                    f"{insight.trend_pct:.1f}",
                    insight.status,
                    insight.first_seen.isoformat() if insight.first_seen else '',
                    insight.last_seen.isoformat() if insight.last_seen else '',
                    ', '.join(keywords)
                ])
        
        return output_path
    
    def export_to_markdown(
        self,
        output_path: str,
        title: str = "Product Insights Report",
        insight_type: Optional[InsightType] = None,
        product_area: Optional[str] = None,
        include_recommendations: bool = True
    ) -> str:
        """
        Export insights to Markdown format (Notion-compatible).
        
        Args:
            output_path: Path to save the Markdown file
            title: Report title
            insight_type: Filter by type
            product_area: Filter by product area
            include_recommendations: Include action recommendations
            
        Returns:
            Path to the created file
        """
        insights = self.insights_store.get_insights(
            insight_type=insight_type,
            product_area=product_area,
            limit=50
        )
        
        lines = []
        
        # Header
        lines.append(f"# {title}")
        lines.append(f"\n*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
        
        # Summary stats
        summary = self.insights_store.get_insights_summary()
        lines.append("## Summary\n")
        lines.append(f"- **Total Insights:** {summary['total_insights']}")
        lines.append(f"- **By Type:** " + ", ".join([f"{k}: {v}" for k, v in summary.get('by_type', {}).items()]))
        lines.append(f"- **By Area:** " + ", ".join([f"{k}: {v}" for k, v in summary.get('by_product_area', {}).items()][:5]))
        lines.append("")
        
        # Group by type
        by_type: Dict[str, List[ProductInsight]] = {}
        for insight in insights:
            if insight.insight_type not in by_type:
                by_type[insight.insight_type] = []
            by_type[insight.insight_type].append(insight)
        
        # Type order for display
        type_order = ['pain_point', 'feature_request', 'bug', 'improvement', 'praise']
        type_icons = {
            'pain_point': '🔴',
            'feature_request': '💡',
            'bug': '🐛',
            'improvement': '📈',
            'praise': '⭐'
        }
        
        for insight_type in type_order:
            if insight_type not in by_type:
                continue
            
            type_insights = by_type[insight_type]
            icon = type_icons.get(insight_type, '📋')
            lines.append(f"\n## {icon} {insight_type.replace('_', ' ').title()}s ({len(type_insights)})\n")
            
            for insight in type_insights[:10]:  # Top 10 per type
                trend_icon = '↑' if insight.trend_direction == 'increasing' else ('↓' if insight.trend_direction == 'decreasing' else '→')
                status_icon = '✅' if insight.status == 'resolved' else ('🔄' if insight.status == 'in_progress' else '🆕')
                
                lines.append(f"### {status_icon} {insight.title}")
                lines.append(f"\n**Impact:** {insight.impact_score:.0f} | **Tickets:** {insight.ticket_count} | **Trend:** {trend_icon} {abs(insight.trend_pct):.0f}%")
                lines.append(f"\n**Product Area:** {insight.product_area}")
                
                if insight.description:
                    lines.append(f"\n{insight.description}\n")
                
                # Metrics
                lines.append(f"\n| Metric | Value |")
                lines.append(f"|--------|-------|")
                lines.append(f"| Negative Sentiment | {insight.negative_pct:.1f}% |")
                lines.append(f"| Resolution Rate | {insight.resolved_pct:.1f}% |")
                lines.append(f"| First Seen | {insight.first_seen or 'N/A'} |")
                lines.append(f"| Last Seen | {insight.last_seen or 'N/A'} |")
                lines.append("")
                
                if include_recommendations:
                    lines.append("**Recommended Actions:**")
                    if insight.insight_type == 'pain_point':
                        lines.append("- Investigate root cause with product team")
                        lines.append("- Review related tickets for patterns")
                    elif insight.insight_type == 'feature_request':
                        lines.append("- Add to product backlog for consideration")
                        lines.append("- Assess feasibility and impact")
                    lines.append("")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return output_path
    
    def export_to_jira_format(
        self,
        output_path: str,
        project_key: str = "PROD",
        insight_type: Optional[InsightType] = None,
        min_impact: float = 50
    ) -> str:
        """
        Export insights as Jira-compatible JSON for bulk import.
        
        Args:
            output_path: Path to save the JSON file
            project_key: Jira project key
            insight_type: Filter by type
            min_impact: Minimum impact score for export
            
        Returns:
            Path to the created file
        """
        insights = self.insights_store.get_insights(
            insight_type=insight_type,
            min_impact=min_impact,
            limit=50
        )
        
        # Map insight types to Jira issue types
        type_mapping = {
            'feature_request': 'Story',
            'pain_point': 'Bug',
            'bug': 'Bug',
            'improvement': 'Improvement',
            'praise': 'Story'
        }
        
        # Map status to Jira status
        status_mapping = {
            'new': 'To Do',
            'acknowledged': 'To Do',
            'in_progress': 'In Progress',
            'resolved': 'Done',
            'wont_fix': 'Done'
        }
        
        jira_issues = []
        
        for insight in insights:
            issue = {
                'project': {'key': project_key},
                'summary': insight.title[:255],  # Jira limit
                'description': self._format_jira_description(insight),
                'issuetype': {'name': type_mapping.get(insight.insight_type, 'Task')},
                'priority': {'name': self._get_jira_priority(insight)},
                'labels': [
                    f"product-insight",
                    f"area-{insight.product_area.lower().replace(' ', '-')}",
                    f"impact-{int(insight.impact_score)}"
                ],
                'customfield_impact_score': insight.impact_score,
                'customfield_ticket_count': insight.ticket_count,
                'customfield_negative_sentiment': insight.negative_pct
            }
            
            jira_issues.append(issue)
        
        output = {
            'issues': jira_issues,
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_issues': len(jira_issues),
                'min_impact_filter': min_impact
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, default=str)
        
        return output_path
    
    def _format_jira_description(self, insight: ProductInsight) -> str:
        """Format insight as Jira description with markup."""
        lines = []
        
        if insight.description:
            lines.append(insight.description)
            lines.append("")
        
        lines.append("h3. Metrics")
        lines.append(f"* *Impact Score:* {insight.impact_score:.1f}")
        lines.append(f"* *Ticket Count:* {insight.ticket_count}")
        lines.append(f"* *Negative Sentiment:* {insight.negative_pct:.1f}%")
        lines.append(f"* *Resolution Rate:* {insight.resolved_pct:.1f}%")
        lines.append(f"* *Product Area:* {insight.product_area}")
        lines.append("")
        
        lines.append("h3. Trend")
        trend_text = f"{insight.trend_direction} ({insight.trend_pct:+.1f}%)"
        lines.append(f"* {trend_text}")
        
        if insight.first_seen and insight.last_seen:
            lines.append(f"* *Period:* {insight.first_seen} to {insight.last_seen}")
        
        lines.append("")
        lines.append("----")
        lines.append("_Generated from AI Support Analyzer Product Insights_")
        
        return '\n'.join(lines)
    
    def _get_jira_priority(self, insight: ProductInsight) -> str:
        """Determine Jira priority based on impact score."""
        if insight.impact_score >= 80:
            return 'Highest'
        elif insight.impact_score >= 60:
            return 'High'
        elif insight.impact_score >= 40:
            return 'Medium'
        elif insight.impact_score >= 20:
            return 'Low'
        return 'Lowest'
    
    def generate_weekly_digest(
        self,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate a weekly digest of insights in Markdown format.
        
        Args:
            output_path: Path to save the digest (optional)
            
        Returns:
            The digest content as a string
        """
        # Get all insights
        insights = self.insights_store.get_insights(limit=100)
        summary = self.insights_store.get_insights_summary()
        
        lines = []
        
        # Header
        week_start = date.today() - timedelta(days=7)
        lines.append(f"# 📊 Weekly Product Insights Digest")
        lines.append(f"\n*Week of {week_start.strftime('%B %d, %Y')} - {date.today().strftime('%B %d, %Y')}*\n")
        
        # Executive Summary
        lines.append("## Executive Summary\n")
        
        # Count by severity
        new_insights = [i for i in insights if i.status == 'new']
        increasing = [i for i in insights if i.trend_direction == 'increasing']
        high_impact = [i for i in insights if i.impact_score >= 70]
        
        lines.append(f"- **Total Active Insights:** {summary['total_insights']}")
        lines.append(f"- **New This Period:** {len(new_insights)}")
        lines.append(f"- **Trending Up:** {len(increasing)}")
        lines.append(f"- **High Priority (Impact ≥70):** {len(high_impact)}")
        lines.append("")
        
        # Top 5 Priority Items
        lines.append("## 🎯 Top Priority Items\n")
        for i, insight in enumerate(high_impact[:5], 1):
            trend_icon = '📈' if insight.trend_direction == 'increasing' else '📉' if insight.trend_direction == 'decreasing' else '➡️'
            lines.append(f"### {i}. [{insight.insight_type.upper()}] {insight.title}")
            lines.append(f"\n{trend_icon} **Impact:** {insight.impact_score:.0f} | **Tickets:** {insight.ticket_count} | **Area:** {insight.product_area}")
            if insight.description:
                lines.append(f"\n{insight.description[:200]}...")
            lines.append("")
        
        # Emerging Issues
        lines.append("## ⚠️ Emerging Issues (Growing Trends)\n")
        for insight in increasing[:5]:
            lines.append(f"- **{insight.title}** - {insight.product_area} (+{insight.trend_pct:.0f}%)")
        if not increasing:
            lines.append("*No significant emerging issues detected.*")
        lines.append("")
        
        # By Product Area
        lines.append("## 📦 By Product Area\n")
        by_area = summary.get('by_product_area', {})
        sorted_areas = sorted(by_area.items(), key=lambda x: x[1], reverse=True)
        for area, count in sorted_areas[:7]:
            lines.append(f"- **{area}:** {count} insights")
        lines.append("")
        
        # Resolved This Week
        resolved = [i for i in insights if i.status == 'resolved']
        if resolved:
            lines.append("## ✅ Recently Resolved\n")
            for insight in resolved[:5]:
                lines.append(f"- {insight.title} ({insight.product_area})")
            lines.append("")
        
        # Recommendations
        lines.append("## 💡 Recommendations\n")
        lines.append("1. **Focus on top priority items** - Address high-impact insights first")
        if increasing:
            lines.append("2. **Monitor emerging issues** - These may need attention soon")
        if by_area:
            top_area = sorted_areas[0][0] if sorted_areas else "Unknown"
            lines.append(f"3. **{top_area} attention needed** - Most insights in this area")
        lines.append("")
        
        # Footer
        lines.append("---")
        lines.append(f"*Generated by AI Support Analyzer on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        
        content = '\n'.join(lines)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return content
    
    def export_insights_json(
        self,
        output_path: str,
        insight_type: Optional[InsightType] = None,
        product_area: Optional[str] = None
    ) -> str:
        """
        Export insights as JSON for API integration.
        
        Args:
            output_path: Path to save the JSON file
            insight_type: Filter by type
            product_area: Filter by product area
            
        Returns:
            Path to the created file
        """
        insights = self.insights_store.get_insights(
            insight_type=insight_type,
            product_area=product_area,
            limit=None
        )
        
        output = {
            'generated_at': datetime.now().isoformat(),
            'total_count': len(insights),
            'insights': [insight.to_dict() for insight in insights]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, default=str)
        
        return output_path


# Singleton instance
_exporter = None

def get_insight_exporter() -> InsightExporter:
    """Get the global InsightExporter instance."""
    global _exporter
    if _exporter is None:
        _exporter = InsightExporter()
    return _exporter


def export_insights_cli():
    """Command-line interface for exporting insights."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export product insights')
    parser.add_argument('--format', choices=['csv', 'markdown', 'jira', 'json', 'digest'],
                        default='markdown', help='Export format')
    parser.add_argument('--output', '-o', type=str, help='Output file path')
    parser.add_argument('--type', type=str, help='Filter by insight type')
    parser.add_argument('--area', type=str, help='Filter by product area')
    parser.add_argument('--min-impact', type=float, default=0, help='Minimum impact score')
    
    args = parser.parse_args()
    
    exporter = get_insight_exporter()
    
    # Default output paths
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    default_paths = {
        'csv': f'insights_export_{timestamp}.csv',
        'markdown': f'insights_report_{timestamp}.md',
        'jira': f'insights_jira_{timestamp}.json',
        'json': f'insights_export_{timestamp}.json',
        'digest': f'weekly_digest_{timestamp}.md'
    }
    
    output_path = args.output or default_paths[args.format]
    insight_type = InsightType(args.type) if args.type else None
    
    print(f"📤 Exporting insights to {args.format.upper()} format...")
    
    if args.format == 'csv':
        result = exporter.export_to_csv(output_path, insight_type, args.area, min_impact=args.min_impact)
    elif args.format == 'markdown':
        result = exporter.export_to_markdown(output_path, insight_type=insight_type, product_area=args.area)
    elif args.format == 'jira':
        result = exporter.export_to_jira_format(output_path, insight_type=insight_type, min_impact=args.min_impact)
    elif args.format == 'json':
        result = exporter.export_insights_json(output_path, insight_type, args.area)
    elif args.format == 'digest':
        content = exporter.generate_weekly_digest(output_path)
        result = output_path
        print("\n--- Digest Preview ---")
        print(content[:500] + "...")
    
    print(f"✅ Exported to: {result}")


if __name__ == '__main__':
    export_insights_cli()
