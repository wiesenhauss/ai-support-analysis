#!/usr/bin/env python3
"""
AI Support Analyzer - GUI Application
by @wiesenhauss

A beautiful GUI application for running customer support analysis with AI:
- Secure API key management with macOS Keychain integration
- Persistent settings storage in user's Application Support directory
- File selection and validation
- Analysis module selection
- Real-time progress tracking
- Live log display
- Cancel functionality with force stop
- Expandable settings system for custom prompts and configurations
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import subprocess
import os
import sys
from pathlib import Path
import queue
import time
import json
from datetime import datetime
import pandas as pd
import platform
import gc

# Import data store for historical analytics
try:
    from data_store import get_data_store, DataStore
    DATA_STORE_AVAILABLE = True
except ImportError:
    DATA_STORE_AVAILABLE = False

class SettingsManager:
    """Secure settings manager for macOS with Keychain integration."""
    
    def __init__(self, app_name="AI Support Analyzer"):
        self.app_name = app_name
        self.app_id = "com.automattic.ai-support-analyzer"
        
        # Determine the settings directory based on platform
        if platform.system() == "Darwin":  # macOS
            # Use ~/Library/Application Support/AI Support Analyzer/
            self.settings_dir = Path.home() / "Library" / "Application Support" / app_name
        elif platform.system() == "Windows":
            # Use %APPDATA%/AI Support Analyzer/
            self.settings_dir = Path(os.environ.get('APPDATA', Path.home())) / app_name
        else:  # Linux and others
            # Use ~/.config/AI Support Analyzer/
            self.settings_dir = Path.home() / ".config" / app_name
        
        # Create settings directory if it doesn't exist
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        
        # Settings file path
        self.settings_file = self.settings_dir / "settings.json"
        
        # Default settings structure
        self.default_settings = {
            "version": "1.0",
            "last_updated": None,
            "ui_preferences": {
                "last_file": "",
                "limit": "No limit",
                "analysis_options": {
                    'main_analysis': True,
                    'data_cleanup': True,
                    'predict_csat': True,
                    'topic_aggregator': True,
                    'csat_trends': True,
                    'product_feedback': True,
                    'goals_trends': True,
                    'custom_analysis': False,
                    'visualization': False
                },
                "window_geometry": "1000x800",
                "log_level": "INFO"
            },
            "custom_prompts": {
                "templates": {},
                "user_prompts": {}
            },
            "advanced_settings": {
                "api_timeout": 60,
                "max_retries": 3,
                "batch_size": 100,
                "temp_directory": ""
            }
        }
    
    def save_api_key_to_keychain(self, api_key):
        """Save API key to macOS Keychain (macOS only)."""
        if platform.system() != "Darwin":
            return False
            
        try:
            # Use security command to store in keychain
            cmd = [
                'security', 'add-generic-password',
                '-a', os.getlogin(),  # account name
                '-s', self.app_id,    # service name
                '-w', api_key,        # password (API key)
                '-U'                  # update if exists
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"Failed to save API key to keychain: {e}")
            return False
    
    def load_api_key_from_keychain(self):
        """Load API key from macOS Keychain (macOS only)."""
        if platform.system() != "Darwin":
            return None
            
        try:
            # Use security command to retrieve from keychain
            cmd = [
                'security', 'find-generic-password',
                '-a', os.getlogin(),  # account name
                '-s', self.app_id,    # service name
                '-w'                  # output password only
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return None
                
        except Exception as e:
            print(f"Failed to load API key from keychain: {e}")
            return None
    
    def delete_api_key_from_keychain(self):
        """Delete API key from macOS Keychain (macOS only)."""
        if platform.system() != "Darwin":
            return False
            
        try:
            cmd = [
                'security', 'delete-generic-password',
                '-a', os.getlogin(),  # account name
                '-s', self.app_id     # service name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"Failed to delete API key from keychain: {e}")
            return False
    
    def save_settings(self, settings_dict):
        """Save settings to the secure settings file."""
        try:
            # Load existing settings
            current_settings = self.load_settings()
            
            # Deep merge the new settings with existing ones
            merged_settings = self._deep_merge(current_settings, settings_dict)
            merged_settings["last_updated"] = datetime.now().isoformat()
            
            # Save to file
            with open(self.settings_file, 'w') as f:
                json.dump(merged_settings, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Failed to save settings: {e}")
            return False
    
    def load_settings(self):
        """Load settings from the secure settings file."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                
                # Merge with defaults to ensure all keys exist
                return self._deep_merge(self.default_settings, settings)
            else:
                # Return default settings if file doesn't exist
                return self.default_settings.copy()
                
        except Exception as e:
            print(f"Failed to load settings: {e}")
            return self.default_settings.copy()
    
    def _deep_merge(self, base_dict, update_dict):
        """Deep merge two dictionaries."""
        result = base_dict.copy()
        
        for key, value in update_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def save_custom_prompt(self, name, prompt, columns=None):
        """Save a custom prompt template."""
        settings = self.load_settings()
        
        settings["custom_prompts"]["user_prompts"][name] = {
            "prompt": prompt,
            "columns": columns or [],
            "created": datetime.now().isoformat(),
            "last_used": None
        }
        
        return self.save_settings(settings)
    
    def load_custom_prompts(self):
        """Load all custom prompt templates."""
        settings = self.load_settings()
        return settings.get("custom_prompts", {}).get("user_prompts", {})
    
    def delete_custom_prompt(self, name):
        """Delete a custom prompt template."""
        settings = self.load_settings()
        
        if name in settings.get("custom_prompts", {}).get("user_prompts", {}):
            del settings["custom_prompts"]["user_prompts"][name]
            return self.save_settings(settings)
        
        return False
    
    def get_settings_info(self):
        """Get information about the settings storage location."""
        return {
            "settings_directory": str(self.settings_dir),
            "settings_file": str(self.settings_file),
            "keychain_service": self.app_id if platform.system() == "Darwin" else None,
            "platform": platform.system()
        }

class AISupportAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Support Analyzer")
        self.root.geometry("1000x800")
        
        # Initialize settings manager
        self.settings_manager = SettingsManager()
        
        # Variables
        self.api_key_var = tk.StringVar()
        self.input_file_var = tk.StringVar()
        self.limit_var = tk.StringVar(value="No limit")
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready")
        
        # Analysis options
        self.analysis_options = {
            'main_analysis': tk.BooleanVar(value=True),
            'data_cleanup': tk.BooleanVar(value=True),
            'auto_import': tk.BooleanVar(value=True),  # Auto-import to history after analysis
            'predict_csat': tk.BooleanVar(value=True),
            'topic_aggregator': tk.BooleanVar(value=True),
            'csat_trends': tk.BooleanVar(value=True),
            'product_feedback': tk.BooleanVar(value=True),
            'goals_trends': tk.BooleanVar(value=True),
            'custom_analysis': tk.BooleanVar(value=False),
            'visualization': tk.BooleanVar(value=False)
        }
        
        # Custom analysis parameters
        self.custom_prompt = ""
        self.custom_columns = []
        
        # Process control
        self.process = None
        self.is_running = False
        self.cancel_requested = False
        self.log_queue = queue.Queue()
        self.input_file_dir = os.getcwd()  # Default to current directory
        self.input_file_full_path = ""  # Store full path internally
        
        # Performance optimization flags
        self._ui_update_pending = False
        self._last_ui_update = 0
        self._ui_update_throttle_ms = 16  # ~60fps max update rate
        self._log_monitor_active = False  # Track if log monitor is running
        self._max_log_lines = 10000  # Maximum lines in log widget to prevent memory issues
        
        self.setup_menu()
        self.setup_ui()
        self.load_settings()
        self.start_log_monitor()
        
        # macOS-specific optimizations (after UI is created)
        if platform.system() == "Darwin":
            self.root.after(100, self._apply_macos_optimizations)
        
        # Save settings when app closes
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _center_dialog_on_screen(self, dialog, width=None, height=None):
        """Center a dialog window on screen, ensuring it stays within view."""
        dialog.update_idletasks()
        
        # Get dialog dimensions
        if width is None:
            width = dialog.winfo_width()
        if height is None:
            height = dialog.winfo_height()
        
        # Get screen dimensions
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        
        # Calculate center position
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # Ensure dialog stays within screen bounds
        x = max(0, min(x, screen_width - width))
        y = max(0, min(y, screen_height - height))
        
        # Apply the position
        dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def _position_dialog_relative_to_parent(self, dialog, parent=None, width=None, height=None):
        """Position a dialog relative to parent window, ensuring it stays within view."""
        if parent is None:
            parent = self.root
            
        dialog.update_idletasks()
        
        # Get dialog dimensions
        if width is None:
            width = dialog.winfo_width()
        if height is None:
            height = dialog.winfo_height()
        
        # Get screen dimensions
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        
        # Force dialog to center on the primary screen
        # Use absolute positioning to avoid any coordinate system issues
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        
        # Ensure dialog stays within screen bounds
        x = min(x, screen_width - width)
        y = min(y, screen_height - height)
        
        # Apply the position using absolute coordinates
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Force the dialog to be visible by bringing it to front
        dialog.lift()
        dialog.focus_force()
        
        # Additional macOS-specific positioning fix
        if platform.system() == "Darwin":
            # On macOS, sometimes we need to force the window to be visible
            dialog.update_idletasks()
            dialog.deiconify()  # Ensure window is not minimized
            dialog.attributes('-topmost', True)  # Bring to front temporarily
            dialog.after(100, lambda: dialog.attributes('-topmost', False))  # Remove topmost after 100ms
    
    def _apply_macos_optimizations(self):
        """Apply macOS-specific performance optimizations."""
        try:
            # Enable high-DPI support for retina displays
            self.root.tk.call('tk', 'scaling', 2.0)
            
            # Optimize window rendering
            self.root.configure(bg='#f0f0f0')  # Use system background color
            
            # Reduce unnecessary redraws by optimizing widget creation
            # Use native macOS widgets where possible
            style = ttk.Style()
            style.theme_use('aqua')  # Use native macOS theme
            
            # Optimize text widget performance
            if hasattr(self, 'log_text'):
                # Configure text widget for better performance
                self.log_text.configure(
                    wrap=tk.WORD,
                    tabs='0.5i',
                    insertwidth=1,
                    highlightthickness=0,
                    relief=tk.FLAT
                )
                
        except Exception as e:
            # Fallback if optimizations fail
            print(f"macOS optimizations failed: {e}")
        
    def setup_menu(self):
        """Create the menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Manage API Keys", command=self.manage_api_keys)
        settings_menu.add_command(label="Custom Prompts", command=self.manage_custom_prompts)
        settings_menu.add_separator()
        settings_menu.add_command(label="Advanced Settings", command=self.show_advanced_settings)
        settings_menu.add_command(label="Settings Info", command=self.show_settings_info)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="How to Use", command=self.show_help_usage)
        help_menu.add_command(label="CSV Format Guide", command=self.show_help_csv)
        help_menu.add_command(label="Analysis Details", command=self.show_help_analysis)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
        
    def setup_ui(self):
        """Create the user interface."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="AI Support Analyzer", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # API Key Section
        api_frame = ttk.LabelFrame(main_frame, text="OpenAI API Configuration", padding="10")
        api_frame.pack(fill=tk.X, pady=(0, 10))
        
        api_inner = ttk.Frame(api_frame)
        api_inner.pack(fill=tk.X)
        
        ttk.Label(api_inner, text="API Key:").pack(side=tk.LEFT)
        self.api_entry = ttk.Entry(api_inner, textvariable=self.api_key_var, show="*", width=50)
        self.api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))
        
        # API key buttons
        api_buttons = ttk.Frame(api_inner)
        api_buttons.pack(side=tk.RIGHT)
        
        ttk.Button(api_buttons, text="Show", command=self.toggle_api_visibility).pack(side=tk.LEFT, padx=(0, 5))
        self.save_key_button = ttk.Button(api_buttons, text="Save", command=self.save_api_key)
        self.save_key_button.pack(side=tk.LEFT)
        
        # API key status
        self.api_status_label = ttk.Label(api_frame, text="🔑 API key will be saved securely", 
                                         font=('Arial', 9), foreground='gray')
        self.api_status_label.pack(pady=(5, 0))
        
        # File Section
        file_frame = ttk.LabelFrame(main_frame, text="Input Data", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        file_inner = ttk.Frame(file_frame)
        file_inner.pack(fill=tk.X)
        
        ttk.Label(file_inner, text="CSV File:").pack(side=tk.LEFT)
        self.file_entry = ttk.Entry(file_inner, textvariable=self.input_file_var, width=50)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))
        self.file_entry.bind('<Return>', self.on_file_path_entered)
        self.file_entry.bind('<FocusOut>', self.on_file_path_entered)
        ttk.Button(file_inner, text="Browse", command=self.browse_file).pack(side=tk.RIGHT)
        
        # File info
        self.file_info_label = ttk.Label(file_frame, text="📁 Select file using Browse button, or type/paste path directly", 
                                        font=('Arial', 9))
        self.file_info_label.pack(pady=(5, 0))
        
        # Analysis Options Section
        analysis_frame = ttk.LabelFrame(main_frame, text="Analysis Modules", padding="10")
        analysis_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Analysis descriptions
        analysis_descriptions = {
            'main_analysis': 'Core CSAT & Sentiment Analysis',
            'data_cleanup': 'Data Cleanup & Validation',
            'predict_csat': 'CSAT Prediction Analysis',
            'topic_aggregator': 'Topic Categorization',
            'csat_trends': 'CSAT Trends Analysis',
            'product_feedback': 'Product Feedback Analysis',
            'goals_trends': 'Customer Goals Analysis',
            'custom_analysis': 'Custom Analysis (configure below)',
            'visualization': 'Generate Visualizations'
        }
        
        # Analyses that support custom prompts
        self.configurable_analyses = {
            'topic_aggregator': 'Topic Categorization',
            'csat_trends': 'CSAT Trends Analysis', 
            'product_feedback': 'Product Feedback Analysis',
            'goals_trends': 'Customer Goals Analysis'
        }
        
        # Create checkboxes in two columns
        checkbox_frame = ttk.Frame(analysis_frame)
        checkbox_frame.pack(fill=tk.X)
        
        left_frame = ttk.Frame(checkbox_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        right_frame = ttk.Frame(checkbox_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        items = list(analysis_descriptions.items())
        for i, (key, description) in enumerate(items):
            parent = left_frame if i < len(items) // 2 else right_frame
            
            if key == 'custom_analysis':
                # Special handling for custom analysis
                custom_frame = ttk.Frame(parent)
                custom_frame.pack(anchor=tk.W, pady=2, fill=tk.X)
                
                cb = ttk.Checkbutton(custom_frame, text=description, variable=self.analysis_options[key])
                cb.pack(side=tk.LEFT)
                
                self.config_button = ttk.Button(custom_frame, text="Configure", 
                                              command=self.configure_custom_analysis, 
                                              state=tk.DISABLED)
                self.config_button.pack(side=tk.LEFT, padx=(10, 0))
                
                # Bind checkbox to enable/disable configure button
                self.analysis_options[key].trace('w', self.on_custom_analysis_toggle)
            elif key in self.configurable_analyses:
                # Configurable analysis with custom prompt support
                config_frame = ttk.Frame(parent)
                config_frame.pack(anchor=tk.W, pady=2, fill=tk.X)
                
                cb = ttk.Checkbutton(config_frame, text=description, variable=self.analysis_options[key])
                cb.pack(side=tk.LEFT)
                
                config_btn = ttk.Button(config_frame, text="Configure", 
                                      command=lambda k=key: self.configure_analysis_prompt(k))
                config_btn.pack(side=tk.LEFT, padx=(10, 0))
            else:
                cb = ttk.Checkbutton(parent, text=description, variable=self.analysis_options[key])
                cb.pack(anchor=tk.W, pady=2)
        
        # Select All / Deselect All buttons
        button_frame = ttk.Frame(analysis_frame)
        button_frame.pack(pady=(10, 0))
        
        ttk.Button(button_frame, text="Select All", command=self.select_all_analysis).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Deselect All", command=self.deselect_all_analysis).pack(side=tk.LEFT)
        
        # Auto-import option
        ttk.Separator(analysis_frame, orient='horizontal').pack(fill=tk.X, pady=(10, 5))
        auto_import_cb = ttk.Checkbutton(
            analysis_frame, 
            text="📊 Auto-import results to History after analysis completes",
            variable=self.analysis_options['auto_import']
        )
        auto_import_cb.pack(anchor=tk.W)
        
        # Limit Section
        limit_frame = ttk.LabelFrame(main_frame, text="Processing Options", padding="10")
        limit_frame.pack(fill=tk.X, pady=(0, 10))
        
        limit_inner = ttk.Frame(limit_frame)
        limit_inner.pack(fill=tk.X)
        
        ttk.Label(limit_inner, text="Record Limit:").pack(side=tk.LEFT)
        
        self.limit_combo = ttk.Combobox(limit_inner, textvariable=self.limit_var, 
                                       values=["No limit", "1000", "5000", "10000", "25000", "50000", "Custom..."],
                                       state="readonly", width=15)
        self.limit_combo.pack(side=tk.LEFT, padx=(10, 10))
        self.limit_combo.bind('<<ComboboxSelected>>', self.on_limit_change)
        
        self.custom_limit_entry = ttk.Entry(limit_inner, width=10)
        
        info_label = ttk.Label(limit_frame, text="💡 Limit records for faster processing (useful for testing)", 
                              font=('Arial', 9))
        info_label.pack(pady=(5, 0))
        
        # Control Buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(pady=20)
        
        self.start_button = ttk.Button(control_frame, text="🚀 Start Analysis", command=self.start_analysis)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.cancel_button = ttk.Button(control_frame, text="⏹ Cancel", command=self.cancel_analysis, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.force_stop_button = ttk.Button(control_frame, text="🛑 Force Stop", command=self.force_stop_analysis, state=tk.DISABLED)
        # Initially hidden, will show if process seems stuck
        
        ttk.Button(control_frame, text="📁 Open Output Folder", command=self.open_output_folder).pack(side=tk.LEFT, padx=(0, 10))
        
        self.talk_to_data_button = ttk.Button(control_frame, text="💬 Talk to Data", command=self.open_talk_to_data, state=tk.DISABLED)
        self.talk_to_data_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.import_history_button = ttk.Button(control_frame, text="📊 Import to History", command=self.import_to_history, state=tk.DISABLED)
        self.import_history_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.history_dashboard_button = ttk.Button(control_frame, text="📈 History Dashboard", command=self.open_history_dashboard)
        self.history_dashboard_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.insights_dashboard_button = ttk.Button(control_frame, text="💡 Product Insights", command=self.open_insights_dashboard)
        self.insights_dashboard_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.talk_to_history_button = ttk.Button(control_frame, text="🗣️ Talk to History", command=self.open_talk_to_history)
        self.talk_to_history_button.pack(side=tk.LEFT)
        
        # Progress Section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.progress_label = ttk.Label(progress_frame, text="Ready to start analysis")
        self.progress_label.pack()
        
        # Log Section
        log_frame = ttk.LabelFrame(main_frame, text="Analysis Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, state=tk.DISABLED, 
                                                 font=('Courier', 12))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        # Configure text widget for better performance
        self.log_text.configure(
            wrap=tk.WORD,
            tabs='0.5i',
            insertwidth=1,
            highlightthickness=0,
            relief=tk.FLAT,
            maxundo=-1  # Disable undo for better performance
        )
        
        # Log buttons
        log_buttons = ttk.Frame(log_frame)
        log_buttons.pack(pady=(5, 0))
        
        ttk.Button(log_buttons, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(log_buttons, text="Save Log", command=self.save_log).pack(side=tk.LEFT)
        
        # Status Bar
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_label.pack(fill=tk.X)
        
    def toggle_api_visibility(self):
        if self.api_entry['show'] == '*':
            self.api_entry['show'] = ''
        else:
            self.api_entry['show'] = '*'
            
    def browse_file(self):
        """Open file browser for CSV selection with macOS compatibility."""
        # Disable the browse button temporarily to prevent multiple dialogs
        browse_button = None
        for widget in self.root.winfo_children():
            if hasattr(widget, 'winfo_children'):
                for child in widget.winfo_children():
                    if hasattr(child, 'winfo_children'):
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, ttk.Button) and 'Browse' in str(grandchild.cget('text')):
                                browse_button = grandchild
                                break
        
        if browse_button:
            browse_button.config(state=tk.DISABLED, text="Opening...")
        
        # Use a thread to prevent UI freezing
        def file_dialog_thread():
            try:
                self.root.update()  # Ensure UI is responsive
                
                filename = filedialog.askopenfilename(
                    title="Select Support Data CSV File",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                    parent=self.root
                )
                
                # Use queue to communicate back to main thread
                if filename:
                    self.log_queue.put(('file_selected', filename))
                else:
                    self.log_queue.put(('file_cancelled', None))
                    
            except Exception as e:
                # If tkinter dialog fails, try alternative approach
                self.log_queue.put(('file_error', str(e)))
            finally:
                # Re-enable the browse button
                self.log_queue.put(('browse_done', None))
        
        # Start the file dialog in a separate thread
        import threading
        dialog_thread = threading.Thread(target=file_dialog_thread, daemon=True)
        dialog_thread.start()
    
    def show_manual_file_input(self):
        """Show a manual file input dialog as fallback."""
        import tkinter.simpledialog as simpledialog
        
        try:
            # Create a simple dialog for manual path entry
            filename = simpledialog.askstring(
                "File Path", 
                "Please enter the full path to your CSV file:\n\n(You can drag and drop the file to Terminal to get the path)",
                parent=self.root
            )
            
            if filename:
                # Clean up the path (remove quotes, normalize)
                filename = self.normalize_file_path(filename)
                
                if os.path.exists(filename):
                    # Store full path internally, display only filename
                    self.input_file_full_path = filename
                    self.input_file_var.set(os.path.basename(filename))
                    self.validate_file(filename)
                    self.log_message(f"📁 File manually entered: {os.path.basename(filename)}")
                else:
                    messagebox.showerror("File Not Found", f"Could not find file: {filename}")
            
        except Exception as e:
            self.log_message(f"❌ Manual file input failed: {str(e)}")
            messagebox.showerror("Error", "File selection failed. Please try entering the path directly in the text field.")
    
    def normalize_file_path(self, file_path):
        """Normalize file path to handle spaces and special characters."""
        if not file_path:
            return file_path
        
        # Remove quotes if they exist
        file_path = file_path.strip().strip('"').strip("'")
        
        # Handle escaped characters (remove backslashes before spaces and special chars)
        file_path = file_path.replace('\\ ', ' ')
        file_path = file_path.replace('\\(', '(')
        file_path = file_path.replace('\\)', ')')
        file_path = file_path.replace('\\-', '-')
        
        # Normalize and expand the path
        file_path = os.path.expanduser(file_path)
        file_path = os.path.normpath(file_path)
        
        return file_path
            
    def validate_file(self, filename):
        """Validate selected file with async processing for better performance."""
        # Show immediate feedback
        self.file_info_label.config(
            text="🔄 Validating file...",
            foreground='blue'
        )
        
        # Use threading for file validation to prevent UI blocking
        def validate_thread():
            try:
                size_mb = os.path.getsize(filename) / (1024 * 1024)
                
                # Try to read first few lines to validate CSV
                with open(filename, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    second_line = f.readline()
                    
                if ',' in first_line:  # Basic CSV validation
                    cols = len(first_line.split(','))
                    result = {
                        'success': True,
                        'message': f"✅ CSV file loaded: {cols} columns, {size_mb:.1f} MB",
                        'color': 'green',
                        'log_message': f"File loaded: {os.path.basename(filename)} ({size_mb:.1f} MB)",
                        'filename': filename
                    }
                else:
                    result = {
                        'success': False,
                        'message': "⚠️ File may not be a valid CSV",
                        'color': 'orange',
                        'log_message': None,
                        'filename': filename
                    }
                    
            except Exception as e:
                result = {
                    'success': False,
                    'message': f"❌ Error reading file: {str(e)[:50]}...",
                    'color': 'red',
                    'log_message': None,
                    'filename': filename
                }
            
            # Queue the result for main thread processing
            self.log_queue.put(('file_validation_result', result))
        
        # Start validation in background thread
        import threading
        validation_thread = threading.Thread(target=validate_thread, daemon=True)
        validation_thread.start()
            
    def on_limit_change(self, event):
        """Handle limit selection change."""  
        if self.limit_var.get() == "Custom...":
            self.custom_limit_entry.pack(side=tk.LEFT, padx=(10, 0))
            self.custom_limit_entry.focus()
        else:
            self.custom_limit_entry.pack_forget()
            
    def select_all_analysis(self):
        for var in self.analysis_options.values():
            var.set(True)
            
    def deselect_all_analysis(self):
        for var in self.analysis_options.values():
            var.set(False)
            
    def start_analysis(self):
        # Validate inputs
        if not self.api_key_var.get().strip():
            messagebox.showerror("Error", "Please enter your OpenAI API key")
            return
            
        if not self.input_file_full_path:
            messagebox.showerror("Error", "Please select an input CSV file")
            return
            
        if not os.path.exists(self.input_file_full_path):
            messagebox.showerror("Error", "Selected file does not exist")
            return
            
        # Check if any analysis is selected
        if not any(var.get() for var in self.analysis_options.values()):
            messagebox.showerror("Error", "Please select at least one analysis module")
            return
        
        # Validate custom analysis configuration if selected
        if self.analysis_options['custom_analysis'].get():
            if not self.custom_prompt.strip() or not self.custom_columns:
                messagebox.showerror("Custom Analysis Not Configured", 
                                   "Custom analysis is selected but not properly configured.\n"
                                   "Please click 'Configure' to set up your custom analysis.")
                return
        
        # Check if the user is trying to run dependent analyses without core analysis
        core_selected = self.analysis_options['main_analysis'].get()
        cleanup_selected = self.analysis_options['data_cleanup'].get()
        prediction_selected = self.analysis_options['predict_csat'].get()
        topic_selected = self.analysis_options['topic_aggregator'].get()
        
        # Warn about dependencies when core analysis is not selected
        if not core_selected and (cleanup_selected or prediction_selected or topic_selected):
            result = messagebox.askyesno("Loading Pre-Analyzed File?", 
                                       "You've selected analysis modules that typically require core analysis, "
                                       "but 'Core CSAT & Sentiment Analysis' is not selected.\n\n"
                                       "This suggests you're loading a file that has already been processed.\n\n"
                                       "Is your input file already analyzed (contains columns like CSAT_RATING, "
                                       "OVERALL_SENTIMENT, etc.)?\n\n"
                                       "Click 'Yes' if loading pre-analyzed data.\n"
                                       "Click 'No' to go back and select core analysis.")
            if not result:
                return
        
        # Save settings
        self.save_settings()
        
        self.is_running = True
        self.cancel_requested = False
        self.start_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.force_stop_button.config(state=tk.DISABLED)
        self.force_stop_button.pack_forget()  # Hide force stop button initially
        self.progress_bar.start()
        self.status_var.set("Running analysis...")
        
        self.log_message("=" * 60)
        self.log_message("🚀 Starting WordPress Support Analysis")
        self.log_message(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Log selected analyses
        selected = [name.replace('_', ' ').title() for name, var in self.analysis_options.items() if var.get()]
        self.log_message(f"📋 Selected analyses: {', '.join(selected)}")
        self.log_message("=" * 60)
        
        # Start analysis in background thread
        analysis_thread = threading.Thread(target=self.run_analysis, daemon=True)
        analysis_thread.start()
        
    def run_analysis(self):
        try:
            # Set up environment
            os.environ['OPENAI_API_KEY'] = self.api_key_var.get().strip()
            
            input_file = self.input_file_full_path
            limit = self.get_limit_value()
            
            self.log_queue.put(('log', f"🏃 Starting analysis pipeline..."))
            if limit:
                self.log_queue.put(('log', f"🔢 Record limit: {limit:,}"))
            
            # Run the analysis pipeline step by step
            success = self.run_analysis_pipeline(input_file, limit)
            
            if success:
                self.log_queue.put(('status', 'Analysis completed successfully! ✅'))
                self.log_queue.put(('log', '=' * 60))
                self.log_queue.put(('log', '✅ Analysis completed successfully!'))
                self.log_queue.put(('log', f'📅 Finished at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'))
                self.log_queue.put(('log', '📁 Check the output files in this folder'))
                self.log_queue.put(('log', '=' * 60))
                
                # Auto-import to history if enabled
                if self.analysis_options['auto_import'].get():
                    self.log_queue.put(('auto_import', self.input_file_dir))
            else:
                self.log_queue.put(('status', 'Analysis failed ❌'))
                
        except Exception as e:
            import traceback
            print(f"[DEBUG] EXCEPTION in run_analysis: {str(e)}", flush=True)
            print(traceback.format_exc(), flush=True)
            self.log_queue.put(('log', f"❌ Error: {str(e)}"))
            self.log_queue.put(('status', 'Analysis failed ❌'))
            
        finally:
            self.log_queue.put(('finished', None))
            
    def run_analysis_pipeline(self, input_file, limit=None):
        """Run the analysis pipeline based on selected modules."""
        try:
            # Get the directory where scripts are located
            script_dir = self.get_script_directory()
            
            # Get the directory of the input file for finding output files
            self.input_file_dir = os.path.dirname(os.path.abspath(input_file))
            
            # Change to script directory for execution
            original_cwd = os.getcwd()
            os.chdir(script_dir)
            
            # Determine the pipeline path based on selected analyses
            limit_args = [f"-limit={limit}"] if limit else []
            current_file = input_file
            step_counter = 1
            
            # Check what type of input file we have and what we need to run
            need_core_analysis = self.analysis_options['main_analysis'].get()
            need_data_cleanup = self.analysis_options['data_cleanup'].get()
            need_prediction = self.analysis_options['predict_csat'].get()
            need_topic_aggregation = self.analysis_options['topic_aggregator'].get()
            
            # If we need core analysis, start from the beginning
            if need_core_analysis:
                # Step 1: Pre-cleanup (always needed if doing core analysis)
                self.log_queue.put(('log', f"📋 Step {step_counter}: Running initial data cleanup..."))
                if self.cancel_requested:
                    self.log_queue.put(('log', "⏹ Analysis cancelled by user"))
                    return False
                if not self.run_python_script("support-data-precleanup.py", [f"-file={current_file}"]):
                    print(f"[DEBUG] precleanup script returned False", flush=True)
                    return False
                
                print(f"[DEBUG] precleanup script returned True, continuing...", flush=True)
                
                # Aggressive memory cleanup after each script
                gc.collect()
                
                print(f"[DEBUG] Looking for preclean file in: {self.input_file_dir}", flush=True)
                # Find the cleaned input file
                current_file = self.find_latest_file("*-preclean*.csv", search_dir=self.input_file_dir)
                print(f"[DEBUG] find_latest_file returned: {current_file}", flush=True)
                if not current_file:
                    self.log_queue.put(('log', "❌ Could not find pre-cleaned file"))
                    # Try to predict what the filename should be
                    original_name = os.path.splitext(os.path.basename(input_file))[0]
                    expected_file = os.path.join(self.input_file_dir, f"{original_name}-preclean.csv")
                    self.log_queue.put(('log', f"   💡 Expected file: {expected_file}"))
                    if os.path.exists(expected_file):
                        self.log_queue.put(('log', f"   ✅ Found expected file, using it"))
                        current_file = expected_file
                    else:
                        self.log_queue.put(('log', f"   ❌ Expected file does not exist either"))
                        return False
                step_counter += 1
                print(f"[DEBUG] Moving to Step 2, step_counter={step_counter}", flush=True)
                
                # Step 2: Main analysis
                self.log_queue.put(('log', f"📋 Step {step_counter}: Running core CSAT analysis..."))
                print(f"[DEBUG] Queued Step 2 log message", flush=True)
                if self.cancel_requested:
                    self.log_queue.put(('log', "⏹ Analysis cancelled by user"))
                    print(f"[DEBUG] Cancelled before main-analysis", flush=True)
                    return False
                print(f"[DEBUG] About to run main-analysis-process.py with file: {current_file}", flush=True)
                if not self.run_python_script("main-analysis-process.py", [f"-file={current_file}"]):
                    return False
                
                # Aggressive memory cleanup after main analysis (largest memory user)
                gc.collect()
                gc.collect()  # Second pass for large DataFrames
                
                # Find the analysis output
                current_file = self.find_latest_file("*support-analysis-output*.csv", search_dir=self.input_file_dir)
                if not current_file:
                    self.log_queue.put(('log', "❌ Could not find analysis output file"))
                    return False
                step_counter += 1
            else:
                # User is loading an already-analyzed file
                self.log_queue.put(('log', "📋 Using pre-analyzed input file..."))
                self.log_queue.put(('log', f"   Input: {os.path.basename(current_file)}"))
            
            # Step: Post-analysis cleanup (if needed and we have analysis output)
            if need_data_cleanup and need_core_analysis:
                self.log_queue.put(('log', f"📋 Step {step_counter}: Running post-analysis cleanup..."))
                if self.cancel_requested:
                    self.log_queue.put(('log', "⏹ Analysis cancelled by user"))
                    return False
                if not self.run_python_script("support-data-cleanup.py", [f"-file={current_file}"]):
                    return False
                
                # Memory cleanup
                gc.collect()
                
                # Find the cleaned file
                current_file = self.find_latest_file("*-clean*.csv", search_dir=self.input_file_dir)
                if not current_file:
                    self.log_queue.put(('log', "❌ Could not find cleaned file"))
                    return False
                step_counter += 1
            
            # Step: CSAT prediction (if needed)
            if need_prediction:
                self.log_queue.put(('log', f"📋 Step {step_counter}: Running CSAT prediction..."))
                if self.cancel_requested:
                    self.log_queue.put(('log', "⏹ Analysis cancelled by user"))
                    return False
                if not self.run_python_script("predict_csat.py", [f"-file={current_file}"]):
                    return False
                
                # Find the predictive file
                current_file = self.find_latest_file("*support-analysis-output-predictive-csat*.csv", search_dir=self.input_file_dir)
                if not current_file:
                    self.log_queue.put(('log', "❌ Could not find predictive CSAT file"))
                    return False
                step_counter += 1
            
            # Step: Topic aggregation (if needed)
            if need_topic_aggregation:
                self.log_queue.put(('log', f"📋 Step {step_counter}: Running topic aggregation..."))
                if self.cancel_requested:
                    self.log_queue.put(('log', "⏹ Analysis cancelled by user"))
                    return False
                
                # Get custom prompt if configured
                custom_prompt_args = self.get_custom_prompt_args('topic_aggregator')
                args = [f"-file={current_file}"] + custom_prompt_args
                
                if not self.run_python_script("topic-aggregator.py", args):
                    return False
                step_counter += 1
            
            # Trend analyses (independent of previous steps)
            if self.analysis_options['csat_trends'].get():
                self.log_queue.put(('log', f"📋 Step {step_counter}: Running CSAT trends analysis..."))
                if self.cancel_requested:
                    self.log_queue.put(('log', "⏹ Analysis cancelled by user"))
                    return False
                
                # Get custom prompt if configured
                custom_prompt_args = self.get_custom_prompt_args('csat_trends')
                args = [f"-file={current_file}"] + limit_args + custom_prompt_args
                
                if not self.run_python_script("csat-trends.py", args):
                    return False
                step_counter += 1
            
            if self.analysis_options['product_feedback'].get():
                self.log_queue.put(('log', f"📋 Step {step_counter}: Running product feedback trends..."))
                if self.cancel_requested:
                    self.log_queue.put(('log', "⏹ Analysis cancelled by user"))
                    return False
                
                # Get custom prompt if configured
                custom_prompt_args = self.get_custom_prompt_args('product_feedback')
                args = [f"-file={current_file}"] + limit_args + custom_prompt_args
                
                if not self.run_python_script("product-feedback-trends.py", args):
                    return False
                step_counter += 1
            
            if self.analysis_options['goals_trends'].get():
                self.log_queue.put(('log', f"📋 Step {step_counter}: Running goals trends analysis..."))
                if self.cancel_requested:
                    self.log_queue.put(('log', "⏹ Analysis cancelled by user"))
                    return False
                
                # Get custom prompt if configured
                custom_prompt_args = self.get_custom_prompt_args('goals_trends')
                args = [f"-file={current_file}"] + limit_args + custom_prompt_args
                
                if not self.run_python_script("goals-trends.py", args):
                    return False
                step_counter += 1
            
            # Custom analysis (if configured)
            if self.analysis_options['custom_analysis'].get():
                if not self.custom_prompt.strip() or not self.custom_columns:
                    self.log_queue.put(('log', "⚠️  Custom analysis skipped - not configured properly"))
                else:
                    self.log_queue.put(('log', f"📋 Step {step_counter}: Running custom analysis..."))
                    if self.cancel_requested:
                        self.log_queue.put(('log', "⏹ Analysis cancelled by user"))
                        return False
                    
                    # For custom analysis, use the original input file if no other analyses were run
                    # This allows custom analysis to work with any CSV structure
                    analysis_file = current_file
                    if current_file == input_file:
                        self.log_queue.put(('log', f"   📁 Using original input file: {os.path.basename(input_file)}"))
                    else:
                        self.log_queue.put(('log', f"   📁 Using processed file: {os.path.basename(current_file)}"))
                    
                    # Build arguments for custom analysis
                    custom_args = [
                        f"-file={analysis_file}",
                        f"-prompt={self.custom_prompt}",
                        f"-columns={','.join(self.custom_columns)}"
                    ] + limit_args
                    
                    if not self.run_python_script("custom-analysis.py", custom_args):
                        self.log_queue.put(('log', "⚠️  Custom analysis failed, but continuing..."))
                    step_counter += 1
            
            # Optional visualization
            if self.analysis_options['visualization'].get():
                self.log_queue.put(('log', f"📋 Step {step_counter}: Generating visualizations..."))
                if not self.cancel_requested:
                    if not self.run_python_script("visualize-overall-sentiment.py", [f"-file={current_file}"]):
                        self.log_queue.put(('log', "⚠️  Visualization step failed, but continuing..."))
                step_counter += 1
            
            # Restore working directory
            os.chdir(original_cwd)
            
            # Final aggressive cleanup after entire pipeline
            gc.collect()
            gc.collect()  # Second pass
            
            return True
            
        except Exception as e:
            import traceback
            print(f"[DEBUG] EXCEPTION in run_analysis_pipeline: {str(e)}", flush=True)
            print(traceback.format_exc(), flush=True)
            self.log_queue.put(('log', f"❌ Pipeline error: {str(e)}"))
            os.chdir(original_cwd)
            return False
            
    def run_python_script(self, script_name, args):
        """Run a Python script in a separate subprocess for memory isolation."""
        original_cwd = os.getcwd()
        process = None
        stdout_lines = None
        stderr_lines = None
        stdout_lock = None
        stderr_lock = None
        stdout_thread = None
        stderr_thread = None
        try:
            # Determine correct Python executable
            if hasattr(sys, '_MEIPASS'):
                # We're in a PyInstaller bundle - need to find system Python
                python_executable = self.find_system_python()
            else:
                # Running from source - use current Python
                python_executable = sys.executable
            
            # Get the full path to the script
            script_dir = self.get_script_directory()
            script_path = os.path.join(script_dir, script_name)
            
            # Verify script exists
            if not os.path.exists(script_path):
                self.log_queue.put(('log', f"   ❌ Script not found: {script_path}"))
                return False
            
            # Change to input file directory to ensure output files are created there
            if hasattr(self, 'input_file_dir') and self.input_file_dir:
                os.chdir(self.input_file_dir)
                self.log_queue.put(('log', f"   Changed to input directory: {self.input_file_dir}"))
            
            # Build command
            command = [python_executable, script_path] + args
            
            self.log_queue.put(('log', f"   Running: {script_name} {' '.join(args)}"))
            self.log_queue.put(('log', f"   Python: {python_executable}"))
            self.log_queue.put(('log', f"   Working directory: {os.getcwd()}"))
            
            # Set up environment
            env = os.environ.copy()
            env['OPENAI_API_KEY'] = self.api_key_var.get().strip()
            # Add script directory to Python path so imports work
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = f"{script_dir}:{env['PYTHONPATH']}"
            else:
                env['PYTHONPATH'] = script_dir
            
            start_time = time.time()
            
            # Run script in subprocess for memory isolation
            # Use Popen with real-time output streaming to avoid memory buildup
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            # Stream output in real-time to avoid accumulating large buffers
            # Use threading to read stdout/stderr without blocking
            import threading
            
            stdout_lines = []
            stderr_lines = []
            stdout_lock = threading.Lock()
            stderr_lock = threading.Lock()
            
            def read_stdout():
                """Read stdout line by line."""
                try:
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            line = line.rstrip()
                            with stdout_lock:
                                stdout_lines.append(line)
                            if line.strip():
                                self.log_queue.put(('log', f"   {line.strip()}"))
                except:
                    pass
                finally:
                    process.stdout.close()
            
            def read_stderr():
                """Read stderr line by line."""
                try:
                    for line in iter(process.stderr.readline, ''):
                        if line:
                            line = line.rstrip()
                            with stderr_lock:
                                stderr_lines.append(line)
                            if line.strip():
                                self.log_queue.put(('log', f"   ⚠️  {line.strip()}"))
                except:
                    pass
                finally:
                    process.stderr.close()
            
            # Start reader threads
            stdout_thread = threading.Thread(target=read_stdout, daemon=True)
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stdout_thread.start()
            stderr_thread.start()
            
            # Wait for process to complete, checking for cancellation
            while process.poll() is None:
                if self.cancel_requested:
                    process.terminate()
                    process.wait(timeout=5)
                    self.log_queue.put(('log', f"   ⏹ Script cancelled"))
                    return False
                time.sleep(0.1)  # Small sleep to avoid busy-waiting
            
            # Wait for reader threads to finish
            stdout_thread.join(timeout=2)
            stderr_thread.join(timeout=2)
            
            # Check return code
            return_code = process.returncode
            elapsed_time = time.time() - start_time
            elapsed_mins = int(elapsed_time / 60)
            
            # Debug: Print return code to terminal for troubleshooting
            print(f"[DEBUG] {script_name} finished with return code: {return_code}", flush=True)
            
            if return_code == 0:
                print(f"[DEBUG] About to log success message for {script_name}", flush=True)
                if elapsed_mins > 0:
                    self.log_queue.put(('log', f"   ✅ {script_name} completed in {elapsed_mins}m {elapsed_time%60:.1f}s"))
                else:
                    self.log_queue.put(('log', f"   ✅ {script_name} completed in {elapsed_time:.1f}s"))
                print(f"[DEBUG] Success message queued, about to cleanup for {script_name}", flush=True)
                
                # Aggressive memory cleanup after script completion
                if stdout_lock and stdout_lines:
                    with stdout_lock:
                        stdout_lines.clear()
                if stderr_lock and stderr_lines:
                    with stderr_lock:
                        stderr_lines.clear()
                del stdout_lines, stderr_lines, stdout_lock, stderr_lock
                gc.collect()
                
                print(f"[DEBUG] run_python_script returning True for {script_name}", flush=True)
                return True
            else:
                print(f"[DEBUG] {script_name} FAILED with exit code: {return_code}", flush=True)
                self.log_queue.put(('log', f"   ❌ {script_name} failed with exit code {return_code}"))
                if stderr_lines:
                    for line in stderr_lines[-10:]:  # Show last 10 error lines
                        self.log_queue.put(('log', f"   ⚠️  {line}"))
                
                # Cleanup even on failure
                if stdout_lock and stdout_lines:
                    try:
                        with stdout_lock:
                            stdout_lines.clear()
                    except:
                        pass
                if stderr_lock and stderr_lines:
                    try:
                        with stderr_lock:
                            stderr_lines.clear()
                    except:
                        pass
                del stdout_lines, stderr_lines, stdout_lock, stderr_lock
                gc.collect()
                
                return False
                
        except subprocess.TimeoutExpired:
            if process:
                process.kill()
                process.wait()
            self.log_queue.put(('log', f"   ❌ {script_name} timed out"))
            gc.collect()
            return False
            
        except Exception as e:
            import traceback
            print(f"[DEBUG] Exception in run_python_script: {str(e)}", flush=True)
            print(traceback.format_exc(), flush=True)
            self.log_queue.put(('log', f"   ❌ Error running {script_name}: {str(e)}"))
            if process:
                try:
                    process.kill()
                    process.wait(timeout=2)
                except:
                    pass
            gc.collect()
            return False
        
        finally:
            print(f"[DEBUG] Entering finally block", flush=True)
            # Always restore working directory
            os.chdir(original_cwd)
            print(f"[DEBUG] Restored cwd to {original_cwd}", flush=True)
            
            # Aggressive cleanup
            if process:
                try:
                    if process.stdout:
                        process.stdout.close()
                    if process.stderr:
                        process.stderr.close()
                except:
                    pass
            
            # Clean up thread references
            if stdout_thread:
                try:
                    stdout_thread.join(timeout=0.1)
                except:
                    pass
            if stderr_thread:
                try:
                    stderr_thread.join(timeout=0.1)
                except:
                    pass
            
            # Force garbage collection and clear pandas cache
            try:
                import pandas as pd
                # Clear pandas internal caches if available
                if hasattr(pd.io.common, '_get_filepath_or_buffer'):
                    func = pd.io.common._get_filepath_or_buffer
                    if hasattr(func, 'cache_clear'):
                        func.cache_clear()
            except:
                pass
            
            # Aggressive garbage collection
            gc.collect()
            gc.collect()  # Second pass to catch circular references
            print(f"[DEBUG] Exiting finally block", flush=True)
            
    def find_latest_file(self, pattern, search_dir=None):
        """Find the most recently created file matching the given pattern."""
        import glob
        if search_dir is None:
            search_dir = getattr(self, 'input_file_dir', os.getcwd())
        
        search_pattern = os.path.join(search_dir, pattern)
        matching_files = glob.glob(search_pattern)
        
        self.log_queue.put(('log', f"   🔍 Searching for: {pattern} in {search_dir}"))
        self.log_queue.put(('log', f"   🔍 Full search pattern: {search_pattern}"))
        self.log_queue.put(('log', f"   🔍 Found {len(matching_files)} matching files"))
        
        # Debug: List all CSV files in the directory
        all_csv_files = glob.glob(os.path.join(search_dir, "*.csv"))
        if all_csv_files:
            self.log_queue.put(('log', f"   📋 All CSV files in directory:"))
            for csv_file in sorted(all_csv_files):
                self.log_queue.put(('log', f"      - {os.path.basename(csv_file)}"))
        else:
            self.log_queue.put(('log', f"   📋 No CSV files found in directory"))
        
        if not matching_files:
            return None
        
        # Sort by creation time, newest first
        latest_file = max(matching_files, key=os.path.getctime)
        self.log_queue.put(('log', f"   📁 Found latest file: {os.path.basename(latest_file)}"))
        return latest_file
        
    def find_system_python(self):
        """Find the system Python executable when running from a packaged app."""
        # Try common Python locations
        python_candidates = [
            '/usr/local/bin/python3',
            '/usr/bin/python3',
            '/opt/homebrew/bin/python3',
            'python3',
            'python'
        ]
        
        for candidate in python_candidates:
            try:
                result = subprocess.run([candidate, '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.log_queue.put(('log', f"🐍 Found Python: {candidate} ({result.stdout.strip()})"))
                    return candidate
            except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        # Fallback to 'python3' and hope it's in PATH
        self.log_queue.put(('log', "⚠️  Could not find Python, using 'python3' as fallback"))
        return 'python3'

    def get_script_directory(self):
        """Get the directory containing the analysis scripts."""
        if hasattr(sys, '_MEIPASS'):
            # We're in a PyInstaller bundle - scripts are in the temp directory
            return sys._MEIPASS
        else:
            # Running from source - scripts are in the same directory
            return os.path.dirname(os.path.abspath(__file__))
            
    def get_limit_value(self):
        """Get the record limit value."""
        limit_str = self.limit_var.get()
        
        if limit_str == "No limit":
            return None
        elif limit_str == "Custom...":
            try:
                return int(self.custom_limit_entry.get())
            except (ValueError, tk.TclError):
                return None
        else:
            try:
                return int(limit_str)
            except ValueError:
                return None
            
    def cancel_analysis(self):
        if self.is_running:
            self.log_message("⏹ Cancel requested - stopping current process...")
            self.status_var.set("Cancelling...")
            # Set the flag so the analysis pipeline will terminate running processes
            self.cancel_requested = True
            
    def finish_analysis(self):
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        self.force_stop_button.config(state=tk.DISABLED)
        self.force_stop_button.pack_forget()  # Hide the force stop button
        self.progress_bar.stop()
        # Force garbage collection after analysis completes
        gc.collect()
        
    def log_message(self, message):
        self.log_queue.put(('log', message))
        
    def start_log_monitor(self):
        """Start the log monitor with proper lifecycle management."""
        if not self._log_monitor_active:
            self._log_monitor_active = True
        self.process_log_queue()
        # Adaptive polling: faster when processing, slower when idle
        # Only schedule next call if monitor is still active
        if self._log_monitor_active:
            if self.is_running:
                self.root.after(50, self.start_log_monitor)  # Faster during processing
            else:
                self.root.after(200, self.start_log_monitor)  # Slower when idle
        
    def process_log_queue(self):
        try:
            # Batch process multiple messages to reduce UI updates
            messages_processed = 0
            max_batch_size = 10  # Process up to 10 messages per cycle
            
            while messages_processed < max_batch_size:
                msg_type, message = self.log_queue.get_nowait()
                messages_processed += 1
                
                if msg_type == 'log':
                    # Batch log messages to reduce text widget updates
                    if not hasattr(self, '_log_buffer'):
                        self._log_buffer = []
                    self._log_buffer.append(message)
                    
                    # Flush buffer when it gets large or when processing stops
                    if len(self._log_buffer) >= 5 or not self.is_running:
                        try:
                            self.log_text.config(state=tk.NORMAL)
                            for log_msg in self._log_buffer:
                                self.log_text.insert(tk.END, f"{log_msg}\n")
                            
                            # Limit log size to prevent memory issues
                            try:
                                line_count = int(self.log_text.index('end-1c').split('.')[0])
                                if line_count > self._max_log_lines:
                                    # Remove oldest lines, keeping only the most recent
                                    lines_to_remove = line_count - self._max_log_lines
                                    self.log_text.delete(f"1.0", f"{lines_to_remove}.0")
                            except (ValueError, tk.TclError):
                                # If we can't determine line count, just clear if it's too large
                                pass
                            
                            self.log_text.see(tk.END)
                            self.log_text.config(state=tk.DISABLED)
                        except (tk.TclError, RuntimeError) as e:
                            # Handle widget destruction or other Tkinter errors gracefully
                            print(f"Error updating log widget: {e}")
                        finally:
                            self._log_buffer = []
                    
                elif msg_type == 'status':
                    # Throttle status updates to prevent excessive UI redraws
                    current_time = time.time() * 1000  # Convert to milliseconds
                    if current_time - self._last_ui_update > self._ui_update_throttle_ms:
                        self.status_var.set(message)
                        self._last_ui_update = current_time
                    else:
                        # Defer the update if too frequent
                        if not self._ui_update_pending:
                            self._ui_update_pending = True
                            self.root.after(self._ui_update_throttle_ms, self._flush_pending_ui_update)
                    
                elif msg_type == 'auto_import':
                    # Auto-import analysis results to history
                    self._perform_auto_import(message)
                    
                elif msg_type == 'finished':
                    self.finish_analysis()
                    # Clean up log buffer
                    if hasattr(self, '_log_buffer'):
                        del self._log_buffer
                    
                elif msg_type == 'file_selected':
                    # Store full path internally, display only filename
                    self.input_file_full_path = message
                    self.input_file_var.set(os.path.basename(message))
                    self.validate_file(message)
                    self.log_message(f"📁 File selected: {os.path.basename(message)}")
                    
                elif msg_type == 'file_cancelled':
                    self.log_message("📁 File selection cancelled")
                    
                elif msg_type == 'file_error':
                    self.log_message(f"⚠️  File dialog failed: {message}")
                    self.log_message("💡 Please try typing the file path directly in the text field")
                    
                elif msg_type == 'browse_done':
                    # Re-enable browse button
                    self.reset_browse_button()
                    
                elif msg_type == 'show_force_stop':
                    # Show the force stop button when process seems stuck
                    self.force_stop_button.pack(side=tk.LEFT, padx=(0, 10))
                    self.force_stop_button.config(state=tk.NORMAL)
                    
                elif msg_type == 'file_validation_result':
                    # Handle async file validation results
                    result = message
                    self.file_info_label.config(
                        text=result['message'],
                        foreground=result['color']
                    )
                    
                    if result['log_message']:
                        self.log_message(result['log_message'])
                    
                    if result['success']:
                        # Enable/disable Talk to Data button based on filename
                        self.update_talk_to_data_button(result['filename'])
                    else:
                        self.talk_to_data_button.config(state=tk.DISABLED)
                    
        except queue.Empty:
            pass
    
    def _flush_pending_ui_update(self):
        """Flush any pending UI updates."""
        self._ui_update_pending = False
        # Process any remaining messages in the queue
        self.process_log_queue()
            
    def clear_log(self):
        """Clear the log display."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def save_log(self):
        """Save log to file."""
        filename = filedialog.asksaveasfilename(
            title="Save Log File",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                log_content = self.log_text.get(1.0, tk.END)
                with open(filename, 'w') as f:
                    f.write(log_content)
                messagebox.showinfo("Success", f"Log saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save log: {str(e)}")
                
    def open_output_folder(self):
        """Open the output folder."""
        # Use the input file directory where outputs are created
        output_dir = getattr(self, 'input_file_dir', os.getcwd())
        self.log_message(f"📁 Opening output directory: {output_dir}")
        
        if sys.platform == "darwin":  # macOS
            subprocess.Popen(["open", output_dir])
        elif sys.platform.startswith("win"):  # Windows
            subprocess.Popen(["explorer", output_dir])
        else:  # Linux
            subprocess.Popen(["xdg-open", output_dir])
            
    def save_api_key(self):
        """Save the API key securely."""
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("No API Key", "Please enter an API key first.")
            return
        
        # Save to keychain on macOS
        if platform.system() == "Darwin":
            if self.settings_manager.save_api_key_to_keychain(api_key):
                self.api_status_label.config(text="🔑 API key saved securely to Keychain", foreground='green')
                messagebox.showinfo("Success", "API key saved securely to macOS Keychain!")
            else:
                # Fallback to settings file
                settings = {"api_key_fallback": api_key}
                if self.settings_manager.save_settings(settings):
                    self.api_status_label.config(text="🔑 API key saved to settings (Keychain unavailable)", foreground='orange')
                    messagebox.showinfo("Success", "API key saved to settings file (Keychain unavailable).")
                else:
                    messagebox.showerror("Error", "Failed to save API key.")
        else:
            # On non-macOS systems, save to settings file
            settings = {"api_key_fallback": api_key}
            if self.settings_manager.save_settings(settings):
                self.api_status_label.config(text="🔑 API key saved to secure settings", foreground='green')
                messagebox.showinfo("Success", "API key saved securely!")
            else:
                messagebox.showerror("Error", "Failed to save API key.")
    
    def save_settings(self):
        """Save current UI settings."""
        settings = {
            "ui_preferences": {
                "last_file": self.input_file_full_path,
                "limit": self.limit_var.get(),
                "analysis_options": {key: var.get() for key, var in self.analysis_options.items()},
                "window_geometry": self.root.geometry()
            }
        }
        
        self.settings_manager.save_settings(settings)
            
    def load_settings(self):
        """Load settings and apply them to the UI."""
        settings = self.settings_manager.load_settings()
        ui_prefs = settings.get("ui_preferences", {})
        
        # Load API key from keychain (macOS) or settings file
        api_key = None
        if platform.system() == "Darwin":
            api_key = self.settings_manager.load_api_key_from_keychain()
            if api_key:
                self.api_status_label.config(text="🔑 API key loaded from Keychain", foreground='green')
            else:
                # Try fallback from settings
                api_key = settings.get("api_key_fallback", "")
                if api_key:
                    self.api_status_label.config(text="🔑 API key loaded from settings", foreground='orange')
        else:
            api_key = settings.get("api_key_fallback", "")
            if api_key:
                self.api_status_label.config(text="🔑 API key loaded from secure settings", foreground='green')
        
        if api_key:
            self.api_key_var.set(api_key)
        else:
            self.api_status_label.config(text="🔑 No saved API key found", foreground='gray')
        
        # Load UI preferences
        last_file = ui_prefs.get('last_file', '')
        if last_file:
            self.input_file_full_path = last_file
            self.input_file_var.set(os.path.basename(last_file))
        self.limit_var.set(ui_prefs.get('limit', 'No limit'))
        
        # Load analysis options
        analysis_settings = ui_prefs.get('analysis_options', {})
        for key, var in self.analysis_options.items():
            var.set(analysis_settings.get(key, var.get()))
        
        # Load window geometry
        geometry = ui_prefs.get('window_geometry', '1000x800')
        try:
            self.root.geometry(geometry)
        except:
            pass  # Ignore invalid geometry

    def on_file_path_entered(self, event):
        """Handle manual file path entry."""
        entered_text = self.input_file_var.get().strip()
        if entered_text:
            # Try to resolve the entered text as a full path
            # If it's just a filename, try to find it in the input_file_dir
            if os.path.isabs(entered_text):
                # It's already a full path
                normalized_path = self.normalize_file_path(entered_text)
            else:
                # It's a relative path or just filename, construct full path
                normalized_path = os.path.join(self.input_file_dir, entered_text)
                normalized_path = self.normalize_file_path(normalized_path)
            
            # Store full path internally
            self.input_file_full_path = normalized_path
            
            # Update display to show only filename
            self.input_file_var.set(os.path.basename(normalized_path))
            
            # Validate the file
            if os.path.exists(normalized_path):
                self.validate_file(normalized_path)
            else:
                self.file_info_label.config(
                    text=f"❌ File not found: {os.path.basename(normalized_path)}",
                    foreground='red'
                )

    def reset_browse_button(self):
        """Reset the browse button to its normal state."""
        # Find and reset the browse button
        for widget in self.root.winfo_children():
            if hasattr(widget, 'winfo_children'):
                for child in widget.winfo_children():
                    if hasattr(child, 'winfo_children'):
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, ttk.Button) and ('Browse' in str(grandchild.cget('text')) or 'Opening' in str(grandchild.cget('text'))):
                                grandchild.config(state=tk.NORMAL, text="Browse")
                                return

    def force_stop_analysis(self):
        if self.is_running:
            self.log_message("🛑 Force Stop requested - stopping current process...")
            self.status_var.set("Cancelling...")
            # Set the flag so the analysis pipeline will terminate running processes
            self.cancel_requested = True
    
    def on_closing(self):
        """Handle application closing - save settings and cleanup."""
        try:
            # Stop log monitor to prevent recursive after() calls
            self._log_monitor_active = False
            
            # Save current settings
            self.save_settings()
            
            # If analysis is running, ask user if they want to cancel
            if self.is_running:
                if messagebox.askyesno("Analysis Running", 
                                     "Analysis is currently running. Do you want to cancel it and exit?"):
                    self.cancel_requested = True
                    # Give it a moment to cancel gracefully
                    self.root.after(1000, self.root.destroy)
                return
            
        except Exception as e:
            print(f"Error saving settings on exit: {e}")
        
        # Clean up before closing
        try:
            # Clear log buffer if it exists
            if hasattr(self, '_log_buffer'):
                del self._log_buffer
            # Force garbage collection
            gc.collect()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        # Close the application
        self.root.destroy()
            
    def manage_api_keys(self):
        """Show API key management dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Manage API Keys")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Position the dialog safely within view
        self._position_dialog_relative_to_parent(dialog, width=500, height=300)
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="API Key Management", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Current API key status
        status_frame = ttk.LabelFrame(main_frame, text="Current Status", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        current_key = self.api_key_var.get()
        if current_key:
            masked_key = current_key[:8] + "..." + current_key[-4:] if len(current_key) > 12 else "***"
            status_text = f"✅ API key loaded: {masked_key}"
        else:
            status_text = "❌ No API key loaded"
        
        ttk.Label(status_frame, text=status_text).pack(anchor=tk.W)
        
        # Check keychain status on macOS
        if platform.system() == "Darwin":
            keychain_key = self.settings_manager.load_api_key_from_keychain()
            if keychain_key:
                ttk.Label(status_frame, text="🔑 API key found in macOS Keychain", foreground='green').pack(anchor=tk.W)
            else:
                ttk.Label(status_frame, text="🔑 No API key in macOS Keychain", foreground='gray').pack(anchor=tk.W)
        
        # Actions
        actions_frame = ttk.LabelFrame(main_frame, text="Actions", padding="10")
        actions_frame.pack(fill=tk.X, pady=(0, 15))
        
        def save_current_key():
            self.save_api_key()
            dialog.destroy()
        
        def clear_saved_key():
            if platform.system() == "Darwin":
                if self.settings_manager.delete_api_key_from_keychain():
                    messagebox.showinfo("Success", "API key removed from Keychain")
                else:
                    messagebox.showwarning("Note", "No API key found in Keychain")
            
            # Also clear from settings file
            settings = self.settings_manager.load_settings()
            if "api_key_fallback" in settings:
                del settings["api_key_fallback"]
                self.settings_manager.save_settings(settings)
            
            self.api_status_label.config(text="🔑 No saved API key found", foreground='gray')
            dialog.destroy()
        
        ttk.Button(actions_frame, text="💾 Save Current API Key", command=save_current_key).pack(pady=5, fill=tk.X)
        ttk.Button(actions_frame, text="🗑️ Clear Saved API Key", command=clear_saved_key).pack(pady=5, fill=tk.X)
        
        # Info
        info_frame = ttk.LabelFrame(main_frame, text="Information", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        info_text = """🔐 Security Information:

• On macOS: API keys are stored in your Keychain for maximum security
• On other platforms: API keys are stored in encrypted settings files
• Your API key never leaves your computer
• Settings are stored in your user directory only

🔑 Get your OpenAI API key from:
https://platform.openai.com/api-keys"""
        
        info_label = ttk.Label(info_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(anchor=tk.W)
        
        # Close button
        ttk.Button(main_frame, text="Close", command=dialog.destroy).pack(pady=(10, 0))
    
    def manage_custom_prompts(self):
        """Show custom prompts management dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Custom Prompts Manager")
        dialog.geometry("700x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Position the dialog safely within view
        self._position_dialog_relative_to_parent(dialog, width=700, height=500)
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Custom Prompts Manager", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Load custom prompts
        custom_prompts = self.settings_manager.load_custom_prompts()
        
        if custom_prompts:
            # List existing prompts
            list_frame = ttk.LabelFrame(main_frame, text="Saved Prompts", padding="10")
            list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
            
            # Create scrollable list
            list_scroll = ttk.Scrollbar(list_frame)
            list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            
            prompt_listbox = tk.Listbox(list_frame, yscrollcommand=list_scroll.set)
            prompt_listbox.pack(fill=tk.BOTH, expand=True)
            list_scroll.config(command=prompt_listbox.yview)
            
            # Populate list
            for name, data in custom_prompts.items():
                created = data.get('created', 'Unknown')[:10]  # Just the date part
                prompt_listbox.insert(tk.END, f"{name} (created: {created})")
            
            # Buttons for managing prompts
            button_frame = ttk.Frame(list_frame)
            button_frame.pack(fill=tk.X, pady=(10, 0))
            
            def view_prompt():
                selection = prompt_listbox.curselection()
                if selection:
                    prompt_name = list(custom_prompts.keys())[selection[0]]
                    prompt_data = custom_prompts[prompt_name]
                    
                    # Show prompt details
                    details_text = f"Name: {prompt_name}\n\n"
                    details_text += f"Prompt:\n{prompt_data['prompt']}\n\n"
                    details_text += f"Columns: {', '.join(prompt_data.get('columns', []))}\n\n"
                    details_text += f"Created: {prompt_data.get('created', 'Unknown')}"
                    
                    messagebox.showinfo(f"Prompt: {prompt_name}", details_text)
            
            def delete_prompt():
                selection = prompt_listbox.curselection()
                if selection:
                    prompt_name = list(custom_prompts.keys())[selection[0]]
                    if messagebox.askyesno("Confirm Delete", f"Delete prompt '{prompt_name}'?"):
                        if self.settings_manager.delete_custom_prompt(prompt_name):
                            messagebox.showinfo("Success", f"Prompt '{prompt_name}' deleted")
                            dialog.destroy()
                            self.manage_custom_prompts()  # Refresh the dialog
                        else:
                            messagebox.showerror("Error", "Failed to delete prompt")
            
            ttk.Button(button_frame, text="View Details", command=view_prompt).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="Delete", command=delete_prompt).pack(side=tk.LEFT)
        else:
            # No prompts yet
            no_prompts_label = ttk.Label(main_frame, text="No custom prompts saved yet.\n\nCreate custom prompts through the Custom Analysis feature.", 
                                        justify=tk.CENTER, font=('Arial', 10))
            no_prompts_label.pack(expand=True)
        
        # Close button
        ttk.Button(main_frame, text="Close", command=dialog.destroy).pack(pady=(10, 0))
    
    def show_advanced_settings(self):
        """Show advanced settings dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Advanced Settings")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Position the dialog safely within view
        self._position_dialog_relative_to_parent(dialog, width=600, height=400)
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Advanced Settings", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Load current settings
        settings = self.settings_manager.load_settings()
        advanced = settings.get("advanced_settings", {})
        
        # Settings form
        form_frame = ttk.LabelFrame(main_frame, text="API Configuration", padding="15")
        form_frame.pack(fill=tk.X, pady=(0, 15))
        
        # API Timeout
        timeout_frame = ttk.Frame(form_frame)
        timeout_frame.pack(fill=tk.X, pady=5)
        ttk.Label(timeout_frame, text="API Timeout (seconds):").pack(side=tk.LEFT)
        timeout_var = tk.StringVar(value=str(advanced.get("api_timeout", 60)))
        ttk.Entry(timeout_frame, textvariable=timeout_var, width=10).pack(side=tk.RIGHT)
        
        # Max Retries
        retries_frame = ttk.Frame(form_frame)
        retries_frame.pack(fill=tk.X, pady=5)
        ttk.Label(retries_frame, text="Max API Retries:").pack(side=tk.LEFT)
        retries_var = tk.StringVar(value=str(advanced.get("max_retries", 3)))
        ttk.Entry(retries_frame, textvariable=retries_var, width=10).pack(side=tk.RIGHT)
        
        # Batch Size
        batch_frame = ttk.Frame(form_frame)
        batch_frame.pack(fill=tk.X, pady=5)
        ttk.Label(batch_frame, text="Processing Batch Size:").pack(side=tk.LEFT)
        batch_var = tk.StringVar(value=str(advanced.get("batch_size", 100)))
        ttk.Entry(batch_frame, textvariable=batch_var, width=10).pack(side=tk.RIGHT)
        
        # Save function
        def save_advanced_settings():
            try:
                new_settings = {
                    "advanced_settings": {
                        "api_timeout": int(timeout_var.get()),
                        "max_retries": int(retries_var.get()),
                        "batch_size": int(batch_var.get())
                    }
                }
                
                if self.settings_manager.save_settings(new_settings):
                    messagebox.showinfo("Success", "Advanced settings saved!")
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "Failed to save settings")
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers for all fields")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Save", command=save_advanced_settings).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT)
        
        # Info
        info_text = """⚙️ Advanced Settings Information:

• API Timeout: How long to wait for OpenAI API responses
• Max Retries: Number of times to retry failed API calls
• Batch Size: Number of records to process in each batch

⚠️ Changing these settings may affect performance and reliability.
Use default values unless you know what you're doing."""
        
        info_label = ttk.Label(main_frame, text=info_text, justify=tk.LEFT, font=('Arial', 9))
        info_label.pack(pady=(20, 0), anchor=tk.W)
    
    def show_settings_info(self):
        """Show information about settings storage."""
        info = self.settings_manager.get_settings_info()
        
        info_text = f"""Settings Storage Information

📁 Settings Directory:
{info['settings_directory']}

📄 Settings File:
{info['settings_file']}

🔐 Security:"""
        
        if info['keychain_service']:
            info_text += f"""
• API keys stored in macOS Keychain
• Service: {info['keychain_service']}
• Account: {os.getlogin()}"""
        else:
            info_text += """
• API keys stored in encrypted settings file
• Platform: """ + info['platform']
        
        info_text += f"""

💾 What's Stored:
• UI preferences (window size, analysis options)
• Custom prompt templates
• Advanced API settings
• File paths and processing limits

🔒 Privacy:
• All data stays on your computer
• No data is sent to external services
• Settings are user-specific and secure"""
        
        messagebox.showinfo("Settings Information", info_text)

    def show_about(self):
        """Show the about dialog."""
        about_text = """AI Support Analyzer
Version 1.4.0+

An AI-powered analysis tool for customer support data.

Copyright © 2025 Automattic Inc.

Questions? Reach out to @wiesenhauss in Slack :)"""
        
        messagebox.showinfo("About AI Support Analyzer", about_text)
    
    def show_help_usage(self):
        """Show how to use the application."""
        help_text = """How to Use AI Support Analyzer

🚀 QUICK START:
1. Get your OpenAI API key from: https://platform.openai.com/api-keys
2. Enter your API key in the secure field
3. Download your support data CSV from Looker (see CSV Format Guide)
4. Click "Browse" or paste the file path directly
5. Choose which analyses you want to run
6. Click "Start Analysis" and wait for completion

📋 ANALYSIS MODULES:
✅ Core CSAT & Sentiment Analysis - Main AI analysis of customer satisfaction
✅ Data Cleanup & Validation - Removes spam and invalid entries  
✅ CSAT Prediction Analysis - Predicts satisfaction scores
✅ Topic Categorization - Groups tickets by subject matter
✅ CSAT Trends Analysis - Identifies patterns over time
✅ Product Feedback Analysis - Extracts product-related insights
✅ Customer Goals Analysis - Understands customer objectives
🎯 Custom Analysis - User-defined analysis with custom prompts and columns
⚡ Generate Visualizations - Creates charts and graphs (optional)

🔄 FLEXIBLE PIPELINE:
• Select 'Core CSAT Analysis' for new/raw data
• Deselect it to load already-analyzed files
• Mix and match any combination of analyses
• Each module can run independently on appropriate data

💬 TALK TO DATA FEATURE:
After running Core CSAT Analysis, use the "💬 Talk to Data" button to:
• Ask questions about your data in natural language
• Get AI-powered insights and recommendations  
• Explore trends and patterns interactively
• Generate custom reports based on your specific questions

⏱️ PROCESSING TIME:
• Small files (< 1,000 tickets): 5-15 minutes
• Medium files (1,000-5,000 tickets): 30-90 minutes  
• Large files (5,000+ tickets): 2-6 hours

💡 TIPS:
• Use record limits for testing with large files
• Keep the app open - it will show live progress
• All output files are saved in the same folder as your input CSV
• You can cancel or force-stop if something goes wrong"""

        self.show_help_dialog("How to Use", help_text)
    
    def show_help_csv(self):
        """Show CSV format requirements."""
        help_text = """CSV Format Guide

📊 WHERE TO GET DATA:
Download support data from this Looker dashboard:
https://looker.a8c.com/dashboards/2557?Created%20Date=24%20hour&Status=&Spam%20Status=Not%20spam&Happiness%20Division=

Adjust the filters as needed for your analysis period and division.

📋 REQUIRED COLUMNS FOR NEW DATA:
If running Core CSAT Analysis on raw data, your CSV must contain:

✅ ticket_id - Unique ticket identifier
✅ chat_transcript - The conversation text between agent and customer
✅ happiness_score - Customer satisfaction rating (1-5 scale, or empty)
✅ created_at - When the ticket was created (date/time)
✅ status - Ticket status (open, solved, etc.)

📋 USING PRE-ANALYZED DATA:
If loading already-processed files, you can skip Core CSAT Analysis and run:
• Trend analyses on files with CSAT_RATING, OVERALL_SENTIMENT columns
• Specific analyses on files with PRODUCT_FEEDBACK, CUSTOMER_GOALS columns
• Custom analysis on any CSV with your chosen columns

📋 OPTIONAL BUT HELPFUL COLUMNS:
• agent_name - Name of the support agent
• customer_email - Customer's email address  
• channel - How customer contacted us (chat, email, etc.)
• priority - Ticket priority level
• tags - Any ticket tags
• product - Product or service related to the ticket

⚠️ IMPORTANT NOTES:
• Column names are case-sensitive and must match exactly
• Chat transcript is the most important - this is what the AI analyzes
• Empty happiness_score values are OK (AI will predict them)
• Larger files take longer but provide more comprehensive insights
• The app automatically filters out spam and invalid entries

❌ COMMON ISSUES:
• "Column not found" errors usually mean column names don't match
• Very old exports might have different column names
• Make sure to export as CSV, not Excel format"""

        self.show_help_dialog("CSV Format Guide", help_text)
    
    def show_help_analysis(self):
        """Show detailed analysis information."""
        help_text = """Analysis Details - What the AI Does

🤖 CORE CSAT & SENTIMENT ANALYSIS:
The AI reads each chat transcript and answers:
• "What was the customer's overall satisfaction level?"
• "What specific issues or concerns did the customer have?"
• "How well did the agent handle the situation?"
• "What was the emotional tone of the conversation?"

This creates detailed satisfaction scores and sentiment analysis for every ticket.

🧹 DATA CLEANUP & VALIDATION:
Automatically removes:
• Spam tickets and promotional messages
• Debug entries and system messages  
• Auto-closed tickets without real customer interaction
• Incomplete or corrupted data entries

📊 CSAT PREDICTION ANALYSIS:
For tickets without satisfaction scores, the AI:
• Analyzes conversation patterns and outcomes
• Compares with similar resolved tickets
• Predicts likely satisfaction rating (1-5 scale)
• Calculates confidence levels for predictions

🏷️ TOPIC CATEGORIZATION:
The AI groups tickets by subject matter:
• Billing and payment issues
• Technical problems and bugs
• Account and login difficulties  
• Product feature requests
• General questions and guidance

📈 TRENDS ANALYSIS:
Identifies patterns over time:
• CSAT score changes by day/week
• Common complaint categories
• Agent performance trends
• Seasonal patterns in support volume

💡 PRODUCT FEEDBACK ANALYSIS:
Extracts actionable insights:
• Feature requests and suggestions
• Bug reports and technical issues
• User experience complaints
• Competitor mentions and comparisons

🎯 CUSTOMER GOALS ANALYSIS:
Understands what customers were trying to achieve:
• Task completion success rates
• Common user journey obstacles
• Self-service opportunity identification
• Educational content gaps

📊 VISUALIZATIONS (Optional):
Creates charts showing:
• Satisfaction score distributions
• Topic category breakdowns
• Trends over time
• Agent performance comparisons

🔬 OUTPUT FILES:
Each analysis creates detailed reports with:
• Individual ticket analysis results
• Summary statistics and insights
• Trend reports in plain English
• Actionable recommendations for improvement

The AI uses advanced language models to understand context, emotion, and intent - providing insights that would take humans weeks to analyze manually."""

        self.show_help_dialog("Analysis Details", help_text)
    
    def show_help_dialog(self, title, content):
        """Show a scrollable help dialog."""
        help_window = tk.Toplevel(self.root)
        help_window.title(title)
        help_window.geometry("800x600")
        help_window.transient(self.root)
        help_window.grab_set()
        
        # Position the dialog safely within view
        self._position_dialog_relative_to_parent(help_window, width=800, height=600)
        
        # Create scrollable text widget
        text_frame = ttk.Frame(help_window, padding="20")
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=('Arial', 12),
            padx=20,
            pady=20
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Insert content
        text_widget.insert(tk.END, content)
        text_widget.config(state=tk.DISABLED)  # Make read-only
        
        # Close button
        button_frame = ttk.Frame(help_window)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Close", command=help_window.destroy).pack()

    def on_custom_analysis_toggle(self, *args):
        """Enable/disable the configure button when custom analysis is toggled."""
        if self.analysis_options['custom_analysis'].get():
            self.config_button.config(state=tk.NORMAL)
        else:
            self.config_button.config(state=tk.DISABLED)
    
    def configure_custom_analysis(self):
        """Show dialog to configure custom analysis prompt and columns."""
        if not self.input_file_full_path:
            messagebox.showwarning("No File Selected", "Please select a CSV file first to see available columns.")
            return
        
        # Try to read the CSV to get column names
        try:
            file_path = self.normalize_file_path(self.input_file_full_path)
            df = pd.read_csv(file_path, nrows=1)  # Just read header
            available_columns = list(df.columns)
        except Exception as e:
            messagebox.showerror("Error Reading File", f"Could not read CSV file to get columns:\n{str(e)}")
            return
        
        # Create configuration dialog
        config_window = tk.Toplevel(self.root)
        config_window.title("Configure Custom Analysis")
        config_window.geometry("600x720")
        config_window.transient(self.root)
        config_window.grab_set()
        
        # Position the dialog safely within view
        self._position_dialog_relative_to_parent(config_window, width=600, height=720)
        
        main_frame = ttk.Frame(config_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Prompt section
        prompt_frame = ttk.LabelFrame(main_frame, text="Analysis Prompt", padding="10")
        prompt_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(prompt_frame, text="Enter your custom analysis prompt:").pack(anchor=tk.W)
        ttk.Label(prompt_frame, text="(This tells the AI what kind of analysis to perform)", 
                 font=('Arial', 9), foreground='gray').pack(anchor=tk.W, pady=(0, 5))
        
        prompt_text = scrolledtext.ScrolledText(prompt_frame, height=6, wrap=tk.WORD, font=('Arial', 12))
        prompt_text.pack(fill=tk.X, pady=(0, 5))
        
        # Set current prompt if exists
        if self.custom_prompt:
            prompt_text.insert(tk.END, self.custom_prompt)
        
        # Template and example prompts
        examples_frame = ttk.Frame(prompt_frame)
        examples_frame.pack(fill=tk.X)
        
        # Load saved templates button
        def load_template():
            custom_prompts = self.settings_manager.load_custom_prompts()
            if not custom_prompts:
                messagebox.showinfo("No Templates", "No saved prompt templates found.")
                return
            
            # Create template selection dialog
            template_dialog = tk.Toplevel(config_window)
            template_dialog.title("Load Template")
            template_dialog.geometry("400x300")
            template_dialog.transient(config_window)
            template_dialog.grab_set()
            
            # Position the dialog safely within view relative to parent
            self._position_dialog_relative_to_parent(template_dialog, config_window, width=400, height=300)
            
            template_frame = ttk.Frame(template_dialog, padding="20")
            template_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(template_frame, text="Select a template to load:", font=('Arial', 10, 'bold')).pack(pady=(0, 10))
            
            # Template listbox
            template_listbox = tk.Listbox(template_frame)
            template_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            template_names = list(custom_prompts.keys())
            for name in template_names:
                template_listbox.insert(tk.END, name)
            
            def apply_template():
                selection = template_listbox.curselection()
                if selection:
                    template_name = template_names[selection[0]]
                    template_data = custom_prompts[template_name]
                    
                    # Load prompt
                    prompt_text.delete("1.0", tk.END)
                    prompt_text.insert(tk.END, template_data['prompt'])
                    
                    # Load columns
                    template_columns = template_data.get('columns', [])
                    for col, var in column_vars.items():
                        var.set(col in template_columns)
                    
                    messagebox.showinfo("Template Loaded", f"Template '{template_name}' loaded successfully!")
                    template_dialog.destroy()
            
            button_frame = ttk.Frame(template_frame)
            button_frame.pack()
            
            ttk.Button(button_frame, text="Load", command=apply_template).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="Cancel", command=template_dialog.destroy).pack(side=tk.LEFT)
        
        # Template management buttons
        template_buttons_frame = ttk.Frame(examples_frame)
        template_buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        def save_prompt_template():
            prompt = prompt_text.get("1.0", tk.END).strip()
            if not prompt:
                messagebox.showwarning("Empty Prompt", "Please enter a prompt before saving.")
                return
            
            import tkinter.simpledialog as simpledialog
            template_name = simpledialog.askstring("Template Name", "Enter a name for this template:")
            if template_name:
                # Get selected columns
                selected_columns = [col for col, var in column_vars.items() if var.get()]
                if self.settings_manager.save_custom_prompt(template_name, prompt, selected_columns):
                    messagebox.showinfo("Success", f"Template '{template_name}' saved!")
                else:
                    messagebox.showerror("Error", "Failed to save template")
        
        def clear_prompt():
            if messagebox.askyesno("Clear Prompt", "Are you sure you want to clear the current prompt?"):
                prompt_text.delete("1.0", tk.END)
        
        ttk.Button(template_buttons_frame, text="📁 Load Template", command=load_template).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(template_buttons_frame, text="💾 Save Prompt", command=save_prompt_template).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(template_buttons_frame, text="🗑️ Clear Prompt", command=clear_prompt).pack(side=tk.LEFT, padx=(0, 10))
        
        # Example prompts section
        examples_section_frame = ttk.Frame(examples_frame)
        examples_section_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(examples_section_frame, text="Example prompts:", font=('Arial', 9, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        example_buttons = [
            ("Agent Performance", "Analyze agent performance based on chat transcripts and satisfaction scores. Identify top performers and areas for improvement."),
            ("Customer Journey", "Analyze the customer journey from initial contact to resolution. Identify pain points and opportunities for process improvement."),
            ("Billing Issues", "Focus on billing-related tickets. Identify common billing problems and their impact on customer satisfaction.")
        ]
        
        example_buttons_frame = ttk.Frame(examples_section_frame)
        example_buttons_frame.pack(fill=tk.X)
        
        for label, prompt in example_buttons:
            btn = ttk.Button(example_buttons_frame, text=label, 
                           command=lambda p=prompt: (prompt_text.delete("1.0", tk.END), prompt_text.insert(tk.END, p)))
            btn.pack(side=tk.LEFT, padx=(0, 5), pady=2)
        
        # Columns section
        columns_frame = ttk.LabelFrame(main_frame, text="Select Columns for Analysis", padding="10")
        columns_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        ttk.Label(columns_frame, text="Choose which columns to include in the analysis:").pack(anchor=tk.W)
        
        # Scrollable frame for checkboxes
        canvas = tk.Canvas(columns_frame)
        scrollbar = ttk.Scrollbar(columns_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Column checkboxes
        column_vars = {}
        for col in available_columns:
            var = tk.BooleanVar()
            # Pre-select if already selected
            if col in self.custom_columns:
                var.set(True)
            
            cb = ttk.Checkbutton(scrollable_frame, text=col, variable=var)
            cb.pack(anchor=tk.W, pady=1)
            column_vars[col] = var
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        def save_configuration():
            # Get prompt
            prompt = prompt_text.get("1.0", tk.END).strip()
            if not prompt:
                messagebox.showwarning("No Prompt", "Please enter an analysis prompt.")
                return
            
            # Get selected columns
            selected_columns = [col for col, var in column_vars.items() if var.get()]
            if not selected_columns:
                messagebox.showwarning("No Columns", "Please select at least one column for analysis.")
                return
            
            # Save configuration
            self.custom_prompt = prompt
            self.custom_columns = selected_columns
            
            messagebox.showinfo("Configuration Saved", 
                              f"Custom analysis configured with:\n"
                              f"• Prompt: {prompt[:50]}...\n"
                              f"• Columns: {', '.join(selected_columns[:3])}"
                              f"{'...' if len(selected_columns) > 3 else ''}")
            config_window.destroy()
        
        ttk.Button(button_frame, text="Save Configuration", command=save_configuration).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=config_window.destroy).pack(side=tk.LEFT)

    def configure_analysis_prompt(self, analysis_key):
        """Configure custom prompt for a specific analysis type."""
        analysis_name = self.configurable_analyses[analysis_key]
        
        # Get the default prompt for this analysis
        default_prompts = self.get_default_prompts()
        default_prompt = default_prompts.get(analysis_key, "No default prompt available.")
        
        # Load any saved custom prompt
        settings = self.settings_manager.load_settings()
        saved_prompts = settings.get("analysis_prompts", {})
        current_prompt = saved_prompts.get(analysis_key, default_prompt)
        
        # Create configuration dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Configure {analysis_name}")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Position the dialog safely within view
        self._position_dialog_relative_to_parent(dialog, width=800, height=600)
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text=f"Configure {analysis_name} Prompt", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Current prompt section
        prompt_frame = ttk.LabelFrame(main_frame, text="Analysis Prompt", padding="10")
        prompt_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        ttk.Label(prompt_frame, text="Edit the prompt that will be used for this analysis:", 
                 font=('Arial', 10)).pack(anchor=tk.W, pady=(0, 5))
        
        # Prompt text area
        prompt_text = scrolledtext.ScrolledText(prompt_frame, height=15, wrap=tk.WORD, font=('Arial', 12))
        prompt_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        prompt_text.insert(tk.END, current_prompt)
        
        # Action buttons
        action_frame = ttk.Frame(prompt_frame)
        action_frame.pack(fill=tk.X)
        
        def reset_to_default():
            prompt_text.delete("1.0", tk.END)
            prompt_text.insert(tk.END, default_prompt)
        
        def save_prompt():
            new_prompt = prompt_text.get("1.0", tk.END).strip()
            if not new_prompt:
                messagebox.showwarning("Empty Prompt", "Please enter a prompt.")
                return
            
            # Save to settings
            settings = self.settings_manager.load_settings()
            if "analysis_prompts" not in settings:
                settings["analysis_prompts"] = {}
            
            settings["analysis_prompts"][analysis_key] = new_prompt
            
            if self.settings_manager.save_settings(settings):
                messagebox.showinfo("Success", f"Custom prompt saved for {analysis_name}!")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to save prompt.")
        
        def clear_custom_prompt():
            if messagebox.askyesno("Confirm Reset", 
                                 f"Reset {analysis_name} to use the default prompt?"):
                # Remove custom prompt from settings
                settings = self.settings_manager.load_settings()
                if "analysis_prompts" in settings and analysis_key in settings["analysis_prompts"]:
                    del settings["analysis_prompts"][analysis_key]
                    self.settings_manager.save_settings(settings)
                
                messagebox.showinfo("Reset Complete", f"{analysis_name} will now use the default prompt.")
                dialog.destroy()
        
        ttk.Button(action_frame, text="Reset to Default", command=reset_to_default).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="Clear Custom", command=clear_custom_prompt).pack(side=tk.LEFT, padx=(0, 10))
        
        # Main buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        ttk.Button(button_frame, text="Save Prompt", command=save_prompt).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT)
        
        # Info section
        info_frame = ttk.LabelFrame(main_frame, text="Information", padding="10")
        info_frame.pack(fill=tk.X, pady=(15, 0))
        
        info_text = f"""💡 About {analysis_name} Prompts:

• This prompt tells the AI how to analyze your data
• You can customize it to focus on specific aspects or change the analysis style
• The prompt will be saved and reused for future analyses
• Use "Reset to Default" to see the original prompt
• Use "Clear Custom" to remove your customization and use defaults"""
        
        info_label = ttk.Label(info_frame, text=info_text, justify=tk.LEFT, font=('Arial', 9))
        info_label.pack(anchor=tk.W)
    
    def get_default_prompts(self):
        """Get the default prompts for each configurable analysis."""
        return {
            'topic_aggregator': """As an AI customer support supervisor for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others), analyze these interaction topics and group them into logical categories. 

Please organize these topics into broad categories with similar themes, including quantitative data. For example:

**Domain Issues (235 occurrences, 32%)**
- DNS configuration issues (78 occurrences, 10.6%)
- Domain connection problems (65 occurrences, 8.8%)
- Domain mapping issues (45 occurrences, 6.1%)
- Domain registration (25 occurrences, 3.4%)
- Domain renewals (12 occurrences, 1.6%)
- Domain transfers (10 occurrences, 1.4%)

**Plugin/Theme Issues (180 occurrences, 24.5%)**
- Plugin compatibility problems (85 occurrences, 11.6%)
- Theme customization (55 occurrences, 7.5%)
- Theme installation errors (40 occurrences, 5.4%)

For each category:
1. Calculate the total occurrences and percentage of all topics in that category
2. List each topic with its individual occurrence count and percentage
3. Sort categories from highest to lowest occurrence count
4. Within each category, sort topics from highest to lowest occurrence count

Make the categorization clear and intuitive for support team analysis.

Here are the topics to categorize with their occurrence counts:

""",
            'csat_trends': """As an AI customer support supervisor for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others), you are assigned to review and analyze a comprehensive dataset of support interactions. The dataset contains the following fields:
• Created Date
• Zendesk Ticket URL
• CSAT Rating
• CSAT Reason
• CSAT Comment
• First reply time without AI (hours)
• Total time spent (mins)
• SENTIMENT_ANALYSIS
• ISSUE_RESOLVED (true/false)
• INTERACTION_TOPICS
• RELATED_TO_PRODUCT (true/false)
• RELATED_TO_SERVICE (true/false)

Your goal is to generate a detailed report that provides actionable insights for the support team. Your analysis should address the following key questions:
    1. Ticket Trends & Volume:
    • How does the ticket volume change over time based on the Created Date?
    • Are there noticeable patterns or peak periods in ticket creation?

    2. CSAT & Customer Feedback:
    • What is the overall average CSAT Rating and how does it trend over time?
    • What common themes emerge from the CSAT Reason and CSAT Comment fields?
    • How do customer sentiments (SENTIMENT_ANALYSIS) correlate with the CSAT ratings?

    3. Response & Resolution Metrics:
    • What are the average First reply times without AI (in hours) and the Total time spent (in minutes) per ticket?
    • Is there a relationship between longer resolution times and lower CSAT ratings or unresolved issues (ISSUE_RESOLVED)?

    4. Interaction Topics & Issue Categorization:
    • Which INTERACTION_TOPICS are most frequent among the support interactions?
    • How do tickets related to product issues (RELATED_TO_PRODUCT) compare to those related to service issues (RELATED_TO_SERVICE) in terms of CSAT, sentiment, and resolution success?

Based on your analysis, please structure your report as follows:

• Title / Report Header: Include the report title, current date, and a brief overview.
• Executive Summary: Summarize key findings and top recommendations.
• Data Overview: Describe the dataset, including the time period and the fields analyzed.
• Ticket Trends & Volume: Provide an analysis of ticket volumes and trends over time. Give multiple examples of tickets (from "Zendesk Ticket URL").
• CSAT & Customer Feedback Analysis: Present findings on CSAT ratings, common feedback themes, and sentiment correlations. Give multiple examples of tickets (from "Zendesk Ticket URL").
• Response & Resolution Metrics: Analyze the first reply time and total time spent, and correlate these with resolution success. Give multiple examples of tickets (from "Zendesk Ticket URL").
• Interaction Topics & Issue Categorization: Break down the frequency and impact of various interaction topics, including differences between product-related and service-related issues. Give examples of tickets (from "Zendesk Ticket URL").
• Actionable Recommendations: List specific, prioritized actions for process improvements, training, or system enhancements based on the insights.
• Conclusion: Summarize the main insights and suggest next steps for the support team.

Ensure that your final output is comprehensive, clearly formatted, and provides practical, immediately actionable insights for improving the support process.

Here are the records to analyze:

""",
            'product_feedback': """As a product insights analyst for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others), you are assigned to review and analyze a dataset of customer product feedback collected from support interactions. The dataset contains the following fields:
• Created Date
• Ticket ID (from Zendesk)
• PRODUCT_FEEDBACK (detailed customer comments about product features, issues, or suggestions)
• Additional fields that may be available:
  - CSAT Rating
  - INTERACTION_TOPICS
  - ISSUE_RESOLVED (true/false)

Your goal is to generate a detailed report that provides actionable product insights for the product and engineering teams. Your analysis should address the following key questions:

1. Product Feedback Trends:
   • What are the most common product issues, pain points, or feature requests mentioned by customers?
   • Are there emerging trends or patterns in the product feedback over time?
   • What specific product features or aspects receive the most feedback (positive or negative)?

2. Feature Requests & Enhancement Suggestions:
   • What new features are customers frequently requesting?
   • What existing features do customers want improved or enhanced?
   • Are there consistent patterns in how customers want the product to evolve?

3. Product Usability & Performance:
   • What usability issues are customers experiencing?
   • Are there performance problems reported consistently?
   • What aspects of the product interface or workflow are causing confusion or frustration?

4. Product Satisfaction Patterns:
   • If CSAT data is available, how does product feedback correlate with satisfaction ratings?
   • What product aspects drive higher or lower satisfaction?
   • Are there specific product issues that consistently lead to negative feedback?

5. Actionable Product Insights:
   • What are the top 3-5 product improvements that would address the most common customer pain points?
   • What quick wins could be implemented to enhance customer experience?
   • What longer-term product development priorities are suggested by the feedback?

Based on your analysis, please structure your report as follows:

• Title / Report Header: Include the report title, current date, and a brief overview.
• Executive Summary: Summarize key findings and top product recommendations.
• Data Overview: Describe the dataset, including the time period and the fields analyzed.
• Product Feedback Categories: Categorize and quantify the types of product feedback (e.g., UI/UX issues, performance problems, feature requests, etc.). Include counts of how many tickets fall into each category.
• Top Product Issues: Identify and analyze the most frequently mentioned product problems. Include specific examples from at least 3 tickets with their Ticket IDs and count how many tickets mention each issue.
• Feature Request Analysis: Summarize and prioritize customer feature requests and enhancement suggestions. Include specific examples from at least 3 tickets with their Ticket IDs and count how many tickets request each feature.
• Product Satisfaction Drivers: If CSAT data is available, analyze the relationship between product aspects and customer satisfaction. Include at least 3 ticket examples with their Ticket IDs.
• Temporal Trends: Identify how product feedback has evolved over the time period in the dataset. Include ticket examples with their Ticket IDs.
• Actionable Recommendations: Provide specific, prioritized product improvement recommendations based on the feedback analysis. For each recommendation, include the count of tickets that would be addressed by this improvement.
• Conclusion: Summarize the main insights and suggest next steps for the product team.

IMPORTANT: For each category, issue, or trend you identify, you MUST:
1. Count how many tickets mention this issue/feature/category
2. Include at least 3 specific ticket examples with their Ticket IDs
3. Quantify the prevalence of each finding (e.g., "27% of tickets mentioned this issue")

Ensure that your final output is comprehensive, clearly formatted, and provides practical, immediately actionable insights for improving the product. Where possible, include specific examples from the dataset to illustrate key points.

Here are the records to analyze:

""",
            'goals_trends': """As a customer experience analyst for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others), you are assigned to review and analyze a dataset of customer goals collected from support interactions. The dataset contains the following fields:
• Created Date
• Ticket ID (from Zendesk)
• CUSTOMER_GOAL (detailed descriptions of what customers were trying to accomplish)
• Additional fields that may be available:
  - CSAT Rating

Your goal is to generate a detailed report that provides actionable insights about customer intentions, needs, and journey patterns for the product, support, and UX teams. Your analysis should address the following key questions:

1. Customer Goal Patterns:
   • What are the most common goals customers are trying to accomplish?
   • How do customer goals cluster into broader categories or themes?
   • Are there patterns in the complexity or clarity of customer goals?

2. Customer Journey Insights:
   • What stages of the customer journey are represented in these goals?
   • Are customers primarily trying to accomplish basic tasks or advanced functions?
   • What obstacles or friction points appear in customer goal descriptions?

3. Goal Completion Challenges:
   • What common barriers prevent customers from achieving their goals independently?
   • Are there specific product areas or features where customers struggle to accomplish their goals?
   • What patterns exist in how customers describe their attempted solutions before contacting support?

4. Customer Needs Analysis:
   • What underlying customer needs can be inferred from the stated goals?
   • Are customers' goals primarily functional, emotional, or social in nature?
   • How do customer goals reflect their expectations of the product?

5. Actionable Insights:
   • What product improvements could help customers achieve their goals more easily?
   • What support resources or documentation could better assist customers?
   • What proactive measures could prevent customers from needing support for these goals?

Based on your analysis, please structure your report as follows:

• Title / Report Header: Include the report title, current date, and a brief overview.
• Executive Summary: Summarize key findings and top recommendations.
• Data Overview: Describe the dataset, including the time period and the fields analyzed.
• Customer Goal Categories: Categorize and quantify the types of customer goals (e.g., content creation, site management, technical troubleshooting, etc.). Include counts of how many tickets fall into each category.
• Top Customer Objectives: Identify and analyze the most frequently mentioned customer goals. Include specific examples from at least 3 tickets with their Ticket IDs and count how many tickets mention each goal.
• Goal Complexity Analysis: Assess the complexity of customer goals and identify patterns in how customers articulate what they're trying to accomplish. Include specific examples from at least 3 tickets with their Ticket IDs.
• Customer Journey Mapping: Map customer goals to different stages of the customer journey. Include at least 3 ticket examples with their Ticket IDs for each journey stage identified.
• Goal Achievement Barriers: Identify common obstacles preventing customers from achieving their goals independently. Include ticket examples with their Ticket IDs.
• Satisfaction Correlation: If CSAT data is available, analyze the relationship between goal types and customer satisfaction. Include at least 3 ticket examples with their Ticket IDs.
• Actionable Recommendations: Provide specific, prioritized recommendations based on the goal analysis. For each recommendation, include the count of tickets that would be addressed by this improvement.
• Conclusion: Summarize the main insights and suggest next steps for the product and support teams.

IMPORTANT: For each category, goal type, or trend you identify, you MUST:
1. Count how many tickets mention this goal/category/trend
2. Include at least 3 specific ticket examples with their Ticket IDs
3. Quantify the prevalence of each finding (e.g., "32% of tickets involved this type of goal")

Ensure that your final output is comprehensive, clearly formatted, and provides practical, immediately actionable insights for improving both the product and support experience. Where possible, include specific examples from the dataset to illustrate key points.

Here are the records to analyze:

"""
        }
    
    def get_custom_prompt_args(self, analysis_key):
        """Get custom prompt arguments for a specific analysis if configured."""
        settings = self.settings_manager.load_settings()
        saved_prompts = settings.get("analysis_prompts", {})
        
        if analysis_key in saved_prompts:
            custom_prompt = saved_prompts[analysis_key]
            # Escape quotes and handle multiline prompts
            escaped_prompt = custom_prompt.replace('"', '\\"').replace('\n', '\\n')
            return [f"-prompt={escaped_prompt}"]
        
        return []

    def update_talk_to_data_button(self, filename):
        """Enable/disable Talk to Data and Import to History buttons based on file validation."""
        if filename and filename.endswith('.csv'):
            self.talk_to_data_button.config(state=tk.NORMAL)
            self.import_history_button.config(state=tk.NORMAL)
            self.log_message("💬 Talk to Data feature available for this CSV file")
        else:
            self.talk_to_data_button.config(state=tk.DISABLED)
            self.import_history_button.config(state=tk.DISABLED)
            if filename:
                self.log_message("💬 Talk to Data requires a CSV file")
    
    def open_talk_to_data(self):
        """Open the Talk to Data analysis window."""
        # Validate API key
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Please enter your OpenAI API key first.")
            return
        
        # Validate file
        input_file = self.input_file_full_path
        if not input_file or not os.path.exists(input_file):
            messagebox.showerror("Error", "Please select a valid CSV file first.")
            return
        
        # Check if file is processed - show confirmation dialog similar to other analyses
        if "support-analysis-output-predictive-csat" not in os.path.basename(input_file):
            result = messagebox.askyesno(
                "Using Raw Data File?", 
                "This CSV file doesn't appear to be processed by Core CSAT Analysis.\n\n"
                "Talk to Data works best with processed files that contain sentiment analysis, "
                "CSAT ratings, and other enriched data columns.\n\n"
                "Do you want to continue with this file anyway?\n\n"
                "• Click 'Yes' to proceed with the current file\n"
                "• Click 'No' to run Core CSAT Analysis first"
            )
            if not result:
                return
        
        try:
            # Import and launch Talk to Data
            from talktodata import TalkToDataWindow
            
            self.log_message("💬 Opening Talk to Data analysis window...")
            talk_window = TalkToDataWindow(self.root, input_file, api_key)
            
        except ImportError as e:
            messagebox.showerror(
                "Module Error", 
                f"Could not import Talk to Data module:\n{str(e)}\n\n"
                "Please ensure talktodata.py is in the same directory."
            )
        except Exception as e:
            error_msg = str(e)
            
            # Provide more helpful error messages for common issues
            if "tiktoken" in error_msg.lower() or "encoding" in error_msg.lower():
                self.log_message(f"⚠️  Token counting initialization issue: {error_msg}")
                self.log_message("💡 Talk to Data will use fallback token estimation")
                
                # Try to continue with fallback
                try:
                    talk_window = TalkToDataWindow(self.root, input_file, api_key)
                    return
                except Exception as e2:
                    error_msg = f"Talk to Data failed to start even with fallback:\n{str(e2)}"
            
            messagebox.showerror("Error", f"Failed to open Talk to Data:\n{error_msg}")
            self.log_message(f"❌ Talk to Data error: {error_msg}")
    
    def _perform_auto_import(self, input_dir):
        """Automatically import analysis results to history after analysis completes."""
        if not DATA_STORE_AVAILABLE:
            self.log_message("⚠️  Auto-import skipped: Historical analytics module not available")
            return
        
        try:
            import glob
            
            # Find the most recent analysis output file
            output_patterns = [
                "*support-analysis-output*.csv",
                "*predictive-csat*.csv"
            ]
            
            analysis_files = []
            for pattern in output_patterns:
                analysis_files.extend(glob.glob(os.path.join(input_dir, pattern)))
            
            if not analysis_files:
                self.log_message("⚠️  Auto-import skipped: No analysis output files found")
                return
            
            # Get the most recent file
            analysis_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            file_to_import = analysis_files[0]
            
            self.log_message("")
            self.log_message("📊 Auto-importing results to historical database...")
            self.log_message(f"   File: {os.path.basename(file_to_import)}")
            
            # Get data store instance
            data_store = get_data_store()
            
            # Import CSV
            stats = data_store.import_csv(file_to_import)
            
            # Show results
            self.log_message("✅ Auto-import completed!")
            self.log_message(f"   ✨ New tickets imported: {stats['imported']:,}")
            self.log_message(f"   🔄 Duplicates skipped: {stats['duplicates']:,}")
            
            if stats['period_start'] and stats['period_end']:
                self.log_message(f"   📅 Date range: {stats['period_start']} to {stats['period_end']}")
            
            # Get overall database stats
            db_stats = data_store.get_database_stats()
            self.log_message(f"   💾 Total tickets in history: {db_stats['total_tickets']:,}")
            
        except Exception as e:
            self.log_message(f"⚠️  Auto-import failed: {str(e)}")
            # Don't raise - this is a non-critical feature
    
    def import_to_history(self):
        """Import the current analysis results to the historical database."""
        if not DATA_STORE_AVAILABLE:
            messagebox.showerror(
                "Feature Unavailable", 
                "Historical analytics module is not available.\n\n"
                "Please ensure data_store.py and models.py are in the application directory."
            )
            return
        
        # Find the most recent analysis output file
        input_file = self.input_file_full_path
        if not input_file:
            messagebox.showerror("Error", "No file loaded. Please load a CSV file first.")
            return
        
        # Look for analysis output files in the same directory
        input_dir = os.path.dirname(input_file)
        import glob
        
        # Find analysis output files
        output_patterns = [
            "*support-analysis-output*.csv",
            "*predictive-csat*.csv"
        ]
        
        analysis_files = []
        for pattern in output_patterns:
            analysis_files.extend(glob.glob(os.path.join(input_dir, pattern)))
        
        if not analysis_files:
            # No analysis files found, check if current file is an analysis file
            basename = os.path.basename(input_file).lower()
            if 'support-analysis' in basename or 'predictive-csat' in basename:
                analysis_files = [input_file]
            else:
                messagebox.showwarning(
                    "No Analysis Files Found",
                    "Could not find any analysis output files in the current directory.\n\n"
                    "Please run an analysis first, or load a file that contains analysis results "
                    "(filename should contain 'support-analysis-output' or 'predictive-csat')."
                )
                return
        
        # If multiple files, let user choose or use most recent
        if len(analysis_files) > 1:
            # Sort by modification time, newest first
            analysis_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            # Create selection dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("Select File to Import")
            dialog.geometry("600x400")
            dialog.transient(self.root)
            dialog.grab_set()
            
            ttk.Label(dialog, text="Multiple analysis files found. Select one to import:", 
                     font=('SF Pro Display', 12)).pack(pady=10, padx=10)
            
            # Listbox with files
            listbox_frame = ttk.Frame(dialog)
            listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            scrollbar = ttk.Scrollbar(listbox_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, font=('Courier', 11))
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=listbox.yview)
            
            for f in analysis_files:
                mtime = datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d %H:%M')
                listbox.insert(tk.END, f"{os.path.basename(f)} ({mtime})")
            
            listbox.selection_set(0)  # Select first (most recent)
            
            selected_file = [None]
            
            def on_select():
                selection = listbox.curselection()
                if selection:
                    selected_file[0] = analysis_files[selection[0]]
                dialog.destroy()
            
            def on_cancel():
                dialog.destroy()
            
            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=10)
            ttk.Button(button_frame, text="Import Selected", command=on_select).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
            
            dialog.wait_window()
            
            if selected_file[0] is None:
                return
            
            file_to_import = selected_file[0]
        else:
            file_to_import = analysis_files[0]
        
        # Confirm import
        result = messagebox.askyesno(
            "Import to History",
            f"Import analysis results to historical database?\n\n"
            f"File: {os.path.basename(file_to_import)}\n\n"
            "This will store the analysis results for historical trend analysis. "
            "Duplicate tickets will be automatically skipped."
        )
        
        if not result:
            return
        
        # Perform import
        try:
            self.log_message("📊 Importing analysis results to historical database...")
            self.log_message(f"   File: {os.path.basename(file_to_import)}")
            
            # Get data store instance
            data_store = get_data_store()
            
            # Import CSV
            stats = data_store.import_csv(file_to_import)
            
            # Show results
            self.log_message("✅ Import completed successfully!")
            self.log_message(f"   📁 Total rows in file: {stats['total_rows']:,}")
            self.log_message(f"   ✨ New tickets imported: {stats['imported']:,}")
            self.log_message(f"   🔄 Duplicates skipped: {stats['duplicates']:,}")
            
            if stats['period_start'] and stats['period_end']:
                self.log_message(f"   📅 Date range: {stats['period_start']} to {stats['period_end']}")
            
            # Get overall database stats
            db_stats = data_store.get_database_stats()
            self.log_message(f"   💾 Total tickets in history: {db_stats['total_tickets']:,}")
            self.log_message(f"   📊 Database size: {db_stats['db_size_mb']:.2f} MB")
            
            messagebox.showinfo(
                "Import Successful",
                f"Analysis results imported to historical database!\n\n"
                f"New tickets imported: {stats['imported']:,}\n"
                f"Duplicates skipped: {stats['duplicates']:,}\n"
                f"Total tickets in history: {db_stats['total_tickets']:,}"
            )
            
        except Exception as e:
            error_msg = str(e)
            self.log_message(f"❌ Import failed: {error_msg}")
            messagebox.showerror("Import Failed", f"Failed to import analysis results:\n\n{error_msg}")
    
    def open_history_dashboard(self):
        """Open the historical analytics dashboard."""
        try:
            from history_dashboard import open_history_dashboard, ANALYTICS_AVAILABLE
            
            if not ANALYTICS_AVAILABLE:
                messagebox.showinfo(
                    "No Historical Data",
                    "The historical analytics feature requires data to be imported first.\n\n"
                    "1. Run an analysis on a CSV file\n"
                    "2. Click 'Import to History' to save the results\n"
                    "3. Then open the History Dashboard to view trends"
                )
                return
            
            self.log_message("📈 Opening Historical Analytics Dashboard...")
            dashboard = open_history_dashboard(self.root)
            
            if dashboard:
                self.log_message("   Dashboard opened successfully")
            
        except ImportError as e:
            messagebox.showerror(
                "Module Error",
                f"Could not import history dashboard module:\n{str(e)}\n\n"
                "Please ensure history_dashboard.py is in the application directory."
            )
        except Exception as e:
            error_msg = str(e)
            self.log_message(f"❌ Dashboard error: {error_msg}")
            messagebox.showerror("Error", f"Failed to open History Dashboard:\n\n{error_msg}")
    
    def open_insights_dashboard(self):
        """Open the Product Insights dashboard."""
        try:
            from insights_dashboard import open_insights_dashboard, INSIGHTS_AVAILABLE
            
            if not INSIGHTS_AVAILABLE:
                messagebox.showinfo(
                    "Feature Not Available",
                    "The Product Insights feature requires additional modules.\n\n"
                    "Please ensure all insight modules are installed."
                )
                return
            
            self.log_message("💡 Opening Product Insights Dashboard...")
            
            dashboard = open_insights_dashboard(self.root)
            
            if dashboard:
                self.log_message("   Product Insights Dashboard opened successfully")
                self.log_message("   💡 Use this dashboard to:")
                self.log_message("      • View prioritized product insights")
                self.log_message("      • Track feature requests and pain points")
                self.log_message("      • Export insights to Jira or reports")
            
        except ImportError as e:
            messagebox.showerror(
                "Module Error",
                f"Could not import insights dashboard module:\n{str(e)}\n\n"
                "Please ensure insights_dashboard.py is in the application directory."
            )
        except Exception as e:
            error_msg = str(e)
            self.log_message(f"❌ Insights Dashboard error: {error_msg}")
            messagebox.showerror("Error", f"Failed to open Product Insights Dashboard:\n\n{error_msg}")
    
    def open_talk_to_history(self):
        """Open Talk to Data with historical database data."""
        # Validate API key
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Please enter your OpenAI API key first.")
            return
        
        try:
            from talktodata import open_talk_to_history
            
            self.log_message("🗣️ Opening Talk to History...")
            
            window = open_talk_to_history(self.root, api_key)
            
            if window:
                self.log_message("   Talk to History opened successfully")
                self.log_message("   💡 Ask questions about your historical support data:")
                self.log_message("      • 'What were the top issues last month?'")
                self.log_message("      • 'How has sentiment changed over time?'")
                self.log_message("      • 'Compare resolution rates this quarter vs last'")
            
        except ImportError as e:
            messagebox.showerror(
                "Module Error",
                f"Could not import talk to history module:\n{str(e)}\n\n"
                "Please ensure talktodata.py is in the application directory."
            )
        except Exception as e:
            error_msg = str(e)
            self.log_message(f"❌ Talk to History error: {error_msg}")
            messagebox.showerror("Error", f"Failed to open Talk to History:\n\n{error_msg}")

def main():
    """Main function to run the GUI application."""
    root = tk.Tk()
    app = AISupportAnalyzerGUI(root)
    
    # Set icon and other window properties
    try:
        # Try to set window icon if available
        root.iconname("AI Support Analyzer")
    except:
        pass
    
    # Center window on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (1000 // 2)
    y = (root.winfo_screenheight() // 2) - (800 // 2)
    root.geometry(f"+{x}+{y}")
    
    # Start the GUI
    root.mainloop()

if __name__ == "__main__":
    main() 