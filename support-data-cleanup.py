#!/usr/bin/env python3
"""
WordPress.com Support Data Cleanup Tool
by @wiesenhauss

This script cleans processed support data by removing rows containing specific patterns
that indicate incomplete analysis, system-generated entries, or spam content. It performs
post-analysis cleanup to ensure only valid, meaningful support interactions remain in the dataset.

Removes rows containing:
- "Analysis incomplete" - Failed AI analysis attempts
- "wpcom_received_generic_not_ai_eligible" - System-flagged non-AI eligible tickets
- "debug_messages" - Development/testing entries
- "closed_by_automerge" - Automatically closed tickets
- "cl_dotcom_likely_spam_promo" - Spam or promotional content
- "close_now" - Immediate closure flags

Features:
- HIGH PERFORMANCE: Uses vectorized pandas operations (~10-20x faster than row iteration)
- Comprehensive pattern matching across all string columns
- Detailed cleanup statistics and reporting
- Configurable output suffix (supports both -clean and -preclean modes)
- Handles file paths with spaces and special characters
- Safe data processing with error handling

Usage:
  python support-data-cleanup.py -file="path/to/input.csv"
  python support-data-cleanup.py -file="path/to/input.csv" --suffix="-preclean"
  python support-data-cleanup.py  # Interactive mode - prompts for file path

Arguments:
  -file, --file    Path to the CSV file to clean
  --suffix         Output file suffix (default: "-clean", use "-preclean" for pre-processing)

Output:
  Creates a cleaned CSV file with specified suffix in the same directory as input
  Example: input.csv -> input-clean.csv (or input-preclean.csv)
"""

import pandas as pd
import os
import argparse

# Import shared utilities
from utils import (
    normalize_file_path,
    filter_dataframe_by_patterns,
    cleanup_dataframe,
    DEFAULT_CLEANUP_PATTERNS,
)


def clean_csv_file(file_path: str = None, suffix: str = "-clean", 
                   patterns: list = None, verbose: bool = True) -> tuple:
    """
    Clean a CSV file by removing rows matching specified patterns.
    
    Uses vectorized pandas operations for high performance on large datasets.
    This is ~10-20x faster than the previous row-by-row iteration approach.
    
    Args:
        file_path: Path to the CSV file (prompts if not provided)
        suffix: Output file suffix (default: "-clean")
        patterns: Patterns to filter out (default: DEFAULT_CLEANUP_PATTERNS)
        verbose: If True, print progress and statistics
        
    Returns:
        Tuple of (output_file_path, statistics_dict)
    """
    # If file_path is not provided as an argument, ask for it
    if file_path is None:
        file_path = input("Please enter the path to your CSV file: ")
    
    # Normalize the file path to handle spaces and special characters
    file_path = normalize_file_path(file_path)
    
    # Check if file exists
    if not os.path.isfile(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return None, None
    
    # Use default patterns if not specified
    if patterns is None:
        patterns = DEFAULT_CLEANUP_PATTERNS
    
    try:
        # Read the CSV file
        if verbose:
            print(f"Reading file: {file_path}")
        
        # Use on_bad_lines for robustness (handles malformed rows)
        df = pd.read_csv(file_path, on_bad_lines='skip')
        
        # Store original row count
        original_count = len(df)
        if verbose:
            print(f"Original file has {original_count:,} rows.")
        
        # Get string columns to filter
        string_columns = df.select_dtypes(include=['object']).columns.tolist()
        
        if not string_columns:
            if verbose:
                print("Warning: No string columns found in the CSV file.")
            cleaned_df = df
            stats = {
                'original_count': original_count,
                'remaining_count': original_count,
                'total_removed': 0,
                'pattern_counts': {p: 0 for p in patterns}
            }
        else:
            # Use optimized vectorized cleanup from utils
            cleaned_df, stats = cleanup_dataframe(
                df, 
                patterns=patterns, 
                columns=string_columns,
                verbose=verbose
            )
        
        # Create output filename
        file_name, file_ext = os.path.splitext(file_path)
        output_file = f"{file_name}{suffix}{file_ext}"
        
        # Save the cleaned data
        cleaned_df.to_csv(output_file, index=False)
        
        if verbose:
            print(f"Cleaned file saved as: {output_file}")
        
        return output_file, stats
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None, None


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='CSV Data Cleanup Tool - High Performance Edition',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python support-data-cleanup.py -file="data.csv"
  python support-data-cleanup.py -file="data.csv" --suffix="-preclean"
  python support-data-cleanup.py  # Interactive mode
        """
    )
    parser.add_argument(
        '-file', '--file', 
        type=str, 
        help='Path to the CSV file to clean'
    )
    parser.add_argument(
        '--suffix',
        type=str,
        default='-clean',
        help='Output file suffix (default: "-clean", use "-preclean" for pre-processing)'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output messages'
    )
    return parser.parse_args()


if __name__ == "__main__":
    print("CSV Data Cleanup Tool - High Performance Edition")
    print("This script will remove rows containing specific patterns and save a clean version.")
    print("Using vectorized operations for ~10-20x faster processing.\n")
    
    # Parse command-line arguments
    args = parse_arguments()
    
    # Call the function with the file path from arguments (if provided)
    clean_csv_file(
        file_path=args.file,
        suffix=args.suffix,
        verbose=not args.quiet
    )
