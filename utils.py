#!/usr/bin/env python3
"""
AI Support Analyzer - Shared Utilities Module
by @wiesenhauss

This module provides common utility functions used across all analysis scripts,
eliminating code duplication and ensuring consistent behavior.

Features:
- File path normalization for cross-platform compatibility
- Fuzzy column matching for flexible CSV handling
- Safe string pattern matching utilities
- OpenAI client singleton for connection reuse
- Vectorized data filtering for performance
- Common logging configuration

Usage:
    from utils import (
        normalize_file_path,
        find_column_by_substring,
        get_openai_client,
        filter_dataframe_by_patterns,
    )
"""
from __future__ import annotations  # Enables deferred evaluation of type hints (PEP 563)

import os
import re
import logging
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING
from functools import lru_cache

# Import pandas with fallback for type checking
if TYPE_CHECKING:
    import pandas as pd

# Runtime import of pandas
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None  # type: ignore

# Try to import openai, but don't fail if not available
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# =============================================================================
# FILE PATH UTILITIES
# =============================================================================

def normalize_file_path(file_path: Optional[str]) -> Optional[str]:
    """
    Normalize file path to handle spaces and special characters.
    
    Handles:
    - Quoted paths (single and double quotes)
    - Escaped characters (backslash-space, etc.)
    - User home directory expansion (~)
    - Path normalization for the current OS
    
    Args:
        file_path: The file path to normalize
        
    Returns:
        Normalized file path, or None if input is None/empty
        
    Examples:
        >>> normalize_file_path("~/Documents/my\\ file.csv")
        '/Users/username/Documents/my file.csv'
        >>> normalize_file_path('"path with spaces.csv"')
        'path with spaces.csv'
    """
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


# =============================================================================
# DATAFRAME COLUMN UTILITIES
# =============================================================================

def find_column_by_substring(df: pd.DataFrame, column_name: str) -> Optional[str]:
    """
    Find a column in the DataFrame by substring matching.
    
    Handles spaces and case variations for flexible column matching.
    Useful when column names might vary slightly between CSV exports.
    
    Args:
        df: The DataFrame to search
        column_name: The column name to search for
        
    Returns:
        The actual column name found, or None if not found
        
    Examples:
        >>> find_column_by_substring(df, 'CSAT Rating')
        'csat_rating'  # Found case-insensitive match
        >>> find_column_by_substring(df, 'Message Body')
        'Interaction Message Body'  # Found substring match
    """
    # First try exact match
    if column_name in df.columns:
        return column_name
    
    # Normalize the column name we're looking for
    normalized_search = column_name.strip().lower()
    
    # Try to find a column that contains the substring
    for col in df.columns:
        normalized_col = col.strip().lower()
        if normalized_search in normalized_col or normalized_col in normalized_search:
            return col
    
    # If no match found, return None
    return None


def get_column_mapping(df: pd.DataFrame, required_columns: List[str], 
                       optional_columns: Optional[List[str]] = None) -> Dict[str, Optional[str]]:
    """
    Build a mapping from expected column names to actual column names.
    
    Args:
        df: The DataFrame to search
        required_columns: List of required column names
        optional_columns: List of optional column names (default: None)
        
    Returns:
        Dictionary mapping expected names to actual column names (or None if not found)
        
    Raises:
        ValueError: If any required columns are not found
    """
    column_mapping = {}
    missing_required = []
    
    # Find required columns
    for col in required_columns:
        actual_col = find_column_by_substring(df, col)
        if actual_col:
            column_mapping[col] = actual_col
        else:
            missing_required.append(col)
    
    if missing_required:
        raise ValueError(f"Missing required columns: {missing_required}")
    
    # Find optional columns
    if optional_columns:
        for col in optional_columns:
            actual_col = find_column_by_substring(df, col)
            column_mapping[col] = actual_col  # Will be None if not found
    
    return column_mapping


# =============================================================================
# STRING PATTERN MATCHING UTILITIES
# =============================================================================

