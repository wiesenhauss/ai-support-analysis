#!/usr/bin/env python3
"""
Talk to Data - AI-Powered CSV Analysis
Interactive data analysis using AI for Automattic Inc support data

Author: @wiesenhauss
Created: 2025-01-09
"""

import os
import sys
import json
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime
import threading
import openai
from pathlib import Path


# Column metadata for intelligent selection
COLUMN_METADATA = {
    "Created Date": {
        "description": "Date/Time values for trend analysis and temporal patterns",
        "use_cases": ["trends", "time analysis", "temporal patterns", "seasonal analysis"],
        "data_size": "small",
        "priority": "high"
    },
    "Zendesk Ticket URL": {
        "description": "URLs of support tickets for collecting examples",
        "use_cases": ["examples", "ticket references", "specific cases"],
        "data_size": "small",
        "priority": "low"
    },
    "Tags": {
        "description": "Zendesk tags, useful when specifically requested",
        "use_cases": ["categorization", "specific tag analysis"],
        "data_size": "small",
        "priority": "low"
    },
    "Description": {
        "description": "Ticket titles, useful when specifically requested",
        "use_cases": ["title analysis", "issue categorization"],
        "data_size": "small",
        "priority": "low"
    },
    "Interaction Message Body": {
        "description": "Full text content - avoid due to size limitations",
        "use_cases": ["detailed content analysis", "specific text search"],
        "data_size": "very_large",
        "priority": "very_low"
    },
    "CSAT Rating Date": {
        "description": "Date/Time when CSAT rating was given",
        "use_cases": ["CSAT timing analysis", "rating trends"],
        "data_size": "small",
        "priority": "medium"
    },
    "CSAT Rating": {
        "description": "Customer satisfaction rating (good/bad)",
        "use_cases": ["satisfaction analysis", "rating distribution"],
        "data_size": "small",
        "priority": "high"
    },
    "CSAT Reason": {
        "description": "Reason for CSAT rating - usually not very useful",
        "use_cases": ["rating reasoning"],
        "data_size": "medium",
        "priority": "low"
    },
    "CSAT Comment": {
        "description": "Customer comments with CSAT - very valuable when present",
        "use_cases": ["customer feedback", "satisfaction insights"],
        "data_size": "medium",
        "priority": "very_high"
    },
    "First reply time without AI (hours)": {
        "description": "Response time metrics in hours",
        "use_cases": ["performance analysis", "response time trends"],
        "data_size": "small",
        "priority": "high"
    },
    "Status": {
        "description": "Ticket status (open, closed, pending, solved)",
        "use_cases": ["status analysis", "resolution tracking"],
        "data_size": "small",
        "priority": "medium"
    },
    "Total time spent (mins)": {
        "description": "Total agent time spent on ticket",
        "use_cases": ["efficiency analysis", "workload assessment"],
        "data_size": "small",
        "priority": "high"
    },
    "DETAIL_SUMMARY": {
        "description": "AI-generated summary of the interaction",
        "use_cases": ["content analysis", "issue understanding"],
        "data_size": "medium",
        "priority": "very_high"
    },
    "CUSTOMER_GOAL": {
        "description": "AI-generated summary of customer's main goal",
        "use_cases": ["goal analysis", "customer intent"],
        "data_size": "small",
        "priority": "very_high"
    },
    "SENTIMENT_ANALYSIS": {
        "description": "Overall sentiment (Negative, Neutral, Positive)",
        "use_cases": ["sentiment trends", "satisfaction analysis"],
        "data_size": "small",
        "priority": "very_high"
    },
    "WHAT_HAPPENED": {
        "description": "AI analysis of issues or positive aspects",
        "use_cases": ["issue identification", "experience analysis"],
        "data_size": "medium",
        "priority": "very_high"
    },
    "ISSUE_RESOLVED": {
        "description": "Boolean assessment of issue resolution",
        "use_cases": ["resolution analysis", "success metrics"],
        "data_size": "small",
        "priority": "high"
    },
    "INTERACTION_TOPICS": {
        "description": "AI-generated list of main topics discussed",
        "use_cases": ["topic analysis", "categorization"],
        "data_size": "medium",
        "priority": "high"
    },
    "PRODUCT_FEEDBACK": {
        "description": "AI-generated product feedback with customer quotes",
        "use_cases": ["product insights", "feature requests"],
        "data_size": "medium",
        "priority": "very_high"
    },
    "RELATED_TO_PRODUCT": {
        "description": "Boolean for product-related issues",
        "use_cases": ["product issue analysis", "categorization"],
        "data_size": "small",
        "priority": "high"
    },
    "RELATED_TO_SERVICE": {
        "description": "Boolean for service-related issues",
        "use_cases": ["service quality analysis", "support assessment"],
        "data_size": "small",
        "priority": "high"
    },
    "INITIAL_SENTIMENT": {
        "description": "Initial sentiment (less relevant than SENTIMENT_ANALYSIS)",
        "use_cases": ["sentiment comparison", "initial vs overall"],
        "data_size": "small",
        "priority": "low"
    },
    "PREDICTED_CSAT": {
        "description": "AI-predicted CSAT rating",
        "use_cases": ["prediction analysis", "satisfaction modeling"],
        "data_size": "small",
        "priority": "medium"
    },
    "PREDICTED_CSAT_ACCURATE": {
        "description": "Accuracy comparison of predicted vs actual CSAT",
        "use_cases": ["model accuracy assessment"],
        "data_size": "small",
        "priority": "low"
    }
}

