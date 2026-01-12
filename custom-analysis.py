#!/usr/bin/env python3
"""
AI Support Analyzer - Custom Analysis Module
by @wiesenhauss

This script provides flexible custom analysis capabilities, allowing users to:
- Define custom AI analysis prompts
- Select specific columns from CSV data for analysis
- Generate tailored insights based on user requirements

Features:
- Custom prompt input for specialized analysis
- Column selection for targeted data analysis
- Configurable record processing limits via -limit parameter
- AI-powered analysis using OpenAI GPT models (gpt-4.1)
- Handles file paths with spaces and special characters
- Flexible output formatting based on analysis type

Usage:
  python custom-analysis.py -file="path/to/data.csv" -prompt="Your custom prompt" -columns="col1,col2,col3" [-limit=10000]
  python custom-analysis.py  # Interactive mode - prompts for all parameters

Arguments:
  -file     Path to CSV file containing the data to analyze
  -prompt   Custom analysis prompt for AI processing
  -columns  Comma-separated list of column names to include in analysis
  -limit    Maximum number of records to analyze (optional, default: all records)

Environment Variables:
  OPENAI_API_KEY  Required for AI-powered analysis

Output:
  Creates a custom analysis report:
  custom-analysis-YYYY-MM-DD-HHMM.txt
"""

import pandas as pd
import openai
from datetime import datetime
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
import os
import sys
import argparse

# Import shared utilities
from utils import (
    normalize_file_path,
    find_column_by_substring,
    get_openai_client,
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Custom analysis of CSV data with user-defined prompts and columns.')
    parser.add_argument('-file', type=str, help='Path to the CSV file containing data to analyze')
    parser.add_argument('-prompt', type=str, help='Custom analysis prompt for AI processing')
    parser.add_argument('-columns', type=str, help='Comma-separated list of column names to include')
    parser.add_argument('-limit', type=int, help='Maximum number of records to process (default: no limit)')
    return parser.parse_args()

def get_parameters():
    """Get analysis parameters from command line arguments or interactive input."""
    args = parse_arguments()
    
    # Get file path
    if args.file:
        file_path = args.file.strip()
    else:
        file_path = input("Please enter the path to the CSV file: ").strip()
    
    # Get custom prompt
    if args.prompt:
        custom_prompt = args.prompt.strip()
    else:
        print("\nEnter your custom analysis prompt:")
        print("(This will guide the AI in analyzing your data)")
        custom_prompt = input("Prompt: ").strip()
    
    # Get columns
    if args.columns:
        columns = [col.strip() for col in args.columns.split(',')]
    else:
        print("\nEnter column names to analyze (comma-separated):")
        print("(e.g., ticket_id,chat_transcript,happiness_score)")
        columns_input = input("Columns: ").strip()
        columns = [col.strip() for col in columns_input.split(',')]
    
    return file_path, custom_prompt, columns, args.limit

def read_csv_data(file_path: str, selected_columns: List[str]) -> pd.DataFrame:
    """Read the CSV file and extract selected columns."""
    try:
        file_path = normalize_file_path(file_path)
        df = pd.read_csv(file_path)
        
        # Find actual column names using fuzzy matching
        actual_columns = []
        missing_columns = []
        
        for col in selected_columns:
            actual_col = find_column_by_substring(df, col)
            if actual_col:
                actual_columns.append(actual_col)
            else:
                missing_columns.append(col)
        
        if missing_columns:
            available_columns = list(df.columns)
            raise ValueError(f"Columns not found: {missing_columns}. Available columns: {available_columns}")
        
        # Return only selected columns
        return df[actual_columns]
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        raise

def prepare_content_for_analysis(df: pd.DataFrame, limit: int = None) -> str:
    """Prepare the content from DataFrame for analysis."""
    content_parts = []
    
    # Apply limit if specified, otherwise process all records
    data_to_process = df.head(limit) if limit else df
    
    content_parts.append(f"Dataset contains {len(data_to_process)} records with the following columns:")
    content_parts.append(f"Columns: {', '.join(df.columns.tolist())}")
    content_parts.append("=" * 80)
    content_parts.append("")
    
    for index, row in data_to_process.iterrows():
        content_parts.append(f"Record {index + 1}:")
        for column in df.columns:
            value = row[column]
            # Handle NaN values
            if pd.isna(value):
                value = "N/A"
            content_parts.append(f"{column}: {value}")
        content_parts.append("-" * 50)
    
    return "\n".join(content_parts)

def analyze_with_openai(content: str, custom_prompt: str) -> str:
    """Send content to OpenAI API for custom analysis."""
    try:
        # Use shared OpenAI client for connection reuse
        client = get_openai_client(api_key=OPENAI_API_KEY)
        
        # Combine custom prompt with data context
        full_prompt = f"""You are an expert data analyst. The user has provided the following analysis request:

CUSTOM ANALYSIS REQUEST:
{custom_prompt}

Please analyze the following dataset according to the user's request. Provide detailed insights, patterns, and recommendations based on the data and the specific analysis requested.

DATA TO ANALYZE:
{content}

Please provide a comprehensive analysis that addresses the user's specific request while highlighting any notable patterns, trends, or insights you discover in the data."""

        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert data analyst specializing in custom data analysis. Provide clear, actionable insights based on the user's specific requirements."
                },
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            max_tokens=4000,
            temperature=0.3
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error with OpenAI API: {str(e)}")
        raise

def save_analysis(analysis: str, custom_prompt: str, columns: List[str], output_file: str):
    """Save the analysis results to a file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("AI SUPPORT ANALYZER - CUSTOM ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Analysis Prompt: {custom_prompt}\n")
            f.write(f"Analyzed Columns: {', '.join(columns)}\n")
            f.write("=" * 80 + "\n\n")
            f.write(analysis)
        
        logger.info(f"Analysis saved to: {output_file}")
    except Exception as e:
        logger.error(f"Error saving analysis: {str(e)}")
        raise

def main():
    """Main function to run custom analysis."""
    try:
        print("🤖 AI Support Analyzer - Custom Analysis")
        print("=" * 50)
        
        # Get parameters
        file_path, custom_prompt, columns, limit = get_parameters()
        
        # Validate inputs
        if not file_path:
            raise ValueError("File path is required")
        if not custom_prompt:
            raise ValueError("Custom prompt is required")
        if not columns:
            raise ValueError("At least one column must be selected")
        
        print(f"\n📊 Reading data from: {file_path}")
        print(f"🎯 Analysis prompt: {custom_prompt[:100]}...")
        print(f"📋 Selected columns: {', '.join(columns)}")
        if limit:
            print(f"🔢 Processing limit: {limit} records")
        
        # Read data
        df = read_csv_data(file_path, columns)
        print(f"✅ Loaded {len(df)} records")
        
        # Apply limit if specified
        if limit and limit < len(df):
            df = df.head(limit)
            print(f"🔄 Limited to {len(df)} records for analysis")
        
        # Prepare content
        print("🔄 Preparing data for analysis...")
        content = prepare_content_for_analysis(df, limit)
        
        # Analyze with OpenAI
        print("🤖 Analyzing data with AI...")
        analysis = analyze_with_openai(content, custom_prompt)
        
        # Save results in the same directory as the input file
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
        input_dir = os.path.dirname(os.path.abspath(file_path))
        output_filename = f"custom-analysis-{timestamp}.txt"
        output_file = os.path.join(input_dir, output_filename)
        save_analysis(analysis, custom_prompt, columns, output_file)
        
        print("✅ Custom analysis completed successfully!")
        print(f"📄 Report saved: {output_filename}")
        print(f"📂 Location: {input_dir}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 