def safe_contains(value: Any, pattern: str) -> bool:
    """
    Safely check if a value contains a pattern string.
    
    Handles NaN values and non-string types gracefully.
    
    Args:
        value: The value to check (can be any type)
        pattern: The pattern string to search for
        
    Returns:
        True if pattern is found in value, False otherwise
    """
    if pd.isna(value):
        return False
    if not isinstance(value, str):
        return False
    return pattern in value


def filter_dataframe_by_patterns(
    df: pd.DataFrame, 
    patterns: List[str],
    columns: Optional[List[str]] = None,
    return_counts: bool = False
) -> Union[pd.DataFrame, tuple]:
    """
    Filter out rows containing any of the specified patterns using vectorized operations.
    
    This is a high-performance replacement for multiple sequential df.apply() calls.
    Uses pandas vectorized string operations for ~10-20x speedup on large datasets.
    
    Args:
        df: The DataFrame to filter
        patterns: List of pattern strings to filter out
        columns: Specific columns to check (default: all string columns)
        return_counts: If True, also return counts of rows removed per pattern
        
    Returns:
        If return_counts is False: Filtered DataFrame
        If return_counts is True: Tuple of (filtered DataFrame, dict of pattern counts)
        
    Examples:
        >>> filtered_df = filter_dataframe_by_patterns(df, ["spam", "test"])
        >>> filtered_df, counts = filter_dataframe_by_patterns(df, ["spam"], return_counts=True)
    """
    if df.empty:
        return (df, {}) if return_counts else df
    
    # Get string columns if not specified
    if columns is None:
        columns = df.select_dtypes(include=['object']).columns.tolist()
    
    if not columns:
        return (df, {p: 0 for p in patterns}) if return_counts else df
    
    # Build a combined regex pattern for efficiency
    # Escape special regex characters in patterns
    escaped_patterns = [re.escape(p) for p in patterns]
    combined_pattern = '|'.join(escaped_patterns)
    
    # Track counts per pattern if requested
    pattern_counts = {p: 0 for p in patterns} if return_counts else None
    
    # Create a combined mask for all patterns across all columns
    combined_mask = pd.Series(False, index=df.index)
    
    for col in columns:
        if col not in df.columns:
            continue
            
        # Convert column to string and check for patterns
        col_str = df[col].astype(str)
        col_mask = col_str.str.contains(combined_pattern, case=True, na=False, regex=True)
        combined_mask = combined_mask | col_mask
        
        # Count individual patterns if requested
        if return_counts:
            for pattern in patterns:
                pattern_mask = col_str.str.contains(re.escape(pattern), case=True, na=False, regex=True)
                # Only count rows not already counted
                new_matches = pattern_mask & ~combined_mask.shift(1, fill_value=False)
                pattern_counts[pattern] += new_matches.sum()
    
    # If we need accurate per-pattern counts, recalculate
    if return_counts:
        pattern_counts = {}
        for pattern in patterns:
            pattern_mask = pd.Series(False, index=df.index)
            for col in columns:
                if col not in df.columns:
                    continue
                col_str = df[col].astype(str)
                col_mask = col_str.str.contains(re.escape(pattern), case=True, na=False, regex=True)
                pattern_mask = pattern_mask | col_mask
            pattern_counts[pattern] = pattern_mask.sum()
    
    # Filter out matching rows
    filtered_df = df[~combined_mask].copy()
    
    return (filtered_df, pattern_counts) if return_counts else filtered_df


# =============================================================================
# RETRY UTILITIES
# =============================================================================