class TalkToDataWindow:
    def __init__(self, parent, csv_file_path, api_key, dataframe=None, data_source_name=None):
        """
        Initialize Talk to Data window.
        
        Args:
            parent: Parent Tkinter window
            csv_file_path: Path to CSV file (can be None if dataframe is provided)
            api_key: OpenAI API key
            dataframe: Optional pre-loaded DataFrame (for historical data mode)
            data_source_name: Optional name for the data source (used when dataframe is provided)
        """
        self.parent = parent
        self.csv_file_path = csv_file_path
        self.api_key = api_key
        self.df = dataframe  # Can be pre-loaded
        self.data_source_name = data_source_name  # For display purposes
        self.is_historical_mode = dataframe is not None
        self.selected_columns = []
        self.analysis_result = ""
        
        # Conversation management
        self.conversation_history = []  # Working history for AI context (may be summarized)
        self.full_conversation_history = []  # Complete history for saving (never truncated)
        self.current_context_columns = []
        self.conversation_summary = ""
        self.max_history_length = 3  # Keep last 3 exchanges + summary
        self.is_follow_up = False
        
        # Token counting setup
        self.MAX_TOKENS = 1000000  # 1 million token limit
        self.CHUNK_TOKEN_LIMIT = int(self.MAX_TOKENS * 0.7)  # 70% of context window for chunks

        self.current_token_count = 0
        
        # Chunked processing state
        self.chunk_results = []
        self.chunk_progress_file = None
        self.is_chunked_processing = False
        self.current_chunk = 0
        self.total_chunks = 0
        
        # Load and validate data (CSV or pre-loaded DataFrame)
        if not self.load_and_validate_data():
            return
            
        self.setup_window()
        self.setup_ui()
        
        # Initialize token counting (using estimation method)
        self.log_message("📊 Token counting initialized (using estimation method)")
        
    def load_and_validate_data(self):
        """Load and validate data from CSV or pre-loaded DataFrame"""
        try:
            # If DataFrame was provided, use it directly
            if self.df is not None:
                if self.df.empty:
                    messagebox.showerror("Error", "The provided data is empty.")
                    return False
                return True
            
            # Otherwise load from CSV
            self.df = pd.read_csv(self.csv_file_path)
            
            if self.df.empty:
                messagebox.showerror("Error", "The CSV file is empty.")
                return False
                
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV file:\n{str(e)}")
            return False
    
    def setup_window(self):
        """Create and configure the popup window"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Talk to Your Data - AI Analysis")
        self.window.geometry("900x900")
        self.window.resizable(True, True)
        
        # Center the window
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Configure grid weights
        self.window.grid_rowconfigure(4, weight=1)  # Log area
        self.window.grid_rowconfigure(5, weight=2)  # Results area
        self.window.grid_columnconfigure(0, weight=1)
        
    def setup_ui(self):
        """Create the user interface"""
        # Title
        title_label = tk.Label(
            self.window, 
            text="Talk to Your Data - AI Analysis", 
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, pady=(10, 5), sticky="ew")
        
        # Dataset info
        if self.is_historical_mode:
            source_name = self.data_source_name or "Historical Database"
            info_text = f"📊 Data Source: {source_name} ({len(self.df):,} tickets)"
        else:
            info_text = f"Dataset: {os.path.basename(self.csv_file_path)} ({len(self.df):,} rows)"
        info_label = tk.Label(self.window, text=info_text, font=("Arial", 10))
        info_label.grid(row=1, column=0, pady=(0, 10), sticky="ew")
        
        # Question frame
        question_frame = ttk.LabelFrame(self.window, text="Your Question", padding="10")
        question_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        question_frame.grid_columnconfigure(0, weight=1)
        
        self.question_text = tk.Text(question_frame, height=3, wrap=tk.WORD)
        self.question_text.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Question buttons
        question_btn_frame = tk.Frame(question_frame)
        question_btn_frame.grid(row=1, column=0, sticky="ew")
        
        self.analyze_btn = ttk.Button(
            question_btn_frame, 
            text="🔍 Analyze Question", 
            command=self.analyze_question
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Follow-up button (initially hidden)
        self.followup_btn = ttk.Button(
            question_btn_frame,
            text="💬 Ask Follow-up",
            command=self.ask_followup_question
        )
        self.followup_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.followup_btn.pack_forget()  # Hide initially
        
        ttk.Button(
            question_btn_frame, 
            text="Clear", 
            command=lambda: self.question_text.delete(1.0, tk.END)
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        # New conversation button
        self.new_conversation_btn = ttk.Button(
            question_btn_frame,
            text="🆕 New Conversation",
            command=self.start_new_conversation
        )
        self.new_conversation_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.new_conversation_btn.pack_forget()  # Hide initially
        
        # Example questions
        examples_btn = ttk.Button(
            question_btn_frame,
            text="💡 Examples",
            command=self.show_example_questions
        )
        examples_btn.pack(side=tk.RIGHT)
        
        # Column selection frame (initially hidden)
        self.column_frame = ttk.LabelFrame(self.window, text="Column Selection", padding="10")
        self.column_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.column_frame.grid_columnconfigure(0, weight=1)
        self.column_frame.grid_remove()  # Hide initially
        
        # AI reasoning display
        self.reasoning_text = tk.Text(self.column_frame, height=2, wrap=tk.WORD, state=tk.DISABLED, font=("Arial", 9))
        self.reasoning_text.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Scrollable column selection
        canvas = tk.Canvas(self.column_frame, height=120)
        scrollbar = ttk.Scrollbar(self.column_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 10))
        
        # Column selection buttons
        col_btn_frame = tk.Frame(self.column_frame)
        col_btn_frame.grid(row=2, column=0, sticky="ew")
        
        self.proceed_btn = ttk.Button(
            col_btn_frame,
            text="🚀 Proceed with Analysis",
            command=self.proceed_with_analysis,
            state=tk.DISABLED
        )
        self.proceed_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        ttk.Button(
            col_btn_frame,
            text="Cancel",
            command=self.cancel_column_selection
        ).pack(side=tk.RIGHT)
        
        # Log frame
        log_frame = ttk.LabelFrame(self.window, text="Analysis Log", padding="10")
        log_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=8,
            wrap=tk.WORD, 
            state=tk.DISABLED,
            font=("Consolas", 12)
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        # Results frame - now shows conversation history
        results_frame = ttk.LabelFrame(self.window, text="Conversation", padding="10")
        results_frame.grid(row=5, column=0, sticky="nsew", padx=10, pady=(0, 10))
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        
        self.results_text = scrolledtext.ScrolledText(
            results_frame, 
            wrap=tk.WORD, 
            state=tk.DISABLED,
            font=("Arial", 12)
        )
        self.results_text.grid(row=0, column=0, sticky="nsew")
        
        # Configure text tags for conversation formatting
        self.results_text.tag_configure("user_question", foreground="blue", font=("Arial", 12, "bold"))
        self.results_text.tag_configure("ai_response", foreground="black", font=("Arial", 12))
        self.results_text.tag_configure("system_message", foreground="gray", font=("Arial", 11, "italic"))
        self.results_text.tag_configure("separator", foreground="lightgray")
        
        # Status and action buttons
        bottom_frame = tk.Frame(self.window)
        bottom_frame.grid(row=6, column=0, sticky="ew", padx=10, pady=(0, 10))
        bottom_frame.grid_columnconfigure(1, weight=1)
        
        # Status and token counter
        status_frame = tk.Frame(bottom_frame)
        status_frame.grid(row=0, column=0, sticky="w")
        
        self.status_label = tk.Label(status_frame, text="Ready", font=("Arial", 10))
        self.status_label.pack(side=tk.LEFT)
        
        # Token counter
        self.token_frame = tk.Frame(status_frame)
        self.token_frame.pack(side=tk.LEFT, padx=(20, 0))
        
        tk.Label(self.token_frame, text="Tokens:", font=("Arial", 9)).pack(side=tk.LEFT)
        self.token_label = tk.Label(
            self.token_frame, 
            text="0 / 1,000,000", 
            font=("Arial", 9, "bold"),
            fg="green"
        )
        self.token_label.pack(side=tk.LEFT, padx=(5, 0))
        
        button_frame = tk.Frame(bottom_frame)
        button_frame.grid(row=0, column=2, sticky="e")
        
        self.save_btn = ttk.Button(
            button_frame, 
            text="💾 Save Conversation", 
            command=self.save_results,
            state=tk.DISABLED
        )
        self.save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame, 
            text="Close", 
            command=self.window.destroy
        ).pack(side=tk.LEFT)
        
        # Initialize token counter first (before logging)
        self.update_token_counter(0)
        
        # Initialize logging
        self.log_message("💬 Talk to Data ready - enter your question above")
        self.log_message("🆕 This is a conversational interface - ask follow-up questions after initial analysis!")
    
    def count_tokens(self, text):
        """Count tokens in text using estimation method"""
        if not text:
            return 0
        return self._estimate_tokens(text)
    
    def _estimate_tokens(self, text):
        """Token estimation based on OpenAI's general guidelines"""
        # More accurate estimation based on OpenAI's general guidelines
        # Average of ~4 characters per token for English text
        char_count = len(text)
        word_count = len(text.split())
        
        # Use character-based estimation (more conservative)
        char_based = char_count / 4
        
        # Use word-based estimation with multiplier
        word_based = word_count * 1.3
        
        # Take the higher estimate for safety
        return int(max(char_based, word_based))
    
    def update_token_counter(self, token_count):
        """Update the token counter display"""
        self.current_token_count = token_count
        
        # Calculate percentage and color
        percentage = (token_count / self.MAX_TOKENS) * 100
        
        if percentage < 50:
            color = "#28a745"  # Green
            status = "Good"
        elif percentage < 80:
            color = "#ffc107"  # Yellow
            status = "Moderate"
        else:
            color = "#dc3545"  # Red
            status = "High"
        
        # Update display
        self.token_label.config(
            text=f"{token_count:,} / {self.MAX_TOKENS:,} ({percentage:.1f}%) - {status}",
            fg=color
        )
        
        # Update progress bar
        # self.token_progress.config(value=percentage) # This line was not in the new_code, so it's removed.
        
        # Change progress bar color based on usage
        style = ttk.Style()
        if percentage < 50:
            style.configure("Token.Horizontal.TProgressbar", background="#28a745")
        elif percentage < 80:
            style.configure("Token.Horizontal.TProgressbar", background="#ffc107")
        else:
            style.configure("Token.Horizontal.TProgressbar", background="#dc3545")

    def _check_if_chunking_needed(self, question, selected_columns, sample_size):
        """Check if chunking is needed based on token estimation"""
        estimated_tokens = self.estimate_prompt_tokens(question, selected_columns, sample_size)
        return estimated_tokens > self.MAX_TOKENS * 0.95  # 95% safety margin

    def _show_chunking_dialog(self, question, selected_columns, estimated_tokens, total_rows):
        """Show dialog asking user to choose between row reduction or chunking"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Large Dataset Processing Options")
        dialog.geometry("650x500")
        dialog.resizable(True, True)  # Allow resizing
        dialog.minsize(650, 500)  # Minimum size to ensure buttons are visible
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (650 // 2)
        y = (dialog.winfo_screenheight() // 2) - (500 // 2)
        dialog.geometry(f"650x500+{x}+{y}")
        
        # Main content frame
        content_frame = ttk.Frame(dialog)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Title
        title_label = ttk.Label(content_frame, text="Dataset Too Large for Single Analysis", 
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 15))
        
        # Information
        info_text = f"""Your dataset is too large to process in a single analysis.

Dataset Information:
• Total rows: {total_rows:,}
• Estimated tokens: {estimated_tokens:,}
• Token limit: {self.MAX_TOKENS:,}

