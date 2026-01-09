#!/usr/bin/env python3
"""
WordPress.com Support Data Pre-Cleanup Tool
by @wiesenhauss

This script performs initial cleanup of raw support data before analysis by removing rows 
containing system-generated content, spam, and other non-meaningful entries. It prepares
the dataset for the main analysis pipeline by filtering out noise and irrelevant data.

NOTE: This is now a thin wrapper around support-data-cleanup.py with --suffix="-preclean".
Both scripts use the same high-performance vectorized filtering logic.

Removes rows containing:
- "Analysis incomplete" - Previously failed analysis attempts
- "wpcom_received_generic_not_ai_eligible" - System-flagged non-AI eligible tickets
- "debug_messages" - Development/testing entries
- "closed_by_automerge" - Automatically closed tickets
- "cl_dotcom_likely_spam_promo" - Spam or promotional content
- "close_now" - Immediate closure flags

Features:
- HIGH PERFORMANCE: Uses vectorized pandas operations (~10-20x faster than row iteration)
- Pre-processing cleanup before main analysis
- Comprehensive pattern matching across all string columns
- Detailed cleanup statistics and reporting
- Automatic output file naming with "-preclean" suffix
- Handles file paths with spaces and special characters
- Safe data processing with error handling

Usage:
  python support-data-precleanup.py -file="path/to/input.csv"
  python support-data-precleanup.py  # Interactive mode - prompts for file path

Arguments:
  -file, --file    Path to the CSV file to clean

Output:
  Creates a pre-cleaned CSV file with "-preclean" suffix in the same directory as input
  Example: input.csv -> input-preclean.csv
"""

import argparse

# Import the consolidated cleanup function
from utils import normalize_file_path

# Import the main cleanup function from the cleanup module
# This ensures we use the same optimized code
try:
    from importlib import import_module
    cleanup_module = import_module('support-data-cleanup')
    clean_csv_file = cleanup_module.clean_csv_file
except (ImportError, ModuleNotFoundError):
    # Fallback: import directly if module import fails
    import pandas as pd
    import os
    from utils import (
        cleanup_dataframe,
        DEFAULT_CLEANUP_PATTERNS,
    )
    
    def clean_csv_file(file_path=None, suffix="-preclean", patterns=None, verbose=True):
        """Fallback implementation if module import fails."""
        if file_path is None:
            file_path = input("Please enter the path to your CSV file: ")
        
        file_path = normalize_file_path(file_path)
        
        if not os.path.isfile(file_path):
            print(f"Error: File '{file_path}' does not exist.")
            return None, None
        
        if patterns is None:
            patterns = DEFAULT_CLEANUP_PATTERNS
        
        try:
            if verbose:
                print(f"Reading file: {file_path}")
            
            df = pd.read_csv(file_path, on_bad_lines='skip')
            original_count = len(df)
            
            if verbose:
                print(f"Original file has {original_count:,} rows.")
            
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
                cleaned_df, stats = cleanup_dataframe(
                    df, patterns=patterns, columns=string_columns, verbose=verbose
                )
            
            file_name, file_ext = os.path.splitext(file_path)
            output_file = f"{file_name}{suffix}{file_ext}"
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
        description='CSV Data Pre-Cleanup Tool - High Performance Edition'
    )
    parser.add_argument(
        '-file', '--file', 
        type=str, 
        help='Path to the CSV file to clean'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output messages'
    )
    return parser.parse_args()


if __name__ == "__main__":
    print("CSV Data Pre-Cleanup Tool - High Performance Edition")
    print("This script will remove rows containing specific patterns and save a pre-cleaned version.")
    print("Using vectorized operations for ~10-20x faster processing.\n")
    
    # Parse command-line arguments
    args = parse_arguments()
    
    # Call the cleanup function with -preclean suffix
    clean_csv_file(
        file_path=args.file,
        suffix="-preclean",
        verbose=not args.quiet
    )