import time
import hashlib
import json
from functools import wraps


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Optional[callable] = None
):
    """
    Decorator that retries a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exceptions that trigger a retry
        on_retry: Optional callback called on each retry (receives attempt, exception, delay)
        
    Returns:
        Decorated function with retry logic
        
    Examples:
        >>> @retry_with_backoff(max_retries=3, base_delay=1.0)
        ... def flaky_function():
        ...     # might fail sometimes
        ...     pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        
                        if on_retry:
                            on_retry(attempt + 1, e, delay)
                        
                        time.sleep(delay)
                    else:
                        raise
            
            raise last_exception
        
        return wrapper
    return decorator


# =============================================================================
# CONTENT HASHING UTILITIES
# =============================================================================

def compute_content_hash(content: str) -> str:
    """
    Compute a SHA-256 hash of the content for caching purposes.
    
    Args:
        content: The string content to hash
        
    Returns:
        Hex string of the SHA-256 hash
    """
    if not content or pd.isna(content):
        return ""
    return hashlib.sha256(str(content).encode('utf-8')).hexdigest()


def compute_ticket_hash(row: Dict[str, Any], content_columns: List[str]) -> str:
    """
    Compute a hash for a ticket row based on its content columns.
    
    This is used to detect if a ticket's content has changed since last analysis.
    
    Args:
        row: Dictionary containing the ticket data
        content_columns: List of column names to include in the hash
        
    Returns:
        Hex string of the combined content hash
    """
    content_parts = []
    for col in content_columns:
        value = row.get(col, "")
        if pd.isna(value):
            value = ""
        content_parts.append(str(value))
    
    combined = "||".join(content_parts)
    return compute_content_hash(combined)


# =============================================================================
# CHECKPOINT UTILITIES
# =============================================================================

class AnalysisCheckpoint:
    """
    Manages checkpoints for resuming interrupted analysis.
    
    Saves progress to a JSON file that can be used to resume
    processing if the analysis is interrupted.
    """
    
    def __init__(self, output_file: str):
        """
        Initialize checkpoint manager.
        
        Args:
            output_file: Path to the output CSV file (checkpoint file will be derived from this)
        """
        self.output_file = output_file
        self.checkpoint_file = f"{output_file}.checkpoint.json"
        self.data = {
            'input_file': '',
            'output_file': output_file,
            'last_processed_index': -1,
            'total_rows': 0,
            'processed_count': 0,
            'skipped_count': 0,
            'error_count': 0,
            'started_at': None,
            'updated_at': None,
            'content_hashes': {},  # Maps row index to content hash for caching
            'completed': False
        }
    
    def exists(self) -> bool:
        """Check if a checkpoint file exists."""
        return os.path.exists(self.checkpoint_file)
    
    def load(self) -> bool:
        """
        Load checkpoint data from file.
        
        Returns:
            True if checkpoint was loaded successfully, False otherwise
        """
        if not self.exists():
            return False
        
        try:
            with open(self.checkpoint_file, 'r') as f:
                self.data = json.load(f)
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load checkpoint: {e}")
            return False
    
    def save(self):
        """Save checkpoint data to file."""
        from datetime import datetime
        self.data['updated_at'] = datetime.now().isoformat()
        
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save checkpoint: {e}")
    
    def update(self, 
               last_index: int = None,
               processed: int = None,
               skipped: int = None,
               errors: int = None,
               content_hash: tuple = None):
        """
        Update checkpoint with progress.
        
        Args:
            last_index: Last processed row index
            processed: Number of successfully processed tickets
            skipped: Number of skipped tickets
            errors: Number of errors
            content_hash: Tuple of (index, hash) to store for caching
        """
        if last_index is not None:
            self.data['last_processed_index'] = last_index
        if processed is not None:
            self.data['processed_count'] = processed
        if skipped is not None:
            self.data['skipped_count'] = skipped
        if errors is not None:
            self.data['error_count'] = errors
        if content_hash is not None:
            idx, hash_value = content_hash
            self.data['content_hashes'][str(idx)] = hash_value
    
    def start(self, input_file: str, total_rows: int):
        """
        Initialize a new checkpoint for starting analysis.
        
        Args:
            input_file: Path to input CSV file
            total_rows: Total number of rows to process
        """
        from datetime import datetime
        self.data['input_file'] = input_file
        self.data['total_rows'] = total_rows
        self.data['started_at'] = datetime.now().isoformat()
        self.data['completed'] = False
        self.save()
    
    def complete(self):
        """Mark the checkpoint as completed and optionally clean up."""
        self.data['completed'] = True
        self.save()
    
    def delete(self):
        """Delete the checkpoint file."""
        if self.exists():
            try:
                os.remove(self.checkpoint_file)
            except IOError:
                pass
    
    def get_resume_index(self) -> int:
        """
        Get the index to resume from.
        
        Returns:
            The next index to process (last_processed_index + 1), or 0 if no checkpoint
        """
        return self.data['last_processed_index'] + 1
    
    def should_skip_cached(self, index: int, content_hash: str) -> bool:
        """
        Check if a row should be skipped based on cached hash.
        
        Args:
            index: Row index
            content_hash: Current content hash of the row
            
        Returns:
            True if the content hasn't changed and can be skipped
        """
        cached_hash = self.data['content_hashes'].get(str(index))
        return cached_hash is not None and cached_hash == content_hash
    
    def get_stats(self) -> Dict[str, Any]:
        """Get checkpoint statistics."""
        return {
            'last_processed': self.data['last_processed_index'],
            'total_rows': self.data['total_rows'],
            'processed': self.data['processed_count'],
            'skipped': self.data['skipped_count'],
            'errors': self.data['error_count'],
            'started_at': self.data['started_at'],
            'updated_at': self.data['updated_at']
        }


# =============================================================================
# OPENAI CLIENT UTILITIES
# =============================================================================

class OpenAIClientManager:
    """
    Singleton manager for OpenAI client to enable connection reuse.
    
    Provides a single shared OpenAI client instance across all API calls,
    reducing connection overhead and enabling better resource management.
    
    Usage:
        client = get_openai_client()
        response = client.chat.completions.create(...)
    """
    
    _instance = None
    _client = None
    _api_key = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_client(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> 'openai.OpenAI':
        """
        Get or create the OpenAI client.
        
        Args:
            api_key: OpenAI API key (default: from environment)
            base_url: Custom base URL for local servers (default: None for OpenAI API)
            
        Returns:
            OpenAI client instance
            
        Raises:
            ValueError: If no API key is available and not using local server
            ImportError: If openai package is not installed
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package is not installed. Install with: pip install openai")
        
        # Determine the API key to use
        if api_key is None:
            api_key = os.getenv('OPENAI_API_KEY')
        
        # For local servers, API key might not be needed
        if base_url and not api_key:
            api_key = "not-needed"
        
        if not api_key and not base_url:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Create new client if API key changed or client doesn't exist
        if self._client is None or self._api_key != api_key:
            self._api_key = api_key
            if base_url:
                self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
            else:
                self._client = openai.OpenAI(api_key=api_key)
        
        return self._client
    
    def reset(self):
        """Reset the client (useful for testing or API key changes)."""
        self._client = None
        self._api_key = None


