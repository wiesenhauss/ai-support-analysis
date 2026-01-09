#!/usr/bin/env python3
"""
WordPress.com Sentiment Analysis Visualization Tool
by @wiesenhauss

This script creates visual representations of sentiment analysis data from processed support
interactions. It generates time series plots and distribution charts to help visualize
sentiment trends and overall customer satisfaction patterns from support analysis results.

Features:
- Time series visualization of sentiment trends over time
- Overall sentiment distribution pie charts with percentages
- Flexible date parsing with error handling for various date formats
- Dual-plot layout showing both temporal and aggregate views
- Handles file paths with spaces and special characters
- Interactive and command-line input modes
- Data validation and error handling for missing columns

Visualization Output:
- Time Series Plot: Shows daily sentiment counts (Positive+Neutral vs Negative)
- Pie Chart: Overall sentiment distribution with counts and percentages
- Grid lines and markers for clear data reading
- Color-coded sentiment categories (Blue: Positive+Neutral, Red: Negative)

Usage:
  python visualize-overall-sentiment.py -file="path/to/analysis_output.csv"
  python visualize-overall-sentiment.py  # Interactive mode - prompts for file path

Arguments:
  -file    Path to CSV file containing analysis results with sentiment data

Required CSV Columns:
  - Created Date (for time series analysis)
  - SENTIMENT_ANALYSIS (containing Positive/Neutral/Negative values)

Output:
  Displays interactive matplotlib charts showing sentiment analysis visualizations
"""

import pandas as pd
import matplotlib.pyplot as plt
import argparse
import sys
import os
from typing import Optional

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

def find_column_by_substring(df: pd.DataFrame, column_name: str) -> Optional[str]:
    """Find a column in the DataFrame by substring matching, handling spaces and case variations."""
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

def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Visualize sentiment analysis from CSV file')
    parser.add_argument('-file', type=str, help='Path to the CSV file')
    args = parser.parse_args()
    
    # If no file is provided via command line, prompt the user
    if args.file:
        file_path = normalize_file_path(args.file)
    else:
        file_path = normalize_file_path(input("Enter the path to your CSV file: "))
    
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading the file: {e}")
        sys.exit(1)
    
    # Find required columns using fuzzy matching
    created_date_col = find_column_by_substring(df, 'Created Date')
    sentiment_col = find_column_by_substring(df, 'SENTIMENT_ANALYSIS')
    
    if not created_date_col:
        print("Error: 'Created Date' column not found in the CSV file.")
        sys.exit(1)
    
    if not sentiment_col:
        print("Error: 'SENTIMENT_ANALYSIS' column not found in the CSV file.")
        sys.exit(1)
    
    # Convert date column to datetime with more flexible parsing
    try:
        # Try to parse dates with automatic format detection
        df[created_date_col] = pd.to_datetime(df[created_date_col], errors='coerce')
        
        # Check if any dates failed to parse
        if df[created_date_col].isna().any():
            print("Warning: Some dates could not be parsed. They will be excluded from the analysis.")
            df = df.dropna(subset=[created_date_col])
            
        if len(df) == 0:
            print("Error: No valid dates found after parsing.")
            sys.exit(1)
    except Exception as e:
        print(f"Error processing dates: {e}")
        sys.exit(1)
    
    # Create a dictionary to store counts for each sentiment per date
    daily_counts = {}
    
    # Initialize the counts dictionary
    for date in df[created_date_col].unique():
        daily_counts[date] = {
            'Positive_Neutral': 0,
            'Negative': 0
        }
    
    # Count occurrences and track overall counts
    overall_counts = {'Positive_Neutral': 0, 'Negative': 0}
    
    for _, row in df.iterrows():
        date = row[created_date_col]
        sentiment = str(row[sentiment_col]).strip()
        
        if sentiment.lower() in ['positive', 'neutral']:
            daily_counts[date]['Positive_Neutral'] += 1
            overall_counts['Positive_Neutral'] += 1
        elif sentiment.lower() == 'negative':
            daily_counts[date]['Negative'] += 1
            overall_counts['Negative'] += 1
    
    # Convert counts to DataFrame for plotting
    plot_df = pd.DataFrame.from_dict(daily_counts, orient='index')
    
    # Sort by date
    plot_df = plot_df.sort_index()
    
    # Create a figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 6))
    
    # First subplot - Time series
    ax1.plot(plot_df.index, plot_df['Positive_Neutral'], marker='o', color='blue', label='Positive + Neutral')
    ax1.plot(plot_df.index, plot_df['Negative'], marker='o', color='red', label='Negative')
    
    ax1.set_title('Sentiment Analysis Over Time')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Number of Tickets')
    ax1.legend()
    ax1.grid(True)
    plt.setp(ax1.get_xticklabels(), rotation=45)
    
    # Second subplot - Overall sentiment pie chart
    labels = ['Positive + Neutral', 'Negative']
    sizes = [overall_counts['Positive_Neutral'], overall_counts['Negative']]
    colors = ['blue', 'red']
    
    # Calculate percentages for labels
    total = sum(sizes)
    percentages = [f"{label}\n{count} ({count/total*100:.1f}%)" for label, count in zip(labels, sizes)]
    
    ax2.pie(sizes, labels=percentages, colors=colors, autopct='', startangle=90)
    ax2.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    ax2.set_title('Overall Sentiment Distribution')
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()