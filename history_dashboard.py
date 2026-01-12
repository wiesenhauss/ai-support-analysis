#!/usr/bin/env python3
from __future__ import annotations
"""
History Dashboard Module for AI Support Analyzer

This module provides a Tkinter-based dashboard for visualizing
historical support analysis data with embedded matplotlib charts.

Features:
- Sentiment trend visualization
- Topic distribution over time
- Resolution rate tracking
- CSAT trends
- Period comparison
- Date range selection
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
import os

# Import matplotlib with Tkinter backend
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.dates as mdates

# Try to import analytics modules
try:
    from data_store import get_data_store, DataStore
    DATA_STORE_AVAILABLE = True
except ImportError:
    DATA_STORE_AVAILABLE = False

try:
    from analytics_engine import get_analytics_engine, AnalyticsEngine
    from insights_engine import get_insights_engine, InsightsEngine, InsightSeverity
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False


class HistoryDashboard(ttk.Frame):
    """
    Dashboard frame for displaying historical analytics.
    
    Embeds matplotlib charts and provides controls for date range
    selection and chart type switching.
    """
    
    # Color scheme for charts
    COLORS = {
        'positive': '#4CAF50',  # Green
        'neutral': '#FFC107',   # Amber
        'negative': '#F44336',  # Red
        'resolved': '#2196F3',  # Blue
        'unresolved': '#9E9E9E',  # Grey
        'good': '#4CAF50',
        'bad': '#F44336',
        'primary': '#1976D2',
        'secondary': '#757575',
        'background': '#FAFAFA',
        'grid': '#E0E0E0'
    }
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.data_store = None
        self.analytics_engine = None
        self.insights_engine = None
        
        # Initialize data connections
        if ANALYTICS_AVAILABLE:
            try:
                self.data_store = get_data_store()
                self.analytics_engine = get_analytics_engine()
                self.insights_engine = get_insights_engine()
            except Exception as e:
                print(f"Failed to initialize analytics: {e}")
        
        # Chart variables - default to topics which works without dates
        self.current_chart = tk.StringVar(value="topics")
        self.granularity = tk.StringVar(value="week")
        self.date_range = tk.StringVar(value="All")  # Default to All to show data
        
        # Setup UI
        self._setup_ui()
        
        # Load initial data
        self.refresh_dashboard()
    
    def _setup_ui(self):
        """Setup the dashboard UI."""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        # === Control Panel ===
        control_frame = ttk.LabelFrame(self, text="Dashboard Controls", padding="10")
        control_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Date range selector
        ttk.Label(control_frame, text="Date Range:").pack(side=tk.LEFT, padx=(0, 5))
        range_combo = ttk.Combobox(
            control_frame, 
            textvariable=self.date_range,
            values=["30", "60", "90", "180", "365", "All"],
            width=10,
            state="readonly"
        )
        range_combo.pack(side=tk.LEFT, padx=(0, 20))
        range_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_dashboard())
        
        # Granularity selector
        ttk.Label(control_frame, text="Granularity:").pack(side=tk.LEFT, padx=(0, 5))
        granularity_combo = ttk.Combobox(
            control_frame,
            textvariable=self.granularity,
            values=["day", "week", "month"],
            width=10,
            state="readonly"
        )
        granularity_combo.pack(side=tk.LEFT, padx=(0, 20))
        granularity_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_dashboard())
        
        # Chart type selector
        ttk.Label(control_frame, text="Chart:").pack(side=tk.LEFT, padx=(0, 5))
        chart_combo = ttk.Combobox(
            control_frame,
            textvariable=self.current_chart,
            values=["sentiment", "topics", "resolution", "csat"],
            width=12,
            state="readonly"
        )
        chart_combo.pack(side=tk.LEFT, padx=(0, 20))
        chart_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_dashboard())
        
        # Refresh button
        ttk.Button(
            control_frame, 
            text="🔄 Refresh", 
            command=self.refresh_dashboard
        ).pack(side=tk.LEFT, padx=(20, 0))
        
        # === Stats Summary ===
        self.stats_frame = ttk.LabelFrame(self, text="Summary Statistics", padding="10")
        self.stats_frame.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        self.stats_labels = {}
        stats_inner = ttk.Frame(self.stats_frame)
        stats_inner.pack(fill=tk.X)
        
        for i, (key, label) in enumerate([
            ('tickets', 'Total Tickets'),
            ('sentiment', 'Positive %'),
            ('resolution', 'Resolved %'),
            ('csat', 'CSAT %')
        ]):
            frame = ttk.Frame(stats_inner)
            frame.pack(side=tk.LEFT, padx=10)
            ttk.Label(frame, text=label, font=('SF Pro Display', 10)).pack()
            self.stats_labels[key] = ttk.Label(frame, text="--", font=('SF Pro Display', 16, 'bold'))
            self.stats_labels[key].pack()
        
        # === Chart Area ===
        chart_frame = ttk.LabelFrame(self, text="Trend Visualization", padding="5")
        chart_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(10, 5), dpi=100, facecolor='white')
        self.ax = self.figure.add_subplot(111)
        
        # Embed in Tkinter
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        
        # Add toolbar
        toolbar_frame = ttk.Frame(chart_frame)
        toolbar_frame.grid(row=1, column=0, sticky="ew")
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()
        
        # === Insights Panel ===
        insights_frame = ttk.LabelFrame(self, text="📊 Automated Insights (Week-over-Week)", padding="5")
        insights_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        insights_frame.columnconfigure(0, weight=1)
        
        # Insights header with refresh button
        insights_header = ttk.Frame(insights_frame)
        insights_header.pack(fill=tk.X, pady=(0, 5))
        
        self.insights_summary_label = ttk.Label(
            insights_header, 
            text="Loading insights...",
            font=('SF Pro Display', 10)
        )
        self.insights_summary_label.pack(side=tk.LEFT)
        
        ttk.Button(
            insights_header,
            text="🔄 Refresh Insights",
            command=self._refresh_insights
        ).pack(side=tk.RIGHT)
        
        # Insights list
        self.insights_text = tk.Text(
            insights_frame,
            height=6,
            wrap=tk.WORD,
            font=('SF Pro Display', 10),
            state=tk.DISABLED,
            background='#FAFAFA'
        )
        self.insights_text.pack(fill=tk.X, expand=False)
        
        # Configure text tags for styling
        self.insights_text.tag_configure('critical', foreground='#D32F2F', font=('SF Pro Display', 10, 'bold'))
        self.insights_text.tag_configure('warning', foreground='#F57C00', font=('SF Pro Display', 10, 'bold'))
        self.insights_text.tag_configure('info', foreground='#1976D2')
        self.insights_text.tag_configure('positive', foreground='#388E3C')
        self.insights_text.tag_configure('title', font=('SF Pro Display', 10, 'bold'))
        
        # === Batches List ===
        batches_frame = ttk.LabelFrame(self, text="Import History", padding="5")
        batches_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Treeview for batches
        columns = ('date', 'file', 'tickets', 'period')
        self.batches_tree = ttk.Treeview(batches_frame, columns=columns, show='headings', height=4)
        
        self.batches_tree.heading('date', text='Import Date')
        self.batches_tree.heading('file', text='Source File')
        self.batches_tree.heading('tickets', text='Tickets')
        self.batches_tree.heading('period', text='Period')
        
        self.batches_tree.column('date', width=150)
        self.batches_tree.column('file', width=300)
        self.batches_tree.column('tickets', width=100)
        self.batches_tree.column('period', width=200)
        
        scrollbar = ttk.Scrollbar(batches_frame, orient=tk.VERTICAL, command=self.batches_tree.yview)
        self.batches_tree.configure(yscrollcommand=scrollbar.set)
        
        self.batches_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _get_date_range(self):
        """Get start and end dates based on selection."""
        range_value = self.date_range.get()
        
        # Always return None for both to get all data if dates aren't working
        # This ensures data is shown even if date parsing failed
        if range_value == "All":
            return None, None
        
        end_date = date.today()
        days = int(range_value)
        start_date = end_date - timedelta(days=days)
        
        return start_date, end_date
    
    def refresh_dashboard(self):
        """Refresh all dashboard components."""
        if not ANALYTICS_AVAILABLE or not self.analytics_engine:
            self._show_no_data_message()
            return
        
        start_date, end_date = self._get_date_range()
        
        # Update statistics
        self._update_stats(start_date, end_date)
        
        # Update chart
        chart_type = self.current_chart.get()
        if chart_type == "sentiment":
            self._draw_sentiment_chart(start_date, end_date)
        elif chart_type == "topics":
            self._draw_topics_chart(start_date, end_date)
        elif chart_type == "resolution":
            self._draw_resolution_chart(start_date, end_date)
        elif chart_type == "csat":
            self._draw_csat_chart(start_date, end_date)
        
        # Update insights
        self._refresh_insights()
        
        # Update batches list
        self._update_batches_list()
    
    def _refresh_insights(self):
        """Refresh the automated insights panel."""
        if not self.insights_engine:
            self._display_insights_message("Insights engine not available")
            return
        
        try:
            # Generate weekly insights
            insights = self.insights_engine.generate_weekly_insights()
            summary = self.insights_engine.get_insights_summary(insights)
            
            # Update summary label
            if summary['total'] == 0:
                self.insights_summary_label.config(
                    text="No significant changes detected this week"
                )
            else:
                parts = []
                if summary['critical'] > 0:
                    parts.append(f"🔴 {summary['critical']} critical")
                if summary['warning'] > 0:
                    parts.append(f"🟡 {summary['warning']} warnings")
                if summary['info'] > 0:
                    parts.append(f"🔵 {summary['info']} info")
                
                self.insights_summary_label.config(
                    text=f"Found {summary['total']} insights: " + ", ".join(parts)
                )
            
            # Display insights
            self._display_insights(insights)
            
        except Exception as e:
            print(f"Error refreshing insights: {e}")
            self._display_insights_message(f"Error loading insights: {str(e)}")
    
    def _display_insights(self, insights):
        """Display insights in the text widget."""
        self.insights_text.config(state=tk.NORMAL)
        self.insights_text.delete(1.0, tk.END)
        
        if not insights:
            self.insights_text.insert(tk.END, "✅ No significant changes detected.\n\n")
            self.insights_text.insert(tk.END, "Your support metrics are stable compared to last week.")
            self.insights_text.config(state=tk.DISABLED)
            return
        
        for i, insight in enumerate(insights[:5]):  # Show top 5 insights
            # Severity indicator
            if insight.severity == InsightSeverity.CRITICAL:
                icon = "🔴"
                tag = 'critical'
            elif insight.severity == InsightSeverity.WARNING:
                icon = "🟡"
                tag = 'warning'
            else:
                icon = "🔵"
                tag = 'info'
            
            # Title
            self.insights_text.insert(tk.END, f"{icon} ", tag)
            self.insights_text.insert(tk.END, f"{insight.title}\n", 'title')
            
            # Description
            self.insights_text.insert(tk.END, f"   {insight.description}\n")
            
            # Change indicator
            change_str = f"   Change: {insight.change_percent:+.1f}%"
            if insight.change_percent > 0 and 'Positive' in insight.title:
                self.insights_text.insert(tk.END, change_str + "\n", 'positive')
            elif insight.change_percent < 0 and 'Negative' in insight.title:
                self.insights_text.insert(tk.END, change_str + "\n", 'positive')
            else:
                self.insights_text.insert(tk.END, change_str + "\n")
            
            if i < len(insights) - 1:
                self.insights_text.insert(tk.END, "\n")
        
        if len(insights) > 5:
            self.insights_text.insert(tk.END, f"\n... and {len(insights) - 5} more insights")
        
        self.insights_text.config(state=tk.DISABLED)
    
    def _display_insights_message(self, message):
        """Display a message in the insights panel."""
        self.insights_text.config(state=tk.NORMAL)
        self.insights_text.delete(1.0, tk.END)
        self.insights_text.insert(tk.END, message)
        self.insights_text.config(state=tk.DISABLED)
    
    def _update_stats(self, start_date, end_date):
        """Update summary statistics."""
        try:
            stats = self.analytics_engine.get_summary_stats(start_date, end_date)
            
            self.stats_labels['tickets'].config(text=f"{stats['ticket_count']:,}")
            self.stats_labels['sentiment'].config(
                text=f"{stats['sentiment']['positive_pct']:.1f}%"
            )
            self.stats_labels['resolution'].config(
                text=f"{stats['resolution']['resolution_rate']:.1f}%"
            )
            self.stats_labels['csat'].config(
                text=f"{stats['csat']['satisfaction_rate']:.1f}%"
            )
        except Exception as e:
            print(f"Error updating stats: {e}")
            for label in self.stats_labels.values():
                label.config(text="--")
    
    def _draw_sentiment_chart(self, start_date, end_date):
        """Draw sentiment trend chart."""
        self.ax.clear()
        
        try:
            df = self.analytics_engine.get_sentiment_trend(
                granularity=self.granularity.get(),
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                self._show_no_data_message(
                    'No date information available for trend analysis.\n\n'
                    'Try the "Topics" view for data without dates,\n'
                    'or import data with valid "Created Date" values.'
                )
                return
            
            # Plot sentiment percentages
            self.ax.plot(df['period'], df['positive_pct'], 
                        color=self.COLORS['positive'], linewidth=2, 
                        marker='o', markersize=4, label='Positive')
            self.ax.plot(df['period'], df['neutral_pct'], 
                        color=self.COLORS['neutral'], linewidth=2, 
                        marker='s', markersize=4, label='Neutral')
            self.ax.plot(df['period'], df['negative_pct'], 
                        color=self.COLORS['negative'], linewidth=2, 
                        marker='^', markersize=4, label='Negative')
            
            self.ax.set_xlabel('Date', fontsize=10)
            self.ax.set_ylabel('Percentage (%)', fontsize=10)
            self.ax.set_title('Sentiment Trend Over Time', fontsize=12, fontweight='bold')
            self.ax.legend(loc='upper right')
            self.ax.grid(True, alpha=0.3)
            self.ax.set_ylim(0, 100)
            
            # Format x-axis dates
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            self.figure.autofmt_xdate()
            
        except Exception as e:
            print(f"Error drawing sentiment chart: {e}")
            self._show_error_message(str(e))
        
        self.canvas.draw()
    
    def _draw_topics_chart(self, start_date, end_date):
        """Draw topic distribution chart."""
        self.ax.clear()
        
        try:
            df = self.analytics_engine.get_topic_distribution(
                start_date=start_date,
                end_date=end_date,
                top_n=10
            )
            
            if df.empty:
                self._show_no_data_message()
                return
            
            # Horizontal bar chart
            colors = plt.cm.Set3(range(len(df)))
            bars = self.ax.barh(df['topic'], df['percentage'], color=colors)
            
            # Add value labels
            for bar, pct in zip(bars, df['percentage']):
                self.ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                           f'{pct:.1f}%', va='center', fontsize=9)
            
            self.ax.set_xlabel('Percentage (%)', fontsize=10)
            self.ax.set_title('Top Topics Distribution', fontsize=12, fontweight='bold')
            self.ax.invert_yaxis()  # Top topic at top
            
        except Exception as e:
            print(f"Error drawing topics chart: {e}")
            self._show_error_message(str(e))
        
        self.canvas.draw()
    
    def _draw_resolution_chart(self, start_date, end_date):
        """Draw resolution rate trend chart."""
        self.ax.clear()
        
        try:
            df = self.analytics_engine.get_resolution_trend(
                granularity=self.granularity.get(),
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                self._show_no_data_message(
                    'No date information available for trend analysis.\n\n'
                    'Try the "Topics" view for data without dates,\n'
                    'or import data with valid "Created Date" values.'
                )
                return
            
            # Plot resolution rate
            self.ax.plot(df['period'], df['resolution_rate'], 
                        color=self.COLORS['resolved'], linewidth=2, 
                        marker='o', markersize=6, label='Resolution Rate')
            
            # Fill area under curve
            self.ax.fill_between(df['period'], df['resolution_rate'], 
                                alpha=0.3, color=self.COLORS['resolved'])
            
            self.ax.set_xlabel('Date', fontsize=10)
            self.ax.set_ylabel('Resolution Rate (%)', fontsize=10)
            self.ax.set_title('Issue Resolution Rate Over Time', fontsize=12, fontweight='bold')
            self.ax.grid(True, alpha=0.3)
            self.ax.set_ylim(0, 100)
            
            # Format x-axis dates
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            self.figure.autofmt_xdate()
            
        except Exception as e:
            print(f"Error drawing resolution chart: {e}")
            self._show_error_message(str(e))
        
        self.canvas.draw()
    
    def _draw_csat_chart(self, start_date, end_date):
        """Draw CSAT satisfaction trend chart."""
        self.ax.clear()
        
        try:
            df = self.analytics_engine.get_csat_trend(
                granularity=self.granularity.get(),
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                self._show_no_data_message(
                    'No date information available for CSAT trend analysis.\n\n'
                    'Try the "Topics" view for data without dates,\n'
                    'or import data with valid "Created Date" values.'
                )
                return
            
            # Plot satisfaction rate
            self.ax.plot(df['period'], df['satisfaction_rate'], 
                        color=self.COLORS['good'], linewidth=2, 
                        marker='o', markersize=6, label='Satisfaction Rate')
            
            # Fill area under curve
            self.ax.fill_between(df['period'], df['satisfaction_rate'], 
                                alpha=0.3, color=self.COLORS['good'])
            
            self.ax.set_xlabel('Date', fontsize=10)
            self.ax.set_ylabel('CSAT Satisfaction Rate (%)', fontsize=10)
            self.ax.set_title('Customer Satisfaction Over Time', fontsize=12, fontweight='bold')
            self.ax.grid(True, alpha=0.3)
            self.ax.set_ylim(0, 100)
            
            # Format x-axis dates
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            self.figure.autofmt_xdate()
            
        except Exception as e:
            print(f"Error drawing CSAT chart: {e}")
            self._show_error_message(str(e))
        
        self.canvas.draw()
    
    def _show_no_data_message(self, message: str = None):
        """Show a message when no data is available."""
        self.ax.clear()
        if message is None:
            message = 'No historical data available.\n\nImport analysis results to see trends.'
        self.ax.text(0.5, 0.5, message,
                    ha='center', va='center', fontsize=12, color='gray',
                    transform=self.ax.transAxes)
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('off')
        self.canvas.draw()
    
    def _show_error_message(self, error: str):
        """Show an error message on the chart."""
        self.ax.clear()
        self.ax.text(0.5, 0.5, f'Error loading data:\n{error}',
                    ha='center', va='center', fontsize=10, color='red',
                    transform=self.ax.transAxes)
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('off')
        self.canvas.draw()
    
    def _update_batches_list(self):
        """Update the batches list."""
        # Clear existing items
        for item in self.batches_tree.get_children():
            self.batches_tree.delete(item)
        
        if not self.data_store:
            return
        
        try:
            batches = self.data_store.get_all_batches()
            
            for batch in batches:
                import_date = batch['import_date'].strftime('%Y-%m-%d %H:%M') if batch['import_date'] else '--'
                period = ''
                if batch['period_start'] and batch['period_end']:
                    period = f"{batch['period_start']} to {batch['period_end']}"
                
                self.batches_tree.insert('', 'end', values=(
                    import_date,
                    batch['source_file'],
                    f"{batch['new_tickets']:,}",
                    period
                ))
        except Exception as e:
            print(f"Error loading batches: {e}")


class HistoryWindow(tk.Toplevel):
    """
    Standalone window for the History Dashboard.
    
    Can be opened from the main application to view historical analytics.
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Historical Analytics Dashboard")
        self.geometry("1200x800")
        
        # Make it modal-like but allow interaction with parent
        self.transient(parent)
        
        # Add the dashboard
        self.dashboard = HistoryDashboard(self)
        self.dashboard.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 1200) // 2
        y = (self.winfo_screenheight() - 800) // 2
        self.geometry(f"+{x}+{y}")


def open_history_dashboard(parent):
    """
    Open the history dashboard window.
    
    Args:
        parent: Parent Tkinter window
        
    Returns:
        HistoryWindow instance
    """
    if not ANALYTICS_AVAILABLE:
        messagebox.showerror(
            "Feature Unavailable",
            "Historical analytics module is not available.\n\n"
            "Please ensure data_store.py, models.py, and analytics_engine.py "
            "are in the application directory."
        )
        return None
    
    return HistoryWindow(parent)