# Global instance for easy access
_client_manager = OpenAIClientManager()


def get_openai_client(api_key: Optional[str] = None, 
                      base_url: Optional[str] = None,
                      use_local: bool = False) -> 'openai.OpenAI':
    """
    Get the shared OpenAI client instance.
    
    This is the recommended way to get an OpenAI client, as it reuses
    connections and reduces overhead.
    
    Args:
        api_key: OpenAI API key (default: from environment)
        base_url: Custom base URL (default: None)
        use_local: If True, use local server at localhost:1234
        
    Returns:
        OpenAI client instance
        
    Examples:
        >>> client = get_openai_client()
        >>> response = client.chat.completions.create(model="gpt-4.1-mini", ...)
        
        >>> local_client = get_openai_client(use_local=True)
    """
    if use_local:
        base_url = "http://localhost:1234/v1"
    
    return _client_manager.get_client(api_key=api_key, base_url=base_url)


def reset_openai_client():
    """Reset the OpenAI client (useful when API key changes)."""
    _client_manager.reset()


# =============================================================================
# LOGGING UTILITIES
# =============================================================================

def setup_logging(
    level: int = logging.INFO,
    format_string: str = '%(asctime)s - %(levelname)s - %(message)s',
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging with consistent configuration.
    
    Args:
        level: Logging level (default: INFO)
        format_string: Log message format
        log_file: Optional file to write logs to
        
    Returns:
        Configured logger instance
    """
    handlers = [logging.StreamHandler()]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)


# =============================================================================
# CSV UTILITIES
# =============================================================================

def read_csv_with_validation(
    file_path: str,
    required_columns: Optional[List[str]] = None,
    optional_columns: Optional[List[str]] = None,
    chunksize: Optional[int] = None,
    **kwargs
) -> Union[pd.DataFrame, pd.io.parsers.TextFileReader]:
    """
    Read a CSV file with path normalization and optional column validation.
    
    Args:
        file_path: Path to the CSV file
        required_columns: List of required column names to validate
        optional_columns: List of optional column names to check
        chunksize: If specified, return an iterator for chunked reading
        **kwargs: Additional arguments passed to pd.read_csv
        
    Returns:
        DataFrame or TextFileReader iterator (if chunksize specified)
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If required columns are missing
    """
    # Normalize the file path
    file_path = normalize_file_path(file_path)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Read the CSV
    if chunksize:
        return pd.read_csv(file_path, chunksize=chunksize, **kwargs)
    
    df = pd.read_csv(file_path, **kwargs)
    
    # Validate columns if specified
    if required_columns:
        column_mapping = get_column_mapping(df, required_columns, optional_columns)
        df.attrs['column_mapping'] = column_mapping
    
    return df


def save_csv_with_backup(
    df: pd.DataFrame,
    file_path: str,
    create_backup: bool = False,
    **kwargs
) -> str:
    """
    Save a DataFrame to CSV with optional backup of existing file.
    
    Args:
        df: DataFrame to save
        file_path: Output file path
        create_backup: If True, backup existing file before overwriting
        **kwargs: Additional arguments passed to df.to_csv
        
    Returns:
        The path where the file was saved
    """
    file_path = normalize_file_path(file_path)
    
    # Create backup if requested and file exists
    if create_backup and os.path.exists(file_path):
        import shutil
        from datetime import datetime
        backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(file_path, backup_path)
    
    # Save the DataFrame
    df.to_csv(file_path, index=False, **kwargs)
    
    return file_path


def process_csv_in_chunks(
    file_path: str,
    process_func,
    chunksize: int = 10000,
    output_file: Optional[str] = None,
    verbose: bool = True,
    **kwargs
) -> Optional[pd.DataFrame]:
    """
    Process a large CSV file in chunks to reduce memory usage.
    
    This is useful for files too large to fit in memory. Each chunk
    is processed by the provided function and results are combined.
    
    Args:
        file_path: Path to the CSV file
        process_func: Function to process each chunk (takes DataFrame, returns DataFrame)
        chunksize: Number of rows per chunk (default: 10000)
        output_file: If provided, write results incrementally to this file
        verbose: If True, print progress information
        **kwargs: Additional arguments passed to pd.read_csv
        
    Returns:
        Combined DataFrame of all processed chunks (if output_file is None)
        None (if output_file is provided - results written to file)
        
    Examples:
        >>> def add_column(df):
        ...     df['new_col'] = df['existing_col'] * 2
        ...     return df
        >>> result = process_csv_in_chunks('large_file.csv', add_column)
    """
    file_path = normalize_file_path(file_path)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get total rows for progress tracking
    if verbose:
        # Quick row count (read only first column)
        total_rows = sum(1 for _ in open(file_path, 'r', encoding='utf-8')) - 1  # -1 for header
        print(f"Processing {total_rows:,} rows in chunks of {chunksize:,}...")
    
    chunks_processed = 0
    results = []
    first_chunk = True
    
    for chunk in pd.read_csv(file_path, chunksize=chunksize, **kwargs):
        # Process the chunk
        processed_chunk = process_func(chunk)
        
        if output_file:
            # Write incrementally to file
            mode = 'w' if first_chunk else 'a'
            header = first_chunk
            processed_chunk.to_csv(output_file, mode=mode, header=header, index=False)
            first_chunk = False
        else:
            results.append(processed_chunk)
        
        chunks_processed += 1
        if verbose:
            rows_processed = chunks_processed * chunksize
            print(f"  Processed chunk {chunks_processed} ({min(rows_processed, total_rows):,} rows)")
    
    if verbose:
        print(f"Completed processing all {chunks_processed} chunks.")
    
    if output_file:
        return None
    else:
        return pd.concat(results, ignore_index=True)


# =============================================================================
# CONTENT PREPARATION UTILITIES
# =============================================================================

def prepare_records_for_analysis(
    df: pd.DataFrame,
    columns: List[str],
    limit: Optional[int] = None,
    record_separator: str = "-" * 50
) -> str:
    """
    Prepare DataFrame records as a formatted string for AI analysis.
    
    Uses efficient string building for better performance with large datasets.
    
    Args:
        df: DataFrame containing the data
        columns: List of column names to include
        limit: Maximum number of records to include (default: all)
        record_separator: String to separate records
        
    Returns:
        Formatted string of records
    """
    from io import StringIO
    
    buffer = StringIO()
    data_to_process = df.head(limit) if limit else df
    
    for idx, (_, row) in enumerate(data_to_process.iterrows(), 1):
        buffer.write(f"Record {idx}:\n")
        for col in columns:
            if col in row.index:
                value = row[col]
                if pd.isna(value):
                    value = "N/A"
                buffer.write(f"{col}: {value}\n")
        buffer.write(f"{record_separator}\n")
    
    return buffer.getvalue()


# =============================================================================
# TICKET URL UTILITIES
# =============================================================================

def extract_ticket_id(url: str) -> str:
    """
    Extract the ticket ID from a Zendesk ticket URL.
    
    URL format: https://a8c.zendesk.com/agent/tickets/{ticket_ID}
    
    Args:
        url: The Zendesk ticket URL
        
    Returns:
        The ticket ID, or "N/A" if extraction fails
    """
    try:
        if pd.isna(url) or not isinstance(url, str):
            return "N/A"
        
        if "/agent/tickets/" in url:
            ticket_id = url.split("/agent/tickets/")[-1].split("/")[0].split("?")[0]
            return ticket_id
        return "N/A"
    except Exception:
        return "N/A"


# =============================================================================
# DATA CLEANUP UTILITIES
# =============================================================================

# Default patterns to filter out during cleanup
DEFAULT_CLEANUP_PATTERNS = [
    "Analysis incomplete",
    "wpcom_received_generic_not_ai_eligible",
    "debug_messages",
    "closed_by_automerge",
    "cl_dotcom_likely_spam_promo",
    "close_now"
]


def cleanup_dataframe(
    df: pd.DataFrame,
    patterns: Optional[List[str]] = None,
    columns: Optional[List[str]] = None,
    verbose: bool = True
) -> tuple:
    """
    Clean a DataFrame by removing rows matching specified patterns.
    
    Uses vectorized operations for high performance on large datasets.
    
    Args:
        df: DataFrame to clean
        patterns: Patterns to filter out (default: DEFAULT_CLEANUP_PATTERNS)
        columns: Columns to check (default: all string columns)
        verbose: If True, print cleanup statistics
        
    Returns:
        Tuple of (cleaned DataFrame, statistics dict)
    """
    if patterns is None:
        patterns = DEFAULT_CLEANUP_PATTERNS
    
    original_count = len(df)
    
    # Use vectorized filtering
    cleaned_df, pattern_counts = filter_dataframe_by_patterns(
        df, patterns, columns, return_counts=True
    )
    
    remaining_count = len(cleaned_df)
    total_removed = original_count - remaining_count
    
    stats = {
        'original_count': original_count,
        'remaining_count': remaining_count,
        'total_removed': total_removed,
        'pattern_counts': pattern_counts
    }
    
    if verbose:
        import sys
        print("\n--- Cleanup Report ---")
        for pattern, count in pattern_counts.items():
            print(f"Rows containing '{pattern}': {count} removed")
        print(f"Total rows removed: {total_removed}")
        print(f"Remaining rows: {remaining_count}")
        sys.stdout.flush()  # Ensure output is captured by subprocess
    
    return cleaned_df, stats