You have two options:"""
        
        info_label = ttk.Label(content_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(pady=(0, 15), anchor="w")
        
        # Calculate chunks for display
        rows_per_chunk = 500  # Starting chunk size
        estimated_chunks = max(1, (total_rows + rows_per_chunk - 1) // rows_per_chunk)
        
        # Options frame
        options_frame = ttk.Frame(content_frame)
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Option A: Reduce rows
        option_a_frame = ttk.LabelFrame(options_frame, text="Option A: Reduce Dataset Size", padding="8")
        option_a_frame.pack(fill=tk.X, pady=(0, 8))
        
        reduced_rows = min(1000, total_rows)
        option_a_text = f"• Analyze a random sample of {reduced_rows:,} rows\n• Faster processing (~2-3 minutes)\n• Single comprehensive analysis\n• May miss some patterns in excluded data"
        ttk.Label(option_a_frame, text=option_a_text, justify=tk.LEFT).pack(anchor="w")
        
        # Option B: Chunked processing
        option_b_frame = ttk.LabelFrame(options_frame, text="Option B: Process All Data in Chunks", padding="8")
        option_b_frame.pack(fill=tk.X)
        
        option_b_text = f"• Process all {total_rows:,} rows in approximately {estimated_chunks} chunks\n• Slower processing (3x to 10x more time)\n• Complete analysis of all data\n• AI will combine findings from all chunks"
        ttk.Label(option_b_frame, text=option_b_text, justify=tk.LEFT).pack(anchor="w")
        
        # Separator
        separator = ttk.Separator(content_frame, orient='horizontal')
        separator.pack(fill="x", pady=(15, 10))
        
        # Buttons frame at bottom
        buttons_frame = ttk.Frame(content_frame)
        buttons_frame.pack(fill="x", pady=(5, 0))
        
        # User choice variable
        user_choice = tk.StringVar()
        
        def choose_reduce():
            user_choice.set("reduce")
            dialog.destroy()
        
        def choose_chunk():
            user_choice.set("chunk")
            dialog.destroy()
        
        def cancel():
            user_choice.set("cancel")
            dialog.destroy()
        
        # Buttons - better layout and styling
        reduce_btn = ttk.Button(buttons_frame, text=f"Reduce to {reduced_rows:,} rows", 
                               command=choose_reduce)
        reduce_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        chunk_btn = ttk.Button(buttons_frame, text="Process all data in chunks", 
                              command=choose_chunk)
        chunk_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_btn = ttk.Button(buttons_frame, text="Cancel", command=cancel)
        cancel_btn.pack(side=tk.RIGHT)
        
        # Set default focus to the reduce button (most common choice)
        reduce_btn.focus_set()
        
        # Add keyboard shortcuts
        def handle_key(event):
            if event.keysym == 'Return' or event.keysym == 'KP_Enter':
                # Enter key defaults to reduce option
                choose_reduce()
            elif event.keysym == 'Escape':
                # Escape key cancels
                cancel()
            elif event.char.lower() == 'r':
                # 'R' for reduce
                choose_reduce()
            elif event.char.lower() == 'c' and event.state == 0:  # 'C' for chunk (not Ctrl+C)
                choose_chunk()
        
        dialog.bind('<Key>', handle_key)
        dialog.focus_set()  # Ensure dialog can receive key events
        
        # Wait for user choice
        dialog.wait_window()
        return user_choice.get()

    def _create_progress_file(self, question, selected_columns, total_rows):
        """Create a progress file to track chunked processing"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"temporary-chunk-analysis-{timestamp}.json"
        
        # Save to same directory as input CSV
        input_dir = os.path.dirname(self.csv_file_path)
        progress_file_path = os.path.join(input_dir, filename)
        
        progress_data = {
            "timestamp": timestamp,
            "question": question,
            "selected_columns": selected_columns,
            "total_rows": total_rows,
            "chunks_completed": 0,
            "total_chunks": 0,
            "chunk_results": [],
            "processing_state": "initialized",
            "csv_file": self.csv_file_path
        }
        
        with open(progress_file_path, 'w') as f:
            json.dump(progress_data, f, indent=2)
        
        self.chunk_progress_file = progress_file_path
        return progress_file_path

    def _save_progress(self, chunk_results=None, processing_state="in_progress"):
        """Save current progress to file"""
        if not self.chunk_progress_file:
            return
        
        try:
            with open(self.chunk_progress_file, 'r') as f:
                progress_data = json.load(f)
            
            progress_data["chunks_completed"] = self.current_chunk
            progress_data["total_chunks"] = self.total_chunks
            progress_data["processing_state"] = processing_state
            
            if chunk_results:
                progress_data["chunk_results"] = chunk_results
            
            with open(self.chunk_progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
                
        except Exception as e:
            self.log_message(f"⚠️ Warning: Could not save progress: {str(e)}")

    def _cleanup_progress_file(self):
        """Clean up the progress file after successful completion"""
        if self.chunk_progress_file and os.path.exists(self.chunk_progress_file):
            try:
                os.remove(self.chunk_progress_file)
                self.log_message("🧹 Cleaned up temporary progress file")
            except Exception as e:
                self.log_message(f"⚠️ Could not clean up progress file: {str(e)}")

    def _perform_chunked_analysis(self, question, selected_columns, analysis_result):
        """Perform chunked analysis of the dataset"""
        try:
            self.is_chunked_processing = True
            self.chunk_results = []
            
            # Create progress file
            progress_file = self._create_progress_file(question, selected_columns, len(self.df))
            self.log_message(f"📁 Created progress file: {os.path.basename(progress_file)}")
            
            # Calculate chunks
            rows_per_chunk = 500  # Starting chunk size
            total_rows = len(self.df)
            chunks = []
            
            for start_idx in range(0, total_rows, rows_per_chunk):
                end_idx = min(start_idx + rows_per_chunk, total_rows)
                chunks.append((start_idx, end_idx))
            
            self.total_chunks = len(chunks)
            self.log_message(f"📊 Will process {total_rows:,} rows in {self.total_chunks} chunks")
            
            # Update UI
            self.window.after(0, lambda: self.status_label.config(text=f"Processing chunk 1 of {self.total_chunks}..."))
            
            # Process each chunk
            for chunk_idx, (start_idx, end_idx) in enumerate(chunks):
                self.current_chunk = chunk_idx + 1
                chunk_rows = end_idx - start_idx
                
                self.window.after(0, lambda c=self.current_chunk, t=self.total_chunks: 
                                self.log_message(f"🔄 Processing chunk {c} of {t} (rows {start_idx+1}-{end_idx})..."))
                
                # Extract chunk data
                chunk_df = self.df.iloc[start_idx:end_idx][selected_columns].copy()
                
                # Process chunk with retry logic
                chunk_result = self._process_single_chunk(chunk_df, question, chunk_idx + 1, selected_columns)
                
                if chunk_result:
                    self.chunk_results.append({
                        "chunk_number": chunk_idx + 1,
                        "rows_processed": chunk_rows,
                        "start_row": start_idx + 1,
                        "end_row": end_idx,
                        "result": chunk_result
                    })
                    
                    # Save progress after each successful chunk
                    self._save_progress(self.chunk_results, "in_progress")
                    
                    self.window.after(0, lambda c=self.current_chunk, t=self.total_chunks: 
                                    self.status_label.config(text=f"Completed chunk {c} of {t}"))
                else:
                    # Chunk failed, but continue with partial results
                    self.window.after(0, lambda c=self.current_chunk: 
                                    self.log_message(f"❌ Chunk {c} failed, continuing with partial results"))
            
            # Combine results
            if self.chunk_results:
                self.window.after(0, lambda: self.log_message("🔄 Combining findings from all chunks..."))
                self.window.after(0, lambda: self.status_label.config(text="Combining findings..."))
                
                combined_result = self._combine_chunk_results(question, selected_columns)
                
                if combined_result:
                    # Save final progress
                    self._save_progress(self.chunk_results, "completed")
                    
                    # Display results
                    self._display_chunked_results(combined_result, question, selected_columns)
                    
                    # Clean up
                    self._cleanup_progress_file()
                    
                    self.window.after(0, lambda: self.log_message("✅ Chunked analysis completed successfully!"))
                else:
                    raise Exception("Failed to combine chunk results")
            else:
                raise Exception("No chunks processed successfully")
                
        except Exception as e:
            # Save partial results
            if self.chunk_results:
                self._save_progress(self.chunk_results, "partial_failure")
                self.window.after(0, lambda: self.log_message(f"⚠️ Partial results saved to progress file"))
            
            self.window.after(0, lambda: self._handle_analysis_error(f"Chunked analysis failed: {str(e)}"))
        finally:
            self.is_chunked_processing = False
            self.window.after(0, self._enable_buttons)

    def _process_single_chunk(self, chunk_df, question, chunk_number, selected_columns):
        """Process a single chunk with retry logic"""
        try:
            # Convert to CSV
            csv_data = chunk_df.to_csv(index=False)
            
            # Estimate tokens
            prompt_tokens = self.count_tokens(f"""You are analyzing a chunk of WordPress.com support data.

This is chunk {chunk_number} of a larger dataset analysis.

Question: {question}
Columns: {', '.join(selected_columns)}
Rows in this chunk: {len(chunk_df)}

Data:
""")
            data_tokens = self.count_tokens(csv_data)
            total_tokens = prompt_tokens + data_tokens
            
            # Check if chunk fits in token limit
            if total_tokens > self.CHUNK_TOKEN_LIMIT:
                self.window.after(0, lambda: self.log_message(f"⚠️ Chunk {chunk_number} too large ({total_tokens:,} tokens), reducing size..."))
                
                # Reduce chunk size
                max_rows = int(len(chunk_df) * 0.7)  # Reduce by 30%
                if max_rows < 10:  # Minimum viable chunk
                    raise Exception(f"Chunk {chunk_number} cannot be reduced further")
                
                chunk_df = chunk_df.sample(n=max_rows, random_state=42)
                csv_data = chunk_df.to_csv(index=False)
                data_tokens = self.count_tokens(csv_data)
                total_tokens = prompt_tokens + data_tokens
            
            # Create chunk analysis prompt
            chunk_prompt = f"""You are analyzing chunk {chunk_number} of a larger WordPress.com support dataset.

Question: {question}

Dataset Context:
- This is chunk {chunk_number} of a multi-chunk analysis
- Rows in this chunk: {len(chunk_df):,}
- Columns: {', '.join(selected_columns)}

Data (CSV format):
{csv_data}

Provide a focused analysis of this chunk that includes:
1. Key findings specific to this data subset
2. Notable patterns or trends
3. Specific examples or data points
4. Any unique insights from this chunk

Keep the response concise but informative - this will be combined with other chunks later."""

            # Make API call
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": chunk_prompt}],
                temperature=0.3,
                max_tokens=2000
            )
            
            result = self._parse_api_response(response, f"Chunk {chunk_number} analysis")
            self.window.after(0, lambda: self.log_message(f"✅ Chunk {chunk_number} processed successfully"))
            
            return result
            
        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"❌ Chunk {chunk_number} failed: {str(e)}"))
            return None

    def _combine_chunk_results(self, question, selected_columns):
        """Combine results from all chunks using AI"""
        try:
            # Prepare chunk results for combination
            chunk_summaries = []
            total_rows_processed = 0
            
            for chunk_data in self.chunk_results:
                chunk_summaries.append(f"CHUNK {chunk_data['chunk_number']} (rows {chunk_data['start_row']}-{chunk_data['end_row']}):\n{chunk_data['result']}")
                total_rows_processed += chunk_data['rows_processed']
            
            # Create aggregation prompt
            aggregation_prompt = f"""You are analyzing results from multiple data chunks. Your task is to combine findings from {len(self.chunk_results)} separate analyses into one comprehensive report.

Original Question: {question}
Total Rows Processed: {total_rows_processed:,}
Columns Analyzed: {', '.join(selected_columns)}

CHUNK RESULTS:
{chr(10).join(chunk_summaries)}

Please synthesize these findings into a unified analysis that:
1. Identifies overarching patterns across all chunks
2. Reconciles any conflicting findings
3. Provides comprehensive statistics
4. Highlights the most significant insights
5. Notes any limitations from the chunked approach

Format your response as a comprehensive analysis report."""

            # Make API call to combine results
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": aggregation_prompt}],
                temperature=0.3,
                max_tokens=4000
            )
            
            combined_result = self._parse_api_response(response, "Chunk combination")
            return combined_result
            
        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"❌ Failed to combine chunk results: {str(e)}"))
            return None

    def _display_chunked_results(self, combined_result, question, selected_columns):
        """Display results from chunked analysis"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total_rows_processed = sum(chunk['rows_processed'] for chunk in self.chunk_results)
            
            final_result = f"""# Talk to Data Analysis Results (Chunked Processing)
**Generated:** {timestamp}

## Question Asked
{question}

## Columns Analyzed
{', '.join(selected_columns)}

## Dataset Information
- **Total rows processed:** {total_rows_processed:,}
- **Processing method:** Chunked analysis ({len(self.chunk_results)} chunks)
- **Chunks completed:** {len(self.chunk_results)} of {self.total_chunks}

## Analysis Results

{combined_result}

---

