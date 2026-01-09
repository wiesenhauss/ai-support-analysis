#!/usr/bin/env python3
"""
WordPress.com CSAT Prediction and Accuracy Analysis
by @wiesenhauss

This script analyzes support interaction data to predict CSAT ratings based on initial 
sentiment tags and final sentiment analysis results. It compares predicted ratings with 
actual CSAT scores to calculate prediction accuracy and identify sentiment changes during 
support interactions.

Features:
- CSAT prediction based on initial vs final sentiment analysis
- Accuracy calculation comparing predictions with actual CSAT ratings
- Sentiment change tracking (positive/negative shifts during interaction)
- Detailed accuracy reporting with statistics
- Handles file paths with spaces and special characters
- Automatic timestamped output file generation

Prediction Logic:
- Initial Neutral/Positive + Final Neutral -> Neutral
- Initial Neutral/Positive + Final Positive -> Positive  
- Initial Neutral/Positive + Final Negative -> Negative (changed)
- Initial Negative + Final Negative -> Negative
- Initial Negative + Final Neutral -> Negative
- Initial Negative + Final Positive -> Positive (changed)

Usage:
  python predict_csat.py -file="path/to/analysis_output.csv"
  python predict_csat.py  # Interactive mode - prompts for file path

Arguments:
  -file    Path to the CSV file containing analysis results with sentiment data

Required CSV Columns:
  - Tags (containing initial sentiment tags)
  - SENTIMENT_ANALYSIS (final sentiment from analysis)
  - CSAT Rating (for accuracy calculation)

Output:
  Creates a timestamped CSV file with prediction results:
  support-analysis-output-predictive-csat-YYYY-MM-DD-HHMMSS.csv
"""

import pandas as pd
from datetime import datetime
import sys
import os
import argparse

# Import shared utilities
from utils import normalize_file_path, find_column_by_substring

def get_initial_sentiment(tags):
    tags = str(tags)
    if 'cl_dotcom_initial_sentiment_neutral' in tags:
        return 'Neutral'
    elif 'cl_dotcom_initial_sentiment_positive' in tags:
        return 'Positive'
    elif 'cl_dotcom_initial_sentiment_negative' in tags:
        return 'Negative'
    return ''

def process_sentiment(row, tags_col='Tags', sentiment_col='SENTIMENT_ANALYSIS', csat_col='CSAT Rating'):
    # Extract tags and sentiment
    tags = str(row[tags_col])
    sentiment = str(row[sentiment_col])
    
    # Check for neutral/positive initial tags
    is_initial_neutral_positive = ('cl_dotcom_initial_sentiment_neutral' in tags or 
                                 'cl_dotcom_initial_sentiment_positive' in tags)
    is_initial_negative = 'cl_dotcom_initial_sentiment_negative' in tags
    
    # Process according to rules
    if is_initial_neutral_positive:
        if 'Neutral' in sentiment:
            return 'Neutral'
        elif 'Positive' in sentiment:
            return 'Positive'
        elif 'Negative' in sentiment:
            return 'Negative (changed)'
    elif is_initial_negative:
        if 'Negative' in sentiment:
            return 'Negative'
        elif 'Neutral' in sentiment:
            return 'Negative'
        elif 'Positive' in sentiment:
            return 'Positive (changed)'
    
    return ''  # Default empty value if no conditions match

def compare_prediction_with_csat(row, csat_col='CSAT Rating'):
    predicted = str(row['PREDICTED_CSAT'])
    
    # Return empty string if PREDICTED_CSAT is empty
    if predicted in ['', 'nan']:
        return ''
        
    actual = str(row[csat_col]).lower()
    
    # Ignore 'offered' or empty CSAT ratings
    if actual in ['offered', 'nan', '']:
        return ''
        
    # Compare predictions with actual ratings
    if actual == 'good':
        # Check if prediction contains either 'Positive' or 'Neutral'
        return str(('Positive' in predicted) or ('Neutral' in predicted)).upper()
    elif actual == 'bad':
        return str('Negative' in predicted).upper()
    
    return ''

def calculate_accuracy(df):
    # Filter to only TRUE or FALSE values
    accuracy_data = df[df['PREDICTED_CSAT_ACCURATE'].isin(['TRUE', 'FALSE'])]
    
    if len(accuracy_data) == 0:
        return "No data available for accuracy calculation"
    
    # Count TRUE values and total values
    true_count = len(accuracy_data[accuracy_data['PREDICTED_CSAT_ACCURATE'] == 'TRUE'])
    total_count = len(accuracy_data)
    
    # Calculate accuracy percentage
    accuracy_percentage = (true_count / total_count) * 100
    
    return f"CSAT Prediction Accuracy: {accuracy_percentage:.2f}% ({true_count}/{total_count})"

def process_file(input_file):
    try:
        # Read the CSV file
        df = pd.read_csv(input_file)
        
        # Find required columns using fuzzy matching
        tags_col = find_column_by_substring(df, 'Tags')
        sentiment_col = find_column_by_substring(df, 'SENTIMENT_ANALYSIS')
        csat_col = find_column_by_substring(df, 'CSAT Rating')
        
        if not tags_col:
            raise Exception("Could not find 'Tags' column")
        if not sentiment_col:
            raise Exception("Could not find 'SENTIMENT_ANALYSIS' column")
        if not csat_col:
            raise Exception("Could not find 'CSAT Rating' column")
        
        # Add INITIAL_SENTIMENT column based on tags
        df['INITIAL_SENTIMENT'] = df[tags_col].apply(get_initial_sentiment)
        
        # Add PREDICTED_CSAT column based on rules
        df['PREDICTED_CSAT'] = df.apply(lambda row: process_sentiment(row, tags_col, sentiment_col, csat_col), axis=1)
        
        # Add PREDICTED_CSAT_ACCURATE column
        df['PREDICTED_CSAT_ACCURATE'] = df.apply(lambda row: compare_prediction_with_csat(row, csat_col), axis=1)
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        
        # Get the directory of the input file
        input_dir = os.path.dirname(os.path.abspath(input_file))
        base_filename = f'support-analysis-output-predictive-csat-{timestamp}.csv'
        
        # Create the output path in the same directory as the input file
        output_file = os.path.join(input_dir, base_filename)
        
        # Write to output file
        df.to_csv(output_file, index=False)
        print(f"Processing complete. Results written to {output_file}")
        
        # Calculate and display accuracy report
        accuracy_report = calculate_accuracy(df)
        print("\n--- CSAT Prediction Accuracy Report ---")
        print(accuracy_report)
        
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process CSV file for CSAT prediction.')
    parser.add_argument('-file', dest='file', help='Input CSV file path')
    args = parser.parse_args()
    
    input_file = args.file
    
    # If no file argument was provided, prompt the user
    if not input_file:
        input_file = input("Please enter the CSV file name: ")
    
    # Normalize the file path to handle spaces and special characters
    input_file = normalize_file_path(input_file)
    
    process_file(input_file)

if __name__ == "__main__":
    main() 