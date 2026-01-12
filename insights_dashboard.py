#!/usr/bin/env python3
"""
Product Insights Dashboard

A Tkinter-based dashboard for exploring and managing product insights
extracted from support ticket analyses.

Features:
- Ranked list of insights by impact score
- Filtering by product area, type, status
- Detail view with trend charts
- Status management
- Drill-down to source tickets
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import threading
import queue

# Check for matplotlib availability
try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Import insights modules
try:
    from product_insights import (
        ProductInsight, ProductInsightsStore, InsightType, InsightStatus,
        PRODUCT_AREAS, get_insights_store
    )
    from insight_extractor import get_insight_extractor, InsightExtractor
    from data_store import get_data_store
    INSIGHTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Insights modules not available: {e}")
    INSIGHTS_AVAILABLE = False


class InsightsDashboard(ttk.Frame):
    """
    Main dashboard widget for product insights.
    """
    
    # Color scheme
    COLORS = {
        'feature_request': '#3498db',  # Blue
        'pain_point': '#e74c3c',        # Red
        'improvement': '#2ecc71',       # Green
        'bug': '#e67e22',               # Orange
        'praise': '#9b59b6',            # Purple
        'increasing': '#e74c3c',
        'decreasing': '#2ecc71',
        'stable': '#95a5a6',
        'new': '#3498db'
    }
    
    STATUS_ICONS = {
        'new': '🆕',
        'acknowledged': '👁️',
        'in_progress': '🔄',
        'resolved': '✅',
        'wont_fix': '🚫'
    }
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.parent = parent
        self.insights_store = None
        self.extractor = None
        self.data_store = None
        
        # Current state
        self.selected_insight_id = None
        self.insights_list = []
        
        # Data queue for async operations
        self.data_queue = queue.Queue()
        
        # Initialize connections
        if INSIGHTS_AVAILABLE:
            try:
                self.data_store = get_data_store()
                self.insights_store = get_insights_store()
                self.extractor = get_insight_extractor()
            except Exception as e:
                print(f"Failed to initialize insights: {e}")
        
        # Filter variables
        self.filter_type = tk.StringVar(value="All")
        self.filter_area = tk.StringVar(value="All")
        self.filter_status = tk.StringVar(value="All")
        self.sort_by = tk.StringVar(value="impact_score")
        
        # Setup UI
        self._setup_ui()
        
        # Load initial data
        self.refresh_insights()
    
    def _setup_ui(self):
        """Setup the dashboard UI."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        # === Control Panel ===
        self._setup_controls()
        
        # === Main Content (PanedWindow) ===
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        
        # Left: Insights List
        self._setup_insights_list()
        
        # Right: Detail Panel
        self._setup_detail_panel()
    
    def _setup_controls(self):
        """Setup control panel with filters."""
        control_frame = ttk.LabelFrame(self, text="Filters & Actions", padding="10")
        control_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        # Row 1: Filters
        filter_frame = ttk.Frame(control_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Type filter
        ttk.Label(filter_frame, text="Type:").pack(side=tk.LEFT, padx=(0, 5))
        type_options = ["All"] + [t.value for t in InsightType]
        ttk.OptionMenu(filter_frame, self.filter_type, self.filter_type.get(), 
                       *type_options, command=self._on_filter_change).pack(side=tk.LEFT, padx=(0, 15))
        
        # Product Area filter
        ttk.Label(filter_frame, text="Area:").pack(side=tk.LEFT, padx=(0, 5))
        area_options = ["All"] + PRODUCT_AREAS
        ttk.OptionMenu(filter_frame, self.filter_area, self.filter_area.get(),
                       *area_options, command=self._on_filter_change).pack(side=tk.LEFT, padx=(0, 15))
        
        # Status filter
        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT, padx=(0, 5))
        status_options = ["All"] + [s.value for s in InsightStatus]
        ttk.OptionMenu(filter_frame, self.filter_status, self.filter_status.get(),
                       *status_options, command=self._on_filter_change).pack(side=tk.LEFT, padx=(0, 15))
        
        # Sort by
        ttk.Label(filter_frame, text="Sort:").pack(side=tk.LEFT, padx=(0, 5))
        sort_options = [("Impact", "impact_score"), ("Tickets", "ticket_count"), 
                        ("Recent", "last_seen"), ("Created", "created_at")]
        self.sort_menu = ttk.OptionMenu(filter_frame, self.sort_by, "impact_score",
                                        *[s[1] for s in sort_options], command=self._on_filter_change)
        self.sort_menu.pack(side=tk.LEFT, padx=(0, 15))
        
        # Row 2: Actions
        action_frame = ttk.Frame(control_frame)
        action_frame.pack(fill=tk.X)
        
        ttk.Button(action_frame, text="🔄 Refresh", 
                   command=self.refresh_insights).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(action_frame, text="🔍 Extract New Insights",
                   command=self._extract_new_insights).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(action_frame, text="📊 Update Trends",
                   command=self._update_trends).pack(side=tk.LEFT, padx=(0, 10))
        
        # Export menu
        export_menu_btn = ttk.Menubutton(action_frame, text="📤 Export")
        export_menu = tk.Menu(export_menu_btn, tearoff=0)
        export_menu.add_command(label="Export to CSV", command=lambda: self._export_insights('csv'))
        export_menu.add_command(label="Export to Markdown", command=lambda: self._export_insights('markdown'))
        export_menu.add_command(label="Export to Jira JSON", command=lambda: self._export_insights('jira'))
        export_menu.add_separator()
        export_menu.add_command(label="Generate Weekly Digest", command=self._generate_weekly_digest)
        export_menu_btn["menu"] = export_menu
        export_menu_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Stats display
        self.stats_label = ttk.Label(action_frame, text="")
        self.stats_label.pack(side=tk.RIGHT)
    
    def _setup_insights_list(self):
        """Setup the insights list panel."""
        list_frame = ttk.Frame(self.paned)
        self.paned.add(list_frame, weight=1)
        
        # Treeview for insights
        columns = ('rank', 'type', 'title', 'impact', 'tickets', 'trend', 'status')
        self.insights_tree = ttk.Treeview(list_frame, columns=columns, show='headings', 
                                          selectmode='browse')
        
        # Configure columns
        self.insights_tree.heading('rank', text='#')
        self.insights_tree.heading('type', text='Type')
        self.insights_tree.heading('title', text='Title')
        self.insights_tree.heading('impact', text='Impact')
        self.insights_tree.heading('tickets', text='Tickets')
        self.insights_tree.heading('trend', text='Trend')
        self.insights_tree.heading('status', text='Status')
        
        self.insights_tree.column('rank', width=40, anchor='center')
        self.insights_tree.column('type', width=100)
        self.insights_tree.column('title', width=300)
        self.insights_tree.column('impact', width=60, anchor='center')
        self.insights_tree.column('tickets', width=60, anchor='center')
        self.insights_tree.column('trend', width=80, anchor='center')
        self.insights_tree.column('status', width=80, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, 
                                  command=self.insights_tree.yview)
        self.insights_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.insights_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection
        self.insights_tree.bind('<<TreeviewSelect>>', self._on_insight_select)
    
    def _setup_detail_panel(self):
        """Setup the detail panel for selected insight."""
        detail_frame = ttk.Frame(self.paned)
        self.paned.add(detail_frame, weight=1)
        
        # Create notebook for tabs
        self.detail_notebook = ttk.Notebook(detail_frame)
        self.detail_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Overview
        overview_tab = ttk.Frame(self.detail_notebook, padding="10")
        self.detail_notebook.add(overview_tab, text="Overview")
        
        # Insight info
        self.detail_title = ttk.Label(overview_tab, text="Select an insight", 
                                      font=('TkDefaultFont', 14, 'bold'), wraplength=400)
        self.detail_title.pack(anchor='w', pady=(0, 10))
        
        self.detail_type_label = ttk.Label(overview_tab, text="")
        self.detail_type_label.pack(anchor='w')
        
        self.detail_area_label = ttk.Label(overview_tab, text="")
        self.detail_area_label.pack(anchor='w')
        
        # Metrics
        metrics_frame = ttk.LabelFrame(overview_tab, text="Metrics", padding="10")
        metrics_frame.pack(fill=tk.X, pady=10)
        
        self.metrics_labels = {}
        metrics_grid = ttk.Frame(metrics_frame)
        metrics_grid.pack(fill=tk.X)
        
        for i, (label, key) in enumerate([
            ("Impact Score:", "impact"),
            ("Ticket Count:", "tickets"),
            ("Trend:", "trend"),
            ("Negative Sentiment:", "negative"),
            ("Resolved Rate:", "resolved")
        ]):
            ttk.Label(metrics_grid, text=label).grid(row=i//2, column=(i%2)*2, sticky='w', padx=5, pady=2)
            self.metrics_labels[key] = ttk.Label(metrics_grid, text="--", font=('TkDefaultFont', 10, 'bold'))
            self.metrics_labels[key].grid(row=i//2, column=(i%2)*2+1, sticky='w', padx=5, pady=2)
        
        # Description
        desc_frame = ttk.LabelFrame(overview_tab, text="Description", padding="10")
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.detail_description = scrolledtext.ScrolledText(desc_frame, height=6, wrap=tk.WORD)
        self.detail_description.pack(fill=tk.BOTH, expand=True)
        self.detail_description.configure(state='disabled')
        
        # Status actions
        status_frame = ttk.LabelFrame(overview_tab, text="Update Status", padding="10")
        status_frame.pack(fill=tk.X, pady=10)
        
        status_buttons = ttk.Frame(status_frame)
        status_buttons.pack(fill=tk.X)
        
        for status in InsightStatus:
            icon = self.STATUS_ICONS.get(status.value, '')
            ttk.Button(status_buttons, text=f"{icon} {status.value.replace('_', ' ').title()}",
                      command=lambda s=status: self._update_insight_status(s)).pack(side=tk.LEFT, padx=2)
        
        # Tab 2: Tickets
        tickets_tab = ttk.Frame(self.detail_notebook, padding="10")
        self.detail_notebook.add(tickets_tab, text="Source Tickets")
        
        # Hint label
        ttk.Label(tickets_tab, text="💡 Double-click a ticket to open in Zendesk", 
                  font=('Helvetica', 9, 'italic')).pack(anchor='w', pady=(0, 5))
        
        tickets_frame = ttk.Frame(tickets_tab)
        tickets_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tickets_tree = ttk.Treeview(tickets_frame, columns=('ticket_id', 'date', 'sentiment', 'summary'),
                                         show='headings', height=10)
        self.tickets_tree.heading('ticket_id', text='Ticket #')
        self.tickets_tree.heading('date', text='Date')
        self.tickets_tree.heading('sentiment', text='Sentiment')
        self.tickets_tree.heading('summary', text='Summary')
        
        self.tickets_tree.column('ticket_id', width=90)
        self.tickets_tree.column('date', width=90)
        self.tickets_tree.column('sentiment', width=70)
        self.tickets_tree.column('summary', width=250)
        
        tickets_scroll = ttk.Scrollbar(tickets_frame, orient=tk.VERTICAL,
                                       command=self.tickets_tree.yview)
        self.tickets_tree.configure(yscrollcommand=tickets_scroll.set)
        
        self.tickets_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tickets_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click to open ticket in browser
        self.tickets_tree.bind('<Double-1>', self._on_ticket_double_click)
        
        # Store ticket URLs for opening
        self.ticket_urls = {}
        
        # Tab 3: Trend Chart (if matplotlib available)
        if MATPLOTLIB_AVAILABLE:
            trend_tab = ttk.Frame(self.detail_notebook, padding="10")
            self.detail_notebook.add(trend_tab, text="Trend Chart")
            
            self.trend_figure = Figure(figsize=(5, 3), dpi=100)
            self.trend_ax = self.trend_figure.add_subplot(111)
            self.trend_canvas = FigureCanvasTkAgg(self.trend_figure, master=trend_tab)
            self.trend_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _on_filter_change(self, *args):
        """Handle filter changes."""
        self.refresh_insights()
    
    def _on_insight_select(self, event):
        """Handle insight selection."""
        selection = self.insights_tree.selection()
        if selection:
            item = self.insights_tree.item(selection[0])
            insight_id = item.get('tags', [None])[0]
            if insight_id:
                self.selected_insight_id = int(insight_id)
                self._load_insight_details(self.selected_insight_id)
    
    def refresh_insights(self):
        """Refresh the insights list."""
        if not self.insights_store:
            return
        
        # Clear current list
        for item in self.insights_tree.get_children():
            self.insights_tree.delete(item)
        
        # Build filters
        insight_type = None if self.filter_type.get() == "All" else self.filter_type.get()
        product_area = None if self.filter_area.get() == "All" else self.filter_area.get()
        status = None if self.filter_status.get() == "All" else self.filter_status.get()
        
        try:
            insights = self.insights_store.get_insights(
                insight_type=insight_type,
                product_area=product_area,
                status=status,
                order_by=self.sort_by.get(),
                limit=100
            )
            
            self.insights_list = insights
            
            # Populate tree
            for rank, insight in enumerate(insights, 1):
                trend_text = self._format_trend(insight.trend_direction, insight.trend_pct)
                status_icon = self.STATUS_ICONS.get(insight.status, '')
                
                self.insights_tree.insert('', 'end', 
                    values=(
                        rank,
                        insight.insight_type,
                        insight.title[:50] + '...' if len(insight.title) > 50 else insight.title,
                        f"{insight.impact_score:.0f}",
                        insight.ticket_count,
                        trend_text,
                        f"{status_icon} {insight.status}"
                    ),
                    tags=(str(insight.id),)
                )
            
            # Update stats
            summary = self.insights_store.get_insights_summary()
            self.stats_label.config(text=f"Total: {summary['total_insights']} insights")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load insights: {e}")
    
    def _format_trend(self, direction: str, pct: float) -> str:
        """Format trend for display."""
        if direction == 'increasing':
            return f"↑ {abs(pct):.0f}%"
        elif direction == 'decreasing':
            return f"↓ {abs(pct):.0f}%"
        elif direction == 'new':
            return "🆕 New"
        else:
            return "→ Stable"
    
    def _load_insight_details(self, insight_id: int):
        """Load details for selected insight."""
        try:
            insight = self.insights_store.get_insight_by_id(insight_id)
            if not insight:
                return
            
            # Update overview
            self.detail_title.config(text=insight.title)
            self.detail_type_label.config(text=f"Type: {insight.insight_type}")
            self.detail_area_label.config(text=f"Product Area: {insight.product_area}")
            
            # Update metrics
            self.metrics_labels['impact'].config(text=f"{insight.impact_score:.1f}")
            self.metrics_labels['tickets'].config(text=str(insight.ticket_count))
            self.metrics_labels['trend'].config(
                text=self._format_trend(insight.trend_direction, insight.trend_pct)
            )
            self.metrics_labels['negative'].config(text=f"{insight.negative_pct:.1f}%")
            self.metrics_labels['resolved'].config(text=f"{insight.resolved_pct:.1f}%")
            
            # Update description
            self.detail_description.configure(state='normal')
            self.detail_description.delete(1.0, tk.END)
            if insight.description:
                self.detail_description.insert(tk.END, insight.description)
            self.detail_description.configure(state='disabled')
            
            # Load source tickets
            self._load_source_tickets(insight)
            
            # Update trend chart
            if MATPLOTLIB_AVAILABLE:
                self._draw_trend_chart(insight)
                
        except Exception as e:
            print(f"Error loading insight details: {e}")
    
    def _load_source_tickets(self, insight: ProductInsight):
        """Load source tickets for the insight."""
        # Clear current tickets and URLs
        for item in self.tickets_tree.get_children():
            self.tickets_tree.delete(item)
        self.ticket_urls = {}
        
        if not insight.tickets:
            return
        
        for ticket in insight.tickets[:50]:  # Limit to 50
            # Extract ticket number from URL (e.g., "https://a8c.zendesk.com/agent/tickets/10452479")
            ticket_url = ticket.ticket_id or ''
            ticket_num = ticket_url.split('/')[-1] if '/' in ticket_url else ticket_url
            
            date_str = ticket.created_date.strftime('%Y-%m-%d') if ticket.created_date else 'N/A'
            summary = ticket.detail_summary[:80] + '...' if ticket.detail_summary and len(ticket.detail_summary) > 80 else (ticket.detail_summary or 'N/A')
            
            item_id = self.tickets_tree.insert('', 'end', values=(
                ticket_num,
                date_str,
                ticket.sentiment or 'N/A',
                summary
            ))
            
            # Store URL for this item
            self.ticket_urls[item_id] = ticket_url
    
    def _on_ticket_double_click(self, event):
        """Handle double-click on a ticket to open in browser."""
        import webbrowser
        
        selection = self.tickets_tree.selection()
        if selection:
            item_id = selection[0]
            url = self.ticket_urls.get(item_id)
            if url and url.startswith('http'):
                webbrowser.open(url)
            else:
                from tkinter import messagebox
                messagebox.showinfo("Info", f"No valid URL for this ticket: {url}")
    
    def _draw_trend_chart(self, insight: ProductInsight):
        """Draw trend chart for the insight."""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        self.trend_ax.clear()
        
        # Simple placeholder - in production, query actual time series data
        if insight.first_seen and insight.last_seen:
            days = (insight.last_seen - insight.first_seen).days
            if days > 0:
                # Simulate trend data
                x = range(min(days + 1, 30))
                y = [insight.ticket_count // max(len(x), 1) for _ in x]
                
                self.trend_ax.plot(x, y, color=self.COLORS.get(insight.insight_type, '#333'))
                self.trend_ax.fill_between(x, y, alpha=0.3)
                self.trend_ax.set_title('Ticket Volume Over Time')
                self.trend_ax.set_xlabel('Days')
                self.trend_ax.set_ylabel('Tickets')
            else:
                self.trend_ax.text(0.5, 0.5, 'Not enough data for trend',
                                  ha='center', va='center', transform=self.trend_ax.transAxes)
        else:
            self.trend_ax.text(0.5, 0.5, 'No date range available',
                              ha='center', va='center', transform=self.trend_ax.transAxes)
        
        self.trend_canvas.draw()
    
    def _update_insight_status(self, new_status: InsightStatus):
        """Update status of selected insight."""
        if not self.selected_insight_id:
            messagebox.showwarning("Warning", "Please select an insight first")
            return
        
        try:
            self.insights_store.update_insight_status(
                self.selected_insight_id,
                new_status
            )
            self.refresh_insights()
            self._load_insight_details(self.selected_insight_id)
            messagebox.showinfo("Success", f"Status updated to {new_status.value}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update status: {e}")
    
    def _extract_new_insights(self):
        """Extract new insights from recent tickets."""
        if not self.extractor:
            messagebox.showerror("Error", "Insight extractor not available")
            return
        
        # Ask for date range
        days = 30  # Default to 30 days
        
        def run_extraction():
            try:
                end_date = date.today()
                start_date = end_date - timedelta(days=days)
                
                result = self.extractor.extract_insights_from_batch(
                    start_date=start_date,
                    end_date=end_date
                )
                
                self.data_queue.put(('extraction_complete', result))
            except Exception as e:
                self.data_queue.put(('extraction_error', str(e)))
        
        # Run in background
        messagebox.showinfo("Info", f"Extracting insights from the last {days} days...\nThis may take a moment.")
        threading.Thread(target=run_extraction, daemon=True).start()
        self.after(500, self._check_extraction_result)
    
    def _check_extraction_result(self):
        """Check for extraction result."""
        try:
            msg_type, result = self.data_queue.get_nowait()
            if msg_type == 'extraction_complete':
                messagebox.showinfo("Extraction Complete", 
                    f"Processed {result['feedback_count']} feedback items\n"
                    f"Created {result['insights_created']} new insights")
                self.refresh_insights()
            elif msg_type == 'extraction_error':
                messagebox.showerror("Error", f"Extraction failed: {result}")
        except queue.Empty:
            self.after(500, self._check_extraction_result)
    
    def _update_trends(self):
        """Update trend data for all insights."""
        if not self.extractor:
            messagebox.showerror("Error", "Insight extractor not available")
            return
        
        try:
            updated = self.extractor.update_insight_trends()
            self.refresh_insights()
            messagebox.showinfo("Success", f"Updated trends for {updated} insights")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update trends: {e}")
    
    def _export_insights(self, format_type: str):
        """Export insights to the specified format."""
        from tkinter import filedialog
        from datetime import datetime
        
        try:
            from insight_exporter import get_insight_exporter
            exporter = get_insight_exporter()
            
            # Get current filters
            insight_type = None if self.filter_type.get() == "All" else self.filter_type.get()
            product_area = None if self.filter_area.get() == "All" else self.filter_area.get()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if format_type == 'csv':
                default_name = f"product_insights_{timestamp}.csv"
                filetypes = [("CSV files", "*.csv")]
            elif format_type == 'markdown':
                default_name = f"product_insights_{timestamp}.md"
                filetypes = [("Markdown files", "*.md")]
            elif format_type == 'jira':
                default_name = f"product_insights_jira_{timestamp}.json"
                filetypes = [("JSON files", "*.json")]
            else:
                return
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=filetypes[0][1].replace('*', ''),
                filetypes=filetypes,
                initialfile=default_name,
                title=f"Export Insights to {format_type.upper()}"
            )
            
            if not file_path:
                return
            
            if format_type == 'csv':
                exporter.export_to_csv(file_path, 
                                       insight_type=insight_type if insight_type else None,
                                       product_area=product_area)
            elif format_type == 'markdown':
                exporter.export_to_markdown(file_path,
                                            title="Product Insights Report",
                                            insight_type=insight_type if insight_type else None,
                                            product_area=product_area)
            elif format_type == 'jira':
                exporter.export_to_jira_format(file_path,
                                               insight_type=insight_type if insight_type else None)
            
            messagebox.showinfo("Export Complete", f"Insights exported to:\n{file_path}")
            
        except ImportError:
            messagebox.showerror("Error", "Export module not available")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")
    
    def _generate_weekly_digest(self):
        """Generate and display weekly digest."""
        from tkinter import filedialog
        from datetime import datetime
        
        try:
            from insight_exporter import get_insight_exporter
            exporter = get_insight_exporter()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_name = f"weekly_digest_{timestamp}.md"
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".md",
                filetypes=[("Markdown files", "*.md")],
                initialfile=default_name,
                title="Save Weekly Digest"
            )
            
            if not file_path:
                return
            
            content = exporter.generate_weekly_digest(file_path)
            
            # Show preview
            preview_window = tk.Toplevel(self)
            preview_window.title("Weekly Digest Preview")
            preview_window.geometry("700x500")
            
            text = scrolledtext.ScrolledText(preview_window, wrap=tk.WORD)
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert(tk.END, content)
            text.configure(state='disabled')
            
            messagebox.showinfo("Digest Generated", f"Weekly digest saved to:\n{file_path}")
            
        except ImportError:
            messagebox.showerror("Error", "Export module not available")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate digest: {e}")


class InsightsWindow(tk.Toplevel):
    """Standalone window for the insights dashboard."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Product Insights Dashboard")
        self.geometry("1300x800")
        
        # Make window modal
        self.transient(parent)
        self.grab_set()
        
        # Create dashboard
        self.dashboard = InsightsDashboard(self)
        self.dashboard.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")


def open_insights_dashboard(parent) -> Optional[InsightsWindow]:
    """
    Open the insights dashboard window.
    
    Args:
        parent: Parent Tkinter window
        
    Returns:
        InsightsWindow instance or None if unavailable
    """
    if not INSIGHTS_AVAILABLE:
        messagebox.showerror(
            "Feature Unavailable",
            "Product insights modules are not available.\n\n"
            "Please ensure all required modules are installed."
        )
        return None
    
    return InsightsWindow(parent)


if __name__ == '__main__':
    # Test the dashboard standalone
    root = tk.Tk()
    root.withdraw()
    
    window = InsightsWindow(root)
    window.protocol("WM_DELETE_WINDOW", root.destroy)
    
    root.mainloop()