### Processing Details
- **Chunks processed:** {len(self.chunk_results)}
- **Average rows per chunk:** {total_rows_processed // len(self.chunk_results):,}
- **Processing method:** Multi-chunk analysis with AI aggregation
"""

            # Display results
            self._display_results(final_result, question, selected_columns, total_rows_processed)
            
            # Add to conversation
            self.add_to_conversation("ai_response", combined_result, {
                "processing_method": "chunked",
                "chunks_processed": len(self.chunk_results),
                "total_chunks": self.total_chunks,
                "rows_analyzed": total_rows_processed,
                "columns_used": selected_columns
            })
            
        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"❌ Failed to display chunked results: {str(e)}"))
            raise e

    def _perform_chunked_followup_analysis(self, question, columns, analysis):
        """Perform chunked follow-up analysis"""
        try:
            self.is_chunked_processing = True
            self.chunk_results = []
            
            # Get conversation context
            conversation_context = self.get_conversation_context()
            
            # Create progress file
            progress_file = self._create_progress_file(f"Follow-up: {question}", columns, len(self.df))
            self.log_message(f"📁 Created follow-up progress file: {os.path.basename(progress_file)}")
            
            # Calculate chunks
            rows_per_chunk = 500  # Starting chunk size
            total_rows = len(self.df)
            chunks = []
            
            for start_idx in range(0, total_rows, rows_per_chunk):
                end_idx = min(start_idx + rows_per_chunk, total_rows)
                chunks.append((start_idx, end_idx))
            
            self.total_chunks = len(chunks)
            self.log_message(f"📊 Will process {total_rows:,} rows in {self.total_chunks} chunks for follow-up")
            
            # Update UI
            self.window.after(0, lambda: self.status_label.config(text=f"Processing follow-up chunk 1 of {self.total_chunks}..."))
            
            # Process each chunk
            for chunk_idx, (start_idx, end_idx) in enumerate(chunks):
                self.current_chunk = chunk_idx + 1
                chunk_rows = end_idx - start_idx
                
                self.window.after(0, lambda c=self.current_chunk, t=self.total_chunks: 
                                self.log_message(f"🔄 Processing follow-up chunk {c} of {t} (rows {start_idx+1}-{end_idx})..."))
                
                # Extract chunk data
                chunk_df = self.df.iloc[start_idx:end_idx][columns].copy()
                
                # Process chunk with follow-up context
                chunk_result = self._process_single_followup_chunk(chunk_df, question, chunk_idx + 1, columns, conversation_context)
                
                if chunk_result:
                    self.chunk_results.append({
                        "chunk_number": chunk_idx + 1,
                        "rows_processed": chunk_rows,
                        "start_row": start_idx + 1,
                        "end_row": end_idx,
                        "result": chunk_result
                    })
                    
                    # Save progress after each successful chunk
                    self._save_progress(self.chunk_results, "in_progress")
                    
                    self.window.after(0, lambda c=self.current_chunk, t=self.total_chunks: 
                                    self.status_label.config(text=f"Completed follow-up chunk {c} of {t}"))
                else:
                    # Chunk failed, but continue with partial results
                    self.window.after(0, lambda c=self.current_chunk: 
                                    self.log_message(f"❌ Follow-up chunk {c} failed, continuing with partial results"))
            
            # Combine results
            if self.chunk_results:
                self.window.after(0, lambda: self.log_message("🔄 Combining follow-up findings from all chunks..."))
                self.window.after(0, lambda: self.status_label.config(text="Combining follow-up findings..."))
                
                combined_result = self._combine_followup_chunk_results(question, columns, conversation_context)
                
                if combined_result:
                    # Save final progress
                    self._save_progress(self.chunk_results, "completed")
                    
                    # Add to conversation and display
                    self.add_to_conversation("ai_response", combined_result, {
                        "processing_method": "chunked_followup",
                        "chunks_processed": len(self.chunk_results),
                        "total_chunks": self.total_chunks,
                        "rows_analyzed": sum(chunk['rows_processed'] for chunk in self.chunk_results),
                        "columns_used": columns
                    })
                    
                    self.window.after(0, lambda: self._add_to_conversation_display(f"Assistant: {combined_result}", "ai_response"))
                    
                    # Clean up
                    self._cleanup_progress_file()
                    
                    self.window.after(0, lambda: self.log_message("✅ Chunked follow-up analysis completed successfully!"))
                else:
                    raise Exception("Failed to combine follow-up chunk results")
            else:
                raise Exception("No follow-up chunks processed successfully")
                
        except Exception as e:
            # Save partial results
            if self.chunk_results:
                self._save_progress(self.chunk_results, "partial_failure")
                self.window.after(0, lambda: self.log_message(f"⚠️ Partial follow-up results saved to progress file"))
            
            self.window.after(0, lambda: self._handle_analysis_error(f"Chunked follow-up analysis failed: {str(e)}"))
        finally:
            self.is_chunked_processing = False
            self.window.after(0, self._enable_buttons)

    def _process_single_followup_chunk(self, chunk_df, question, chunk_number, columns, conversation_context):
        """Process a single chunk for follow-up analysis"""
        try:
            # Convert to CSV
            csv_data = chunk_df.to_csv(index=False)
            
            # Estimate tokens
            prompt_tokens = self.count_tokens(f"""You are continuing a data analysis conversation for WordPress.com support data.

Previous conversation:
{conversation_context}

This is chunk {chunk_number} of a larger follow-up analysis.

Follow-up question: {question}
Columns: {', '.join(columns)}
Rows in this chunk: {len(chunk_df)}

Data:
""")
            data_tokens = self.count_tokens(csv_data)
            total_tokens = prompt_tokens + data_tokens
            
            # Check if chunk fits in token limit
            if total_tokens > self.CHUNK_TOKEN_LIMIT:
                self.window.after(0, lambda: self.log_message(f"⚠️ Follow-up chunk {chunk_number} too large ({total_tokens:,} tokens), reducing size..."))
                
                # Reduce chunk size
                max_rows = int(len(chunk_df) * 0.7)  # Reduce by 30%
                if max_rows < 10:  # Minimum viable chunk
                    raise Exception(f"Follow-up chunk {chunk_number} cannot be reduced further")
                
                chunk_df = chunk_df.sample(n=max_rows, random_state=42)
                csv_data = chunk_df.to_csv(index=False)
                data_tokens = self.count_tokens(csv_data)
                total_tokens = prompt_tokens + data_tokens
            
            # Create follow-up chunk analysis prompt
            chunk_prompt = f"""You are continuing a data analysis conversation for WordPress.com support data.

Previous conversation:
{conversation_context}

This is chunk {chunk_number} of a larger follow-up analysis.

Follow-up question: {question}

Dataset Context:
- This is chunk {chunk_number} of a multi-chunk follow-up analysis
- Rows in this chunk: {len(chunk_df):,}
- Columns: {', '.join(columns)}

Data (CSV format):
{csv_data}

Provide a focused follow-up analysis of this chunk that:
1. Directly addresses the follow-up question
2. References previous conversation context when relevant
3. Provides specific insights from this data subset
4. Keeps the response concise but informative

This will be combined with other chunks later, so focus on this chunk's specific contributions."""

            # Make API call
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": chunk_prompt}],
                temperature=0.3,
                max_tokens=2000
            )
            
            result = self._parse_api_response(response, f"Follow-up chunk {chunk_number} analysis")
            self.window.after(0, lambda: self.log_message(f"✅ Follow-up chunk {chunk_number} processed successfully"))
            
            return result
            
        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"❌ Follow-up chunk {chunk_number} failed: {str(e)}"))
            return None

    def _combine_followup_chunk_results(self, question, columns, conversation_context):
        """Combine results from all follow-up chunks using AI"""
        try:
            # Prepare chunk results for combination
            chunk_summaries = []
            total_rows_processed = 0
            
            for chunk_data in self.chunk_results:
                chunk_summaries.append(f"CHUNK {chunk_data['chunk_number']} (rows {chunk_data['start_row']}-{chunk_data['end_row']}):\n{chunk_data['result']}")
                total_rows_processed += chunk_data['rows_processed']
            
            # Create follow-up aggregation prompt
            aggregation_prompt = f"""You are combining follow-up analysis results from multiple data chunks in an ongoing conversation.

Previous conversation:
{conversation_context}

Follow-up Question: {question}
Total Rows Processed: {total_rows_processed:,}
Columns Analyzed: {', '.join(columns)}

CHUNK RESULTS:
{chr(10).join(chunk_summaries)}

Please synthesize these follow-up findings into a unified response that:
1. Directly answers the follow-up question
2. References the previous conversation appropriately
3. Identifies patterns across all chunks
4. Provides a concise but comprehensive answer
5. Maintains the conversational flow

Keep the response focused and conversational - this is a follow-up in an ongoing discussion."""

            # Make API call to combine results
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": aggregation_prompt}],
                temperature=0.3,
                max_tokens=3000
            )
            
            combined_result = self._parse_api_response(response, "Follow-up chunk combination")
            return combined_result
            
        except Exception as e:
            self.window.after(0, lambda: self.log_message(f"❌ Failed to combine follow-up chunk results: {str(e)}"))
            return None

    def estimate_prompt_tokens(self, question, selected_columns, sample_size):
        """Estimate total tokens for the analysis prompt"""
        # Base prompt structure
        base_prompt = f"""You are a senior data analyst at Automattic Inc, specializing in customer support analytics for WordPress.com, WooCommerce, and Jetpack products.

Analysis Request: {question}

Original Question: {question}

Dataset Context:
- Total rows analyzed: {sample_size:,}
- Columns included: {', '.join(selected_columns)}
- Data source: support interactions
- Sample method: Random sample

Data (CSV format):
"""
        
        # Count tokens for base prompt
        base_tokens = self.count_tokens(base_prompt)
        
        # Estimate data tokens (sample a few rows to get average)
        if len(self.df) > 0 and selected_columns:
            try:
                sample_data = self.df[selected_columns].head(min(10, len(self.df)))
                sample_csv = sample_data.to_csv(index=False)
                tokens_per_row = self.count_tokens(sample_csv) / len(sample_data)
                estimated_data_tokens = int(tokens_per_row * sample_size)
            except:
                # Fallback estimation
                estimated_data_tokens = sample_size * len(selected_columns) * 10
        else:
            estimated_data_tokens = 0
        
        total_tokens = base_tokens + estimated_data_tokens
        return total_tokens
    
    def _parse_api_response(self, response, context="API call"):
        """Robust API response parsing with detailed error handling"""
        try:
            # Validate response object
            if not response or not hasattr(response, 'choices'):
                raise Exception(f"{context}: API returned invalid response object")
            
            if not response.choices or len(response.choices) == 0:
                raise Exception(f"{context}: API returned empty choices array")
            
            if not response.choices[0] or not hasattr(response.choices[0], 'message'):
                raise Exception(f"{context}: API returned invalid choice object")
            
            if not response.choices[0].message or not hasattr(response.choices[0].message, 'content'):
                raise Exception(f"{context}: API returned invalid message object")
            
            response_text = response.choices[0].message.content
            if not response_text:
                raise Exception(f"{context}: API returned empty content")
            
            return response_text.strip()
            
        except Exception as e:
            # Log the error with context
            self.window.after(0, lambda: self.log_message(f"❌ Response parsing failed for {context}: {str(e)}"))
            raise
    
    def log_message(self, message):
        """Add a message to the log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Update the window to show the message immediately
        self.window.update_idletasks()
        
    def show_example_questions(self):
        """Show example questions in a popup"""
        examples = [
            "What are the main reasons customers give negative CSAT ratings?",
            "What product feedback trends have emerged in the last month?",
            "How does response time correlate with customer satisfaction?",
            "What are the most common customer goals in support interactions?",
            "Which topics are associated with the longest resolution times?",
            "What percentage of issues are product-related vs service-related?",
            "How accurate are our CSAT predictions compared to actual ratings?",
            "What sentiment patterns do we see in resolved vs unresolved tickets?"
        ]
        
        example_window = tk.Toplevel(self.window)
        example_window.title("Example Questions")
        example_window.geometry("600x400")
        example_window.transient(self.window)
        
        tk.Label(
            example_window, 
            text="Click any question to use it:", 
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        for i, example in enumerate(examples):
            btn = tk.Button(
                example_window,
                text=f"{i+1}. {example}",
                wraplength=550,
                justify=tk.LEFT,
                command=lambda q=example: self.use_example_question(q, example_window)
            )
            btn.pack(fill=tk.X, padx=20, pady=2)
            
    def use_example_question(self, question, example_window):
        """Use an example question"""
        self.question_text.delete(1.0, tk.END)
        self.question_text.insert(1.0, question)
        example_window.destroy()
        
    def analyze_question(self):
        """Analyze the user's question and select relevant columns"""
        question = self.question_text.get(1.0, tk.END).strip()
        
        if not question:
            messagebox.showwarning("Warning", "Please enter a question first.")
            return
            
        if not self.api_key:
            messagebox.showerror("Error", "No API key provided.")
            return
            
        # Clear previous results
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state=tk.DISABLED)
        
        # Disable button and show progress
        self.analyze_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Analyzing question...")
        self.log_message(f"🔍 Analyzing question: {question[:100]}{'...' if len(question) > 100 else ''}")
        
        # Run analysis in thread
        thread = threading.Thread(target=self._analyze_question_thread, args=(question,))
        thread.daemon = True
        thread.start()
        
    def _analyze_question_thread(self, question):
        """Thread function for question analysis"""
        try:
            self.window.after(0, lambda: self.log_message("🤖 Sending question to AI for analysis..."))
            
            # Prepare column metadata for AI
            available_columns = []
            for col in self.df.columns:
                if col in COLUMN_METADATA:
                    metadata = COLUMN_METADATA[col]
                    available_columns.append({
                        "name": col,
                        "description": metadata["description"],
                        "use_cases": metadata["use_cases"],
                        "data_size": metadata["data_size"],
                        "priority": metadata["priority"]
                    })
                else:
                    # Handle columns not in metadata
                    available_columns.append({
                        "name": col,
                        "description": f"Column: {col}",
                        "use_cases": ["general analysis"],
                        "data_size": "unknown",
                        "priority": "medium"
                    })
            
            self.window.after(0, lambda: self.log_message(f"📊 Found {len(available_columns)} columns in dataset"))
            
            # Create analysis prompt
            analysis_prompt = f"""You are a senior data analyst specializing in customer support analytics for Automattic Inc (WordPress.com, WooCommerce, Jetpack).

User Question: "{question}"

Available Columns in Dataset:
{json.dumps(available_columns, indent=2)}

Analyze the user's question and return a JSON response with:
1. A refined, optimized analytical prompt that will help answer the question effectively
2. A list of the most relevant columns needed for this analysis
3. Brief reasoning for your selections

Guidelines:
- Prioritize columns with "very_high" and "high" priority when relevant
- Avoid "very_large" data_size columns unless absolutely necessary
- Consider context window limitations
- Focus on columns that directly relate to the question
- The refined prompt should be clear, specific, and analytical

Return only valid JSON in this format:
{{
    "refined_prompt": "Your optimized analytical prompt here",
    "selected_columns": ["column1", "column2", "column3"],
    "reasoning": "Brief explanation of why these columns were selected"
}}"""

            # Make API call with robust error handling
            client = openai.OpenAI(api_key=self.api_key)
            
            # Log the prompt size for debugging
            prompt_size = len(analysis_prompt)
            self.window.after(0, lambda: self.log_message(f"📤 Sending prompt ({prompt_size:,} characters) to AI..."))
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4.1",
                    messages=[{"role": "user", "content": analysis_prompt}],
                    temperature=0.3,
                    max_tokens=1000
                )
                
                self.window.after(0, lambda: self.log_message("✅ AI analysis complete, parsing response..."))
                
                # Robust response parsing
                if not response or not hasattr(response, 'choices'):
                    raise Exception("API returned invalid response object")
                
                if not response.choices or len(response.choices) == 0:
                    raise Exception("API returned empty choices array")
                
                if not response.choices[0] or not hasattr(response.choices[0], 'message'):
                    raise Exception("API returned invalid choice object")
                
                if not response.choices[0].message or not hasattr(response.choices[0].message, 'content'):
                    raise Exception("API returned invalid message object")
                
                response_text = response.choices[0].message.content
                if not response_text:
                    raise Exception("API returned empty content")
                
                response_text = response_text.strip()
                self.window.after(0, lambda: self.log_message(f"📥 Received response ({len(response_text):,} characters)"))
                
                # Try to extract JSON from response
                try:
                    # Find JSON in response
                    start_idx = response_text.find('{')
                    end_idx = response_text.rfind('}') + 1
                    
                    if start_idx == -1 or end_idx == 0:
                        raise Exception("No JSON found in API response")
                    
                    json_str = response_text[start_idx:end_idx]
                    self.window.after(0, lambda: self.log_message(f"🔍 Extracting JSON ({len(json_str):,} characters)"))
                    
                    analysis_result = json.loads(json_str)
                    
                    # Validate the JSON structure
                    if not isinstance(analysis_result, dict):
                        raise Exception("API response is not a valid JSON object")
                    
                    if "selected_columns" not in analysis_result:
                        raise Exception("API response missing 'selected_columns' field")
                    
                    selected_columns = analysis_result.get("selected_columns", [])
                    if not isinstance(selected_columns, list):
                        raise Exception("'selected_columns' field is not a list")
                    
                    # Validate that selected columns exist in dataset
                    valid_columns = []
                    for col in selected_columns:
                        if col in self.df.columns:
                            valid_columns.append(col)
                        else:
                            self.window.after(0, lambda c=col: self.log_message(f"⚠️  Column '{c}' not found in dataset, skipping"))
                    
                    analysis_result["selected_columns"] = valid_columns
                    selected_count = len(valid_columns)
                    self.window.after(0, lambda: self.log_message(f"🎯 AI selected {selected_count} valid columns"))
                    
                except json.JSONDecodeError as je:
                    self.window.after(0, lambda: self.log_message(f"❌ JSON parsing error: {str(je)}"))
                    self.window.after(0, lambda: self.log_message(f"📄 Raw response: {response_text[:500]}..."))
                    raise Exception(f"Failed to parse AI response as JSON: {str(je)}")
                except Exception as pe:
                    self.window.after(0, lambda: self.log_message(f"❌ Response parsing error: {str(pe)}"))
                    raise Exception(f"Failed to parse AI response: {str(pe)}")
                
            except Exception as api_error:
                # Handle specific API errors
                error_str = str(api_error)
                if "context_length_exceeded" in error_str or "token" in error_str.lower():
                    self.window.after(0, lambda: self.log_message("❌ Context length exceeded during question analysis"))
                    raise Exception("Dataset too large for initial analysis. Try selecting fewer columns manually or reducing dataset size.")
                elif "rate_limit" in error_str.lower():
                    self.window.after(0, lambda: self.log_message("❌ Rate limit exceeded"))
                    raise Exception("API rate limit exceeded. Please wait a moment and try again.")
                elif "invalid_request" in error_str.lower():
                    self.window.after(0, lambda: self.log_message("❌ Invalid API request"))
                    raise Exception("Invalid API request. This may be due to very large text content in your data.")
                else:
                    self.window.after(0, lambda: self.log_message(f"❌ API error: {error_str}"))
                    raise Exception(f"API error: {error_str}")
            
            # Update UI in main thread
            self.window.after(0, self._show_column_selection, analysis_result, question)
            
        except Exception as e:
            self.window.after(0, self._handle_analysis_error, str(e))
            
    def _show_column_selection(self, analysis_result, original_question):
        """Show column selection in the main window"""
        self.status_label.config(text="Review column selection")
        self.analyze_btn.config(state=tk.NORMAL)
        
        # Add question to conversation history
        if not self.is_follow_up:  # Only add if it's not already added as follow-up
            self.add_to_conversation("user_question", original_question)
            self._add_to_conversation_display(f"You: {original_question}", "user_question")
        
        # Store the analysis result and question for later use
        self.current_analysis_result = analysis_result
        self.current_question = original_question
        
        # Show AI reasoning
        reasoning = analysis_result.get("reasoning", "No reasoning provided")
        self.reasoning_text.config(state=tk.NORMAL)
        self.reasoning_text.delete(1.0, tk.END)
        self.reasoning_text.insert(1.0, f"AI Reasoning: {reasoning}")
        self.reasoning_text.config(state=tk.DISABLED)
        
        # Clear previous column checkboxes
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Column checkboxes
        self.column_vars = {}
        selected_cols = analysis_result.get("selected_columns", [])
        
        for col in self.df.columns:
            var = tk.BooleanVar(value=col in selected_cols)
            self.column_vars[col] = var
            
            frame = tk.Frame(self.scrollable_frame)
            frame.pack(fill=tk.X, pady=1, anchor=tk.W)
            
            cb = tk.Checkbutton(
                frame, 
                text=col, 
                variable=var,
                command=self.update_token_estimate  # Update tokens when selection changes
            )
            cb.pack(side=tk.LEFT)
            
            # Show column info if available
            if col in COLUMN_METADATA:
                info_label = tk.Label(
                    frame, 
                    text=f"({COLUMN_METADATA[col]['description']})",
                    font=("Arial", 8),
                    fg="gray"
                )
                info_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Show the column selection frame
        self.column_frame.grid()
        self.proceed_btn.config(state=tk.NORMAL)
        
        # Update token estimate
        self.update_token_estimate()
        
        self.log_message("📋 Review and modify column selection, then click 'Proceed with Analysis'")
    
    def update_token_estimate(self):
        """Update token estimate based on current column selection"""
        if not hasattr(self, 'column_vars') or not hasattr(self, 'current_question'):
            return
            
        # Get currently selected columns
        selected_columns = [col for col, var in self.column_vars.items() if var.get()]
        
        if not selected_columns:
            self.update_token_counter(0)
            return
        
        # Estimate tokens using dynamic row reduction strategy
        actual_size = min(len(self.df), 5000)  # Start with 5000 or dataset size if smaller
        
        estimated_tokens = self.estimate_prompt_tokens(
            self.current_question, 
            selected_columns, 
            actual_size
        )
        
        # Update the display
        self.update_token_counter(estimated_tokens)
        
        # Log token estimate details
        if estimated_tokens > 0:
            percentage = (estimated_tokens / self.MAX_TOKENS) * 100
            self.log_message(f"📊 Token estimate: {estimated_tokens:,} ({percentage:.1f}%) for {len(selected_columns)} columns, {actual_size:,} rows")
    
    def cancel_column_selection(self):
        """Cancel column selection and hide the frame"""
        self.column_frame.grid_remove()
        self.status_label.config(text="Ready")
        self.log_message("❌ Column selection cancelled")
    
    def proceed_with_analysis(self):
        """Proceed with the data analysis using selected columns"""
        # Get selected columns
        selected_columns = [col for col, var in self.column_vars.items() if var.get()]
        
        if not selected_columns:
            messagebox.showwarning("Warning", "Please select at least one column.")
            return
        
        # Hide column selection frame
        self.column_frame.grid_remove()
        
        # Log the selection
        self.log_message(f"✅ Selected {len(selected_columns)} columns for analysis")
        self.log_message(f"📊 Columns: {', '.join(selected_columns[:5])}{', ...' if len(selected_columns) > 5 else ''}")
        
        # Start data analysis
        self.status_label.config(text="Analyzing data...")
        self.proceed_btn.config(state=tk.DISABLED)
        
        thread = threading.Thread(
            target=self._perform_data_analysis_thread, 
            args=(self.current_analysis_result, self.current_question, selected_columns)
        )
        thread.daemon = True
        thread.start()
        
    def _perform_data_analysis_thread(self, analysis_result, original_question, selected_columns):
        """Perform the actual data analysis"""
        try:
            self.window.after(0, lambda: self.log_message("🔄 Preparing data for analysis..."))
            
            # Prepare data sample with error handling
            max_rows = 5000
            sample_df = self.df
            
            try:
                self.window.after(0, lambda: self.log_message(f"📊 Dataset info: {len(self.df):,} rows, {len(self.df.columns)} columns"))
                self.window.after(0, lambda: self.log_message(f"📋 Dataset columns: {list(self.df.columns)}"))
                
                if len(self.df) > max_rows:
                    self.window.after(0, lambda: self.log_message(f"🔄 Sampling {max_rows:,} rows from {len(self.df):,} total..."))
                    sample_df = self.df.sample(n=max_rows, random_state=42)
                    self.window.after(0, lambda l=max_rows: self.log_message(f"📊 Using random sample of {l:,} rows from {len(self.df):,} total"))
                    self.window.after(0, lambda l=max_rows: self.status_label.config(
                        text=f"Using random sample of {l:,} rows..."
                    ))
                else:
                    self.window.after(0, lambda: self.log_message(f"📊 Using full dataset ({len(self.df):,} rows)"))
                    
                self.window.after(0, lambda: self.log_message(f"✅ Sample prepared: {len(sample_df):,} rows, {len(sample_df.columns)} columns"))
                
            except Exception as sample_error:
                self.window.after(0, lambda: self.log_message(f"❌ Sampling failed: {str(sample_error)}"))
                raise Exception(f"Failed to prepare data sample: {str(sample_error)}")
            
            # Check if chunking is needed
            if self._check_if_chunking_needed(original_question, selected_columns, len(self.df)):
                self.window.after(0, lambda: self.log_message("⚠️ Dataset too large for single analysis"))
                
                # Estimate tokens for user dialog
                estimated_tokens = self.estimate_prompt_tokens(original_question, selected_columns, len(self.df))
                
                # Show user choice dialog
                user_choice = self._show_chunking_dialog(original_question, selected_columns, estimated_tokens, len(self.df))
                
                if user_choice == "chunk":
                    # Perform chunked analysis
                    self.window.after(0, lambda: self.log_message("🔄 Starting chunked analysis..."))
                    self._perform_chunked_analysis(original_question, selected_columns, analysis_result)
                    return
                elif user_choice == "reduce":
                    # Continue with reduced dataset
                    max_rows = min(1000, len(self.df))
                    self.window.after(0, lambda: self.log_message(f"🔄 Continuing with reduced dataset ({max_rows:,} rows)"))
                    if len(self.df) > max_rows:
                        sample_df = self.df.sample(n=max_rows, random_state=42)
                else:
                    # User cancelled
                    self.window.after(0, lambda: self.log_message("❌ Analysis cancelled by user"))
                    self.window.after(0, self._enable_buttons)
                    return
            
            # Try different row limits if API fails - start with dataset size and reduce by 500 each time
            max_rows = len(sample_df)
            row_limits = []
            
            # Generate row limits starting from max_rows, reducing by 500 each time, down to minimum
            current_limit = max_rows
            min_rows = min(500, max_rows)  # Use actual dataset size if smaller than 500
            
            # Always include the full dataset size first
            row_limits.append(current_limit)
            
            # Generate additional limits only if we have more than the minimum
            if max_rows > min_rows:
                current_limit -= 500
                while current_limit >= min_rows:
                    row_limits.append(current_limit)
                    current_limit -= 500
                
                # Ensure we always have the minimum as the last option
                if row_limits[-1] != min_rows:
                    row_limits.append(min_rows)
            
            # Remove duplicates and sort in descending order
            row_limits = sorted(list(set(row_limits)), reverse=True)
            
            self.window.after(0, lambda: self.log_message(f"📊 Row reduction strategy: {len(row_limits)} attempts from {max_rows:,} down to {min_rows:,} rows"))
            
            analysis_successful = False
            final_row_count = 0
            
            for attempt_num, limit in enumerate(row_limits, 1):
                try:
                    # Prepare current sample with error handling
                    try:
                        if len(sample_df) > limit:
                            current_sample = sample_df.sample(n=limit, random_state=42)
                            self.window.after(0, lambda l=limit, a=attempt_num, t=len(row_limits): self.log_message(f"⚠️  Attempt {a}/{t}: Trying with {l:,} rows"))
                            self.window.after(0, lambda l=limit, a=attempt_num, t=len(row_limits): self.status_label.config(
                                text=f"Attempt {a}/{t}: Trying with {l:,} rows..."
                            ))
                        else:
                            current_sample = sample_df
                            
                        self.window.after(0, lambda: self.log_message(f"📊 Current sample prepared: {len(current_sample):,} rows"))
                        
                    except Exception as sample_error:
                        self.window.after(0, lambda: self.log_message(f"❌ Failed to create sample: {str(sample_error)}"))
                        raise Exception(f"Sampling error: {str(sample_error)}")
                    
                    # Select only the chosen columns with error handling
                    try:
                        self.window.after(0, lambda: self.log_message(f"🔍 Selecting columns: {selected_columns}"))
                        self.window.after(0, lambda: self.log_message(f"📊 Current sample shape: {current_sample.shape}"))
                        self.window.after(0, lambda: self.log_message(f"📋 Available columns: {list(current_sample.columns)}"))
                        
                        # Validate columns exist
                        missing_columns = [col for col in selected_columns if col not in current_sample.columns]
                        if missing_columns:
                            raise Exception(f"Missing columns in dataset: {missing_columns}")
                        
                        analysis_data = current_sample[selected_columns]
                        final_row_count = len(analysis_data)
                        
                        self.window.after(0, lambda: self.log_message(f"🎯 Analyzing {final_row_count:,} rows with {len(selected_columns)} columns"))
                        self.window.after(0, lambda: self.log_message(f"📊 Analysis data shape: {analysis_data.shape}"))
                        
                    except Exception as column_error:
                        self.window.after(0, lambda: self.log_message(f"❌ Column selection failed: {str(column_error)}"))
                        raise Exception(f"Failed to select columns: {str(column_error)}")
                    
                    # Convert to CSV string for API with error handling
                    try:
                        self.window.after(0, lambda: self.log_message("🔄 Converting data to CSV format..."))
                        csv_data = analysis_data.to_csv(index=False)
                        self.window.after(0, lambda: self.log_message(f"📄 CSV data size: {len(csv_data):,} characters"))
                        
                    except Exception as csv_error:
                        self.window.after(0, lambda: self.log_message(f"❌ CSV conversion failed: {str(csv_error)}"))
                        raise Exception(f"Failed to convert data to CSV: {str(csv_error)}")
                    data_size_kb = len(csv_data.encode('utf-8')) / 1024
                    
                    # Count actual tokens
                    actual_tokens = self.estimate_prompt_tokens(
                        original_question, 
                        selected_columns, 
                        final_row_count
                    )
                    
                    # Update token counter
                    self.window.after(0, lambda: self.update_token_counter(actual_tokens))
                    
                    # Check if tokens exceed limit
                    if actual_tokens > self.MAX_TOKENS * 0.95:  # 95% safety margin
                        self.window.after(0, lambda: self.log_message(f"❌ Token limit exceeded: {actual_tokens:,} tokens. Trying smaller sample..."))
                        continue
                    
                    self.window.after(0, lambda: self.log_message(f"📤 Sending {data_size_kb:.1f} KB ({actual_tokens:,} tokens) to AI..."))
                    
                    # Create analysis prompt
                    refined_prompt = analysis_result.get("refined_prompt", original_question)
                    
                    data_analysis_prompt = f"""You are a senior data analyst at Automattic Inc, specializing in customer support analytics for WordPress.com, WooCommerce, and Jetpack products.

Analysis Request: {refined_prompt}

Original Question: {original_question}

Dataset Context:
- Total rows analyzed: {final_row_count:,}
- Columns included: {', '.join(selected_columns)}
- Data source: support interactions
- Sample method: {"Random sample" if len(self.df) > final_row_count else "Full dataset"}

Data (CSV format):
{csv_data}

Please provide a comprehensive analysis with:

1. **Executive Summary** - Key findings in 2-3 sentences
2. **Detailed Analysis** - In-depth insights with specific data points
3. **Key Metrics** - Important numbers and percentages
4. **Actionable Recommendations** - Specific steps based on findings
5. **Supporting Evidence** - Data points that support your conclusions

Format your response in clear markdown with headers and bullet points for readability."""

                    # Make API call
                    client = openai.OpenAI(api_key=self.api_key)
                    self.window.after(0, lambda: self.log_message("🤖 Sending data to AI for comprehensive analysis..."))
                    
                    response = client.chat.completions.create(
                        model="gpt-4.1",
                        messages=[{"role": "user", "content": data_analysis_prompt}],
                        temperature=0.3,
                        max_tokens=4000
                    )
                    
                    analysis_result_text = self._parse_api_response(response, "Data analysis")
                    analysis_successful = True
                    
                    self.window.after(0, lambda: self.log_message("✅ AI analysis completed successfully!"))
                    break
                    
                except Exception as e:
                    if "context" in str(e).lower() or "token" in str(e).lower():
                        self.window.after(0, lambda l=limit, a=attempt_num, t=len(row_limits): self.log_message(f"⚠️  Attempt {a}/{t}: Context limit exceeded with {l:,} rows, trying smaller sample..."))
                        continue  # Try with fewer rows
                    else:
                        raise e  # Different error, don't retry
            
            if not analysis_successful:
                raise Exception("Failed to analyze data even with reduced dataset size")
            
            # Prepare final result
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            final_result = f"""# Talk to Data Analysis Results
**Generated:** {timestamp}

## Question Asked
{original_question}

## Columns Analyzed
{', '.join(selected_columns)}

## Dataset Information
- **Rows analyzed:** {final_row_count:,}
- **Total dataset size:** {len(self.df):,} rows
- **Sampling method:** {"Random sample" if len(self.df) > final_row_count else "Full dataset"}

---

{analysis_result_text}

---
*Generated by AI Support Analyzer - Talk to Data feature*
"""
            
            # Update UI
            self.window.after(0, self._display_results, final_result, original_question, selected_columns, final_row_count)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.window.after(0, lambda: self.log_message(f"❌ Full error traceback: {error_details}"))
            self.window.after(0, self._handle_analysis_error, str(e))
            
    def _display_results(self, result_text, question, columns, row_count):
        """Display analysis results in the conversational interface"""
        self.analysis_result = result_text
        
        # Store current context for follow-ups
        self.current_context_columns = columns
        
        # Add to conversation history
        self.add_to_conversation("ai_response", result_text, {
            "columns_used": columns,
            "rows_analyzed": row_count
        })
        
        # Display in conversation format
        self._add_to_conversation_display(f"Assistant: {result_text}", "ai_response")
        
        # Show follow-up options
        self.followup_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.new_conversation_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.save_btn.config(state=tk.NORMAL)
        self.status_label.config(text=f"Analysis complete - {row_count:,} rows analyzed")
        self.analyze_btn.config(state=tk.NORMAL)
        
        # Clear question text and focus for next input
        self.question_text.delete(1.0, tk.END)
        self.question_text.focus()
        
        self.log_message(f"🎉 Analysis complete! Results displayed ({len(result_text):,} characters)")
        self.log_message(f"💬 You can now ask follow-up questions or start a new conversation")
        
    def _handle_analysis_error(self, error_message):
        """Handle analysis errors"""
        self.status_label.config(text="Error occurred")
        self.analyze_btn.config(state=tk.NORMAL)
        self.proceed_btn.config(state=tk.NORMAL)
        
        self.log_message(f"❌ Analysis failed: {error_message}")
        messagebox.showerror("Analysis Error", f"Failed to analyze data:\n\n{error_message}")
        
    def save_results(self):
        """Save conversation history to file"""
        if not self.full_conversation_history and not self.analysis_result:
            return
            
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        default_filename = f"talktodata-conversation-{timestamp}.txt"
        
        # Get directory of original CSV file
        csv_dir = os.path.dirname(self.csv_file_path)
        default_path = os.path.join(csv_dir, default_filename)
        
        filename = filedialog.asksaveasfilename(
            title="Save Conversation",
            initialdir=csv_dir,
            initialfile=default_filename,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Talk to Data - Conversation Export\n")
                    f.write(f"Dataset: {os.path.basename(self.csv_file_path)}\n")
                    f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 60 + "\n\n")
                    
                    if self.conversation_summary:
                        f.write(f"Conversation Summary:\n{self.conversation_summary}\n\n")
                        f.write("=" * 60 + "\n\n")
                    
                    # Write FULL conversation history (not the summarized version)
                    for i, entry in enumerate(self.full_conversation_history):
                        timestamp = entry['timestamp'].strftime('%H:%M:%S')
                        if entry['type'] == 'user_question':
                            f.write(f"[{timestamp}] You: {entry['content']}\n\n")
                        elif entry['type'] == 'ai_response':
                            f.write(f"[{timestamp}] Assistant: {entry['content']}\n\n")
                            if entry.get('metadata'):
                                meta = entry['metadata']
                                if 'columns_used' in meta:
                                    f.write(f"    Columns analyzed: {', '.join(meta['columns_used'])}\n")
                                if 'rows_analyzed' in meta:
                                    f.write(f"    Rows analyzed: {meta['rows_analyzed']:,}\n")
                                f.write("\n")
                        
                        if i < len(self.full_conversation_history) - 1:
                            f.write("-" * 50 + "\n\n")
                
                self.log_message(f"💾 Conversation saved to: {os.path.basename(filename)}")
                messagebox.showinfo("Success", f"Conversation saved to:\n{filename}")
            except Exception as e:
                self.log_message(f"❌ Failed to save file: {str(e)}")
                messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")

    def add_to_conversation(self, message_type, content, metadata=None):
        """Add a message to conversation history"""
        entry = {
            "type": message_type,  # "user_question", "ai_response", "column_request"
            "content": content,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }
        self.conversation_history.append(entry)
        self.full_conversation_history.append(entry)  # Always keep full history
        
        # Manage conversation length and summarize if needed
        if len(self.conversation_history) > self.max_history_length * 2:  # *2 for user+ai pairs
            self._summarize_old_conversation()
    
    def _summarize_old_conversation(self):
        """Summarize older conversation exchanges to maintain context while reducing tokens"""
        if len(self.conversation_history) <= self.max_history_length * 2:
            return
            
        # Keep recent exchanges
        recent_exchanges = self.conversation_history[-(self.max_history_length * 2):]
        old_exchanges = self.conversation_history[:-(self.max_history_length * 2)]
        
        # Create summary of old exchanges
        summary_content = []
        for entry in old_exchanges:
            if entry["type"] == "user_question":
                summary_content.append(f"User asked: {entry['content'][:100]}...")
            elif entry["type"] == "ai_response":
                summary_content.append(f"AI found: {entry['content'][:200]}...")
        
        # Create summarization prompt
        summary_prompt = f"""Summarize this conversation history into a brief context summary:

{chr(10).join(summary_content)}

Create a concise summary that captures:
1. Key findings and insights discovered
2. Main topics explored
3. Data context and filters used

Keep it under 200 words and focus on actionable insights."""

        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3,
                max_tokens=300
            )
            
            self.conversation_summary = self._parse_api_response(response, "Conversation summary")
            self.conversation_history = recent_exchanges
            self.log_message("📝 Conversation summarized to maintain context")
            
        except Exception as e:
            self.log_message(f"⚠️ Failed to summarize conversation: {str(e)}")
    
    def get_conversation_context(self):
        """Get conversation context for AI prompts"""
        context = []
        
        # Add summary if available
        if self.conversation_summary:
            context.append(f"Previous conversation summary:\n{self.conversation_summary}\n")
        
        # Add recent exchanges
        for entry in self.conversation_history:
            if entry["type"] == "user_question":
                context.append(f"User: {entry['content']}")
            elif entry["type"] == "ai_response":
                # Truncate long responses for context
                response = entry['content'][:500] + "..." if len(entry['content']) > 500 else entry['content']
                context.append(f"Assistant: {response}")
        
        return "\n".join(context)
    
    def start_new_conversation(self):
        """Start a new conversation, clearing history"""
        self.conversation_history = []
        self.full_conversation_history = []
        self.current_context_columns = []
        self.conversation_summary = ""
        self.is_follow_up = False
        
        # Clear UI elements
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state=tk.DISABLED)
        
        self.question_text.delete(1.0, tk.END)
        self.column_frame.grid_remove()
        
        self.log_message("🆕 Started new conversation")
        self.status_label.config(text="Ready for new conversation")
        
    def ask_followup_question(self):
        """Handle follow-up questions in the conversation"""
        question = self.question_text.get(1.0, tk.END).strip()
        
        if not question:
            messagebox.showwarning("Warning", "Please enter a follow-up question first.")
            return
            
        if not self.api_key:
            messagebox.showerror("Error", "No API key provided.")
            return
        
        # Mark as follow-up
        self.is_follow_up = True
        
        # Add question to conversation
        self.add_to_conversation("user_question", question)
        
        # Disable button and show progress
        self.followup_btn.config(state=tk.DISABLED)
        self.analyze_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Analyzing follow-up question...")
        
        # Display the question in conversation
        self._add_to_conversation_display(f"You: {question}", "user_question")
        
        self.log_message(f"🔄 Processing follow-up: {question[:100]}{'...' if len(question) > 100 else ''}")
        
        # Run analysis in thread
        thread = threading.Thread(target=self._analyze_followup_thread, args=(question,))
        thread.daemon = True
        thread.start()
    
    def _analyze_followup_thread(self, question):
        """Thread function for follow-up question analysis"""
        try:
            self.window.after(0, lambda: self.log_message("🤖 AI analyzing follow-up for new data needs..."))
            
            # Get conversation context
            conversation_context = self.get_conversation_context()
            
            # Determine if new columns or data filtering is needed
            followup_analysis_prompt = f"""You are analyzing a follow-up question in an ongoing data analysis conversation.

Current conversation context:
{conversation_context}

Current data columns in use: {', '.join(self.current_context_columns)}

New follow-up question: "{question}"

Analyze if this follow-up question requires:
1. Additional data columns beyond those currently in use
2. New data filtering criteria
3. Whether this is a clarification (conversational response) or requires new analysis

Return JSON with:
{{
    "analysis_type": "new_analysis" or "clarification",
    "additional_columns_needed": ["column1", "column2"] or [],
    "new_filtering_needed": true/false,
    "filtering_criteria": "description of new filters needed" or null,
    "reasoning": "brief explanation of the analysis approach"
}}

Available columns: {list(self.df.columns)}"""

            # Make API call for follow-up analysis
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": followup_analysis_prompt}],
                temperature=0.3,
                max_tokens=800
            )
            
            # Parse response
            response_text = self._parse_api_response(response, "Follow-up analysis")
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            json_str = response_text[start_idx:end_idx]
            followup_analysis = json.loads(json_str)
            
            self.window.after(0, self._handle_followup_analysis, followup_analysis, question)
            
        except Exception as e:
            self.window.after(0, self._handle_analysis_error, f"Follow-up analysis failed: {str(e)}")
    
    def _handle_followup_analysis(self, analysis, question):
        """Handle the results of follow-up analysis"""
        analysis_type = analysis.get("analysis_type", "clarification")
        additional_columns = analysis.get("additional_columns_needed", [])
        
        if analysis_type == "clarification":
            # Direct conversational response
            self.log_message("💬 Providing conversational response...")
            self._generate_conversational_response(question)
        else:
            # New analysis needed
            if additional_columns:
                self.log_message(f"📊 AI requests {len(additional_columns)} additional columns")
                self._request_additional_columns(additional_columns, analysis, question)
            else:
                # Use existing columns with new filtering
                self.log_message("🔄 Proceeding with existing columns...")
                self._perform_followup_analysis(question, self.current_context_columns, analysis)
    
    def _request_additional_columns(self, requested_columns, analysis, question):
        """Interactive request for additional columns"""
        reasoning = analysis.get("reasoning", "No reasoning provided")
        
        # Create approval dialog
        dialog = tk.Toplevel(self.window)
        dialog.title("Additional Data Requested")
        dialog.geometry("600x400")
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (
            self.window.winfo_rootx() + 50,
            self.window.winfo_rooty() + 50
        ))
        
        # Content
        tk.Label(dialog, text="AI requests additional data columns", 
                font=("Arial", 14, "bold")).pack(pady=10)
        
        tk.Label(dialog, text=f"Reasoning: {reasoning}", 
                wraplength=550, justify=tk.LEFT).pack(pady=5, padx=20)
        
        # Requested columns
        frame = ttk.LabelFrame(dialog, text="Requested Additional Columns", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.column_approval_vars = {}
        for col in requested_columns:
            if col in self.df.columns and col not in self.current_context_columns:
                var = tk.BooleanVar(value=True)
                self.column_approval_vars[col] = var
                
                cb_frame = tk.Frame(frame)
                cb_frame.pack(fill=tk.X, pady=2)
                
                cb = tk.Checkbutton(cb_frame, text=col, variable=var)
                cb.pack(side=tk.LEFT)
                
                # Show column description
                if col in COLUMN_METADATA:
                    desc = COLUMN_METADATA[col]['description']
                    tk.Label(cb_frame, text=f"({desc})", 
                            font=("Arial", 8), fg="gray").pack(side=tk.LEFT, padx=(10, 0))
        
        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def approve_columns():
            approved_columns = [col for col, var in self.column_approval_vars.items() if var.get()]
            all_columns = list(set(self.current_context_columns + approved_columns))
            dialog.destroy()
            self._perform_followup_analysis(question, all_columns, analysis)
        
        def reject_columns():
            dialog.destroy()
            self._perform_followup_analysis(question, self.current_context_columns, analysis)
        
        ttk.Button(btn_frame, text="✅ Approve & Continue", 
                  command=approve_columns).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="❌ Use Existing Data", 
                  command=reject_columns).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", 
                  command=lambda: [dialog.destroy(), self._enable_buttons()]).pack(side=tk.LEFT, padx=5)

    def _add_to_conversation_display(self, text, tag="ai_response"):
        """Add text to the conversation display"""
        self.results_text.config(state=tk.NORMAL)
        
        # Add separator if not the first message
        if self.results_text.get(1.0, tk.END).strip():
            self.results_text.insert(tk.END, "\n" + "─" * 50 + "\n", "separator")
        
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M")
        self.results_text.insert(tk.END, f"[{timestamp}] ", "system_message")
        
        # Add the main text
        self.results_text.insert(tk.END, text + "\n", tag)
        
        # Scroll to bottom
        self.results_text.see(tk.END)
        self.results_text.config(state=tk.DISABLED)
    
    def _generate_conversational_response(self, question):
        """Generate a conversational response for clarification questions"""
        try:
            conversation_context = self.get_conversation_context()
            
            conversational_prompt = f"""You are continuing a data analysis conversation. The user is asking for clarification or additional details about previous findings.

Conversation context:
{conversation_context}

User's clarification question: "{question}"

Provide a helpful, conversational response that:
1. Directly addresses their question
2. References previous findings when relevant
3. Is concise but informative
4. Maintains a friendly, professional tone

Do not perform new data analysis - just clarify or expand on what was already discussed."""

            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": conversational_prompt}],
                temperature=0.7,
                max_tokens=500
            )
            
            response_text = self._parse_api_response(response, "Conversational response")
            
            # Add to conversation and display
            self.add_to_conversation("ai_response", response_text)
            self.window.after(0, lambda: self._add_to_conversation_display(f"Assistant: {response_text}", "ai_response"))
            self.window.after(0, self._enable_buttons)
            self.window.after(0, lambda: self.log_message("💬 Conversational response provided"))
            
        except Exception as e:
            self.window.after(0, self._handle_analysis_error, f"Conversational response failed: {str(e)}")
    
    def _perform_followup_analysis(self, question, columns, analysis):
        """Perform new analysis for follow-up questions with retry logic"""
        try:
            # Update current context columns
            self.current_context_columns = columns
            
            # Apply any new filtering if needed
            working_df = self.df.copy()
            if analysis.get("new_filtering_needed"):
                # AI-driven filtering would go here
                # For now, we'll use the full dataset
                pass
            
            # Get conversation context
            conversation_context = self.get_conversation_context()
            
            # Check if chunking is needed for follow-up
            if self._check_if_chunking_needed(question, columns, len(working_df)):
                self.window.after(0, lambda: self.log_message("⚠️ Follow-up dataset too large for single analysis"))
                
                # Estimate tokens for user dialog
                estimated_tokens = self.estimate_prompt_tokens(question, columns, len(working_df))
                
                # Show user choice dialog
                user_choice = self._show_chunking_dialog(question, columns, estimated_tokens, len(working_df))
                
                if user_choice == "chunk":
                    # Perform chunked follow-up analysis
                    self.window.after(0, lambda: self.log_message("🔄 Starting chunked follow-up analysis..."))
                    self._perform_chunked_followup_analysis(question, columns, analysis)
                    return
                elif user_choice == "reduce":
                    # Continue with reduced dataset
                    max_rows = min(1000, len(working_df))
                    self.window.after(0, lambda: self.log_message(f"🔄 Continuing follow-up with reduced dataset ({max_rows:,} rows)"))
                    if len(working_df) > max_rows:
                        working_df = working_df.sample(n=max_rows, random_state=42)
                else:
                    # User cancelled
                    self.window.after(0, lambda: self.log_message("❌ Follow-up analysis cancelled by user"))
                    self.window.after(0, self._enable_buttons)
                    return
            
            # Implement retry logic similar to initial analysis
            max_rows = min(5000, len(working_df))  # Start with 5,000 rows for follow-ups
            row_limits = []
            
            # Generate row limits starting from max_rows, reducing by 300 each time, down to minimum
            # This gives us more granular steps and up to 15 attempts
            current_limit = max_rows
            min_rows = min(500, max_rows)  # Use actual dataset size if smaller than 500
            
            # Always include the full dataset size first
            row_limits.append(current_limit)
            
            # Generate additional limits only if we have more than the minimum
            if max_rows > min_rows and len(row_limits) < 15:
                current_limit -= 300
                while current_limit >= min_rows and len(row_limits) < 15:
                    row_limits.append(current_limit)
                    current_limit -= 300
                
                # Ensure we always have the minimum as the last option
                if row_limits[-1] != min_rows and len(row_limits) < 15:
                    row_limits.append(min_rows)
            
            # Remove duplicates and sort in descending order
            row_limits = sorted(list(set(row_limits)), reverse=True)
            
            self.window.after(0, lambda: self.log_message(f"📊 Follow-up retry strategy: {len(row_limits)} attempts from {max_rows:,} down to {min_rows:,} rows"))
            
            analysis_successful = False
            final_row_count = 0
            response_text = ""
            
            for attempt_num, limit in enumerate(row_limits, 1):
                try:
                    # Prepare data sample
                    if len(working_df) > limit:
                        current_sample = working_df.sample(n=limit, random_state=42)
                        self.window.after(0, lambda l=limit, a=attempt_num, t=len(row_limits): self.log_message(f"⚠️  Attempt {a}/{t}: Trying follow-up with {l:,} rows"))
                    else:
                        current_sample = working_df
                    
                    # Select only the needed columns
                    analysis_df = current_sample[columns].copy()
                    final_row_count = len(analysis_df)
                    
                    self.window.after(0, lambda: self.log_message(f"🎯 Analyzing follow-up with {final_row_count:,} rows and {len(columns)} columns"))
                    
                    # Convert to CSV string for API
                    csv_data = analysis_df.to_csv(index=False)
                    
                    # Estimate tokens for this attempt
                    base_prompt_tokens = self.count_tokens(f"""You are continuing a data analysis conversation for WordPress.com support data.

Previous conversation:
{conversation_context}

New follow-up question: "{question}"

Data provided: {final_row_count} rows with columns: {', '.join(columns)}

CSV Data:
""")
                    data_tokens = self.count_tokens(csv_data)
                    total_tokens = base_prompt_tokens + data_tokens
                    
                    # Check if tokens exceed limit
                    if total_tokens > self.MAX_TOKENS * 0.95:  # 95% safety margin
                        self.window.after(0, lambda: self.log_message(f"❌ Token limit exceeded: {total_tokens:,} tokens. Trying smaller sample..."))
                        continue
                    
                    self.window.after(0, lambda: self.log_message(f"📊 Estimated tokens: {total_tokens:,} (within limit)"))
                    
                    # Create follow-up analysis prompt
                    analysis_prompt = f"""You are continuing a data analysis conversation for WordPress.com support data.

Previous conversation:
{conversation_context}

New follow-up question: "{question}"

Data provided: {final_row_count} rows with columns: {', '.join(columns)}

CSV Data:
{csv_data}

Provide a CONCISE follow-up response that:
1. Directly answers the follow-up question
2. References previous findings briefly
3. Includes 2-3 key data points or examples
4. Keeps the response under 300 words

Format as a focused, conversational response - not a full report. Be specific but brief."""

                    client = openai.OpenAI(api_key=self.api_key)
                    response = client.chat.completions.create(
                        model="gpt-4.1",
                        messages=[{"role": "user", "content": analysis_prompt}],
                        temperature=0.3,
                        max_tokens=2000
                    )
                    
                    response_text = self._parse_api_response(response, "Follow-up data analysis")
                    analysis_successful = True
                    
                    self.window.after(0, lambda: self.log_message("✅ Follow-up analysis completed successfully!"))
                    break
                    
                except Exception as e:
                    if "context" in str(e).lower() or "token" in str(e).lower():
                        self.window.after(0, lambda l=limit, a=attempt_num, t=len(row_limits): self.log_message(f"⚠️  Attempt {a}/{t}: Context limit exceeded with {l:,} rows, trying smaller sample..."))
                        continue  # Try with fewer rows
                    else:
                        raise e  # Different error, don't retry
            
            if not analysis_successful:
                raise Exception("Failed to analyze follow-up question even with reduced dataset size")
            
            # Add to conversation and display
            self.add_to_conversation("ai_response", response_text, {
                "columns_used": columns,
                "rows_analyzed": final_row_count
            })
            
            self.window.after(0, lambda: self._add_to_conversation_display(f"Assistant: {response_text}", "ai_response"))
            self.window.after(0, self._enable_buttons)
            self.window.after(0, lambda: self.log_message(f"✅ Follow-up analysis complete ({final_row_count:,} rows, {len(columns)} columns)"))
            
        except Exception as e:
            self.window.after(0, self._handle_analysis_error, f"Follow-up analysis failed: {str(e)}")
    
    def _enable_buttons(self):
        """Re-enable UI buttons after analysis"""
        self.analyze_btn.config(state=tk.NORMAL)
        self.followup_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Ready for next question")
        
        # Clear question text for next input
        self.question_text.delete(1.0, tk.END)
        self.question_text.focus()


