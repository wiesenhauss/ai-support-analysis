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
- Comprehensive pattern matching across all string columns
- Detailed cleanup statistics and reporting
- Automatic output file naming with "-clean" suffix
- Handles file paths with spaces and special characters
- Safe data processing with error handling

Usage:
  python support-data-cleanup.py -file="path/to/input.csv"
  python support-data-cleanup.py  # Interactive mode - prompts for file path

Arguments:
  -file, --file    Path to the CSV file to clean

Output:
  Creates a cleaned CSV file with "-clean" suffix in the same directory as input
  Example: input.csv -> input-clean.csv
"""

import pandas as pd
import os
import argparse

def normalize_file_path(file_path):
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

def clean_csv_file(file_path=None):
    # If file_path is not provided as an argument, ask for it
    if file_path is None:
        file_path = input("Please enter the path to your CSV file: ")
    
    # Normalize the file path to handle spaces and special characters
    file_path = normalize_file_path(file_path)
    
    # Check if file exists
    if not os.path.isfile(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return
    
    try:
        # Read the CSV file
        print(f"Reading file: {file_path}")
        df = pd.read_csv(file_path)
        
        # Store original row count
        original_count = len(df)
        print(f"Original file has {original_count} rows.")
        
        # Initialize counters for each condition
        analysis_incomplete_count = 0
        not_ai_eligible_count = 0
        debug_messages_count = 0
        closed_by_automerge_count = 0  # New counter for closed_by_automerge
        likely_spam_promo_count = 0    # New counter for cl_dotcom_likely_spam_promo
        close_now_count = 0            # New counter for close_now
        
        # Check for string columns to filter
        string_columns = df.select_dtypes(include=['object']).columns
        
        if not len(string_columns):
            print("Warning: No string columns found in the CSV file.")
        else:
            # Function to safely check if a value contains a string
            def safe_contains(value, pattern):
                if pd.isna(value):
                    return False
                if not isinstance(value, str):
                    return False
                return pattern in value
            
            # Filter out rows containing "Analysis incomplete"
            mask_analysis = df.apply(
                lambda row: any(safe_contains(row[col], "Analysis incomplete") for col in string_columns),
                axis=1
            )
            analysis_incomplete_count = mask_analysis.sum()
            df = df[~mask_analysis]
            
            # Filter out rows containing "wpcom_received_generic_not_ai_eligible"
            mask_not_eligible = df.apply(
                lambda row: any(safe_contains(row[col], "wpcom_received_generic_not_ai_eligible") for col in string_columns),
                axis=1
            )
            not_ai_eligible_count = mask_not_eligible.sum()
            df = df[~mask_not_eligible]
            
            # Filter out rows containing "debug_messages"
            mask_debug = df.apply(
                lambda row: any(safe_contains(row[col], "debug_messages") for col in string_columns),
                axis=1
            )
            debug_messages_count = mask_debug.sum()
            df = df[~mask_debug]
            
            # Filter out rows containing "closed_by_automerge"
            mask_automerge = df.apply(
                lambda row: any(safe_contains(row[col], "closed_by_automerge") for col in string_columns),
                axis=1
            )
            closed_by_automerge_count = mask_automerge.sum()
            df = df[~mask_automerge]
            
            # Filter out rows containing "cl_dotcom_likely_spam_promo"
            mask_spam_promo = df.apply(
                lambda row: any(safe_contains(row[col], "cl_dotcom_likely_spam_promo") for col in string_columns),
                axis=1
            )
            likely_spam_promo_count = mask_spam_promo.sum()
            df = df[~mask_spam_promo]
            
            # Filter out rows containing "close_now"
            mask_close_now = df.apply(
                lambda row: any(safe_contains(row[col], "close_now") for col in string_columns),
                axis=1
            )
            close_now_count = mask_close_now.sum()
            df = df[~mask_close_now]
        
        # Calculate total removed rows
        remaining_count = len(df)
        total_removed = original_count - remaining_count
        
        # Create output filename
        file_name, file_ext = os.path.splitext(file_path)
        output_file = f"{file_name}-clean{file_ext}"
        
        # Save the cleaned data
        df.to_csv(output_file, index=False)
        
        # Report statistics
        print("\n--- Cleanup Report ---")
        print(f"Rows containing 'Analysis incomplete': {analysis_incomplete_count} removed")
        print(f"Rows containing 'wpcom_received_generic_not_ai_eligible': {not_ai_eligible_count} removed")
        print(f"Rows containing 'debug_messages': {debug_messages_count} removed")
        print(f"Rows containing 'closed_by_automerge': {closed_by_automerge_count} removed")  # New report line
        print(f"Rows containing 'cl_dotcom_likely_spam_promo': {likely_spam_promo_count} removed")  # New report line
        print(f"Rows containing 'close_now': {close_now_count} removed")  # New report line
        print(f"Total rows removed: {total_removed}")
        print(f"Remaining rows: {remaining_count}")
        print(f"Cleaned file saved as: {output_file}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def parse_arguments():
    parser = argparse.ArgumentParser(description='CSV Data Cleanup Tool')
    parser.add_argument('-file', '--file', type=str, help='Path to the CSV file to clean')
    return parser.parse_args()

if __name__ == "__main__":
    print("CSV Data Cleanup Tool")
    print("This script will remove rows containing specific patterns and save a clean version.")
    
    # Parse command-line arguments
    args = parse_arguments()
    
    # Call the function with the file path from arguments (if provided)
    clean_csv_file(args.file)