def open_talk_to_history(parent, api_key, start_date=None, end_date=None):
    """
    Open Talk to Data window with historical database data.
    
    This function loads data from the historical database and opens
    the Talk to Data interface for natural language querying.
    
    Args:
        parent: Parent Tkinter window
        api_key: OpenAI API key
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        TalkToDataWindow instance or None if failed
    """
    try:
        from data_store import get_data_store, DATA_STORE_AVAILABLE
        
        if not DATA_STORE_AVAILABLE:
            messagebox.showerror(
                "Feature Unavailable",
                "Historical data store is not available.\n\n"
                "Please ensure data_store.py is in the application directory."
            )
            return None
        
        data_store = get_data_store()
        
        # Get database stats
        stats = data_store.get_database_stats()
        
        if stats['total_tickets'] == 0:
            messagebox.showinfo(
                "No Historical Data",
                "No historical data found in the database.\n\n"
                "Please import some analysis results first using 'Import to History'."
            )
            return None
        
        # Load tickets from database
        df = data_store.get_tickets_dataframe(start_date=start_date, end_date=end_date)
        
        if df.empty:
            messagebox.showinfo(
                "No Data in Range",
                "No tickets found in the specified date range."
            )
            return None
        
        # Create data source name
        date_range = data_store.get_date_range()
        if date_range[0] and date_range[1]:
            source_name = f"Historical Database ({date_range[0]} to {date_range[1]})"
        else:
            source_name = f"Historical Database ({stats['total_tickets']:,} tickets)"
        
        # Open Talk to Data with historical data
        return TalkToDataWindow(
            parent=parent,
            csv_file_path=None,
            api_key=api_key,
            dataframe=df,
            data_source_name=source_name
        )
        
    except ImportError as e:
        messagebox.showerror(
            "Module Error",
            f"Could not import data store module:\n{str(e)}"
        )
        return None
    except Exception as e:
        messagebox.showerror(
            "Error",
            f"Failed to load historical data:\n{str(e)}"
        )
        return None


def main():
    """Main function for testing"""
    if len(sys.argv) != 3:
        print("Usage: python3 talktodata.py <csv_file> <api_key>")
        sys.exit(1)
        
    csv_file = sys.argv[1]
    api_key = sys.argv[2]
    
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    app = TalkToDataWindow(root, csv_file, api_key)
    root.mainloop()

if __name__ == "__main__":
    main() 