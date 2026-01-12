#!/usr/bin/env python3
from __future__ import annotations
"""
WordPress.com CSAT Trends and Patterns Analysis
by @wiesenhauss

This script analyzes customer satisfaction (CSAT) data from processed support interactions to 
identify trends, patterns, and actionable insights for support team optimization. It examines
multiple dimensions of customer feedback including temporal trends, response metrics, topic
analysis, and correlations between various support factors.

Features:
- Comprehensive CSAT trends analysis over time periods
- Response time and resolution metrics correlation analysis
- Sentiment analysis integration with CSAT ratings
- Topic frequency and impact analysis
- Product vs service issue categorization
- Configurable record processing limits via -limit parameter
- AI-powered insights using OpenAI GPT models (gpt-4.1)
- Detailed reporting with specific ticket examples and URLs
- Handles file paths with spaces and special characters

Analysis Areas:
- Ticket volume trends and peak periods
- CSAT rating distributions and temporal patterns
- Response time impact on customer satisfaction
- Common interaction topics and their resolution rates
- Product-related vs service-related issue analysis
- Sentiment correlation with CSAT outcomes

Usage:
  python csat-trends.py -file="path/to/analysis_output.csv" [-limit=1000]
  python csat-trends.py  # Interactive mode - prompts for file path

Arguments:
  -file     Path to CSV file containing processed analysis results
  -limit    Maximum number of records to analyze (optional, default: all records)

Required CSV Columns:
  - Created Date, Zendesk Ticket URL, CSAT Rating, CSAT Reason, CSAT Comment
  - First reply time without AI (hours), Total time spent (mins)
  - SENTIMENT_ANALYSIS, ISSUE_RESOLVED, INTERACTION_TOPICS
  - RELATED_TO_PRODUCT, RELATED_TO_SERVICE

Environment Variables:
  OPENAI_API_KEY  Required for AI-powered trend analysis

Output:
  Creates a comprehensive analysis report:
  csat-trends-YYYY-MM-DD-HHMM.txt
"""

import pandas as pd
import openai
from datetime import datetime
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
import os
import argparse

# Import shared utilities
from utils import (
    normalize_file_path,
    find_column_by_substring,
    get_openai_client,
    prepare_records_for_analysis,
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

def read_csv_data(file_path: str) -> pd.DataFrame:
    """
    Read the CSV file and verify required columns exist.
    """
    try:
        df = pd.read_csv(file_path)
        # Define truly required columns vs optional ones
        required_columns = [
            "Created Date",
            "Zendesk Ticket URL",
            "CSAT Rating",
            "CSAT Reason",
            "CSAT Comment",
            "SENTIMENT_ANALYSIS",
            "ISSUE_RESOLVED",
            "INTERACTION_TOPICS",
            "RELATED_TO_PRODUCT",
            "RELATED_TO_SERVICE"
        ]
        
        # Optional columns (may not exist in all CSVs)
        optional_columns = [
            "First reply time without AI (hours)",
            "Total time spent (mins)"
        ]
        
        # Find actual column names using fuzzy matching and verify required ones exist
        missing_required = []
        column_mapping = {}
        
        for col in required_columns:
            actual_col = find_column_by_substring(df, col)
            if actual_col:
                column_mapping[col] = actual_col
            else:
                missing_required.append(col)
        
        # Find optional columns if they exist
        for col in optional_columns:
            actual_col = find_column_by_substring(df, col)
            if actual_col:
                column_mapping[col] = actual_col
        
        if missing_required:
            raise ValueError(f"Missing required columns: {missing_required}")
        
        # Store column mapping in DataFrame attributes for later use
        df.attrs['column_mapping'] = column_mapping
            
        # Return full DataFrame to avoid breaking existing code
        return df
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        raise

def prepare_content_for_analysis(df: pd.DataFrame, limit: int = None) -> str:
    """
    Prepare the content from DataFrame for analysis.
    
    Uses StringIO for efficient string building on large datasets.
    """
    from io import StringIO
    
    buffer = StringIO()
    
    # Get column mapping if available
    column_mapping = df.attrs.get('column_mapping', {})
    
    # Helper function to safely get column value
    def get_col_value(row, key):
        col_name = column_mapping.get(key, key)
        try:
            if col_name in row.index:
                value = row[col_name]
                return value if pd.notna(value) else 'N/A'
            return 'N/A'
        except (KeyError, AttributeError):
            return 'N/A'
    
    # Apply limit if specified, otherwise process all records
    data_to_process = df.head(limit) if limit else df
    
    for idx, (_, row) in enumerate(data_to_process.iterrows(), 1):
        buffer.write(f"Record {idx}:\n")
        buffer.write(f"Created Date: {get_col_value(row, 'Created Date')}\n")
        buffer.write(f"Ticket URL: {get_col_value(row, 'Zendesk Ticket URL')}\n")
        buffer.write(f"CSAT Rating: {get_col_value(row, 'CSAT Rating')}\n")
        buffer.write(f"CSAT Reason: {get_col_value(row, 'CSAT Reason')}\n")
        buffer.write(f"CSAT Comment: {get_col_value(row, 'CSAT Comment')}\n")
        
        # Optional columns - only add if they exist
        first_reply_time = get_col_value(row, 'First reply time without AI (hours)')
        if first_reply_time != 'N/A':
            buffer.write(f"First Reply Time (hours): {first_reply_time}\n")
        
        total_time = get_col_value(row, 'Total time spent (mins)')
        if total_time != 'N/A':
            buffer.write(f"Total Time (mins): {total_time}\n")
        
        buffer.write(f"Sentiment Analysis: {get_col_value(row, 'SENTIMENT_ANALYSIS')}\n")
        buffer.write(f"Issue Resolved: {get_col_value(row, 'ISSUE_RESOLVED')}\n")
        buffer.write(f"Interaction Topics: {get_col_value(row, 'INTERACTION_TOPICS')}\n")
        buffer.write(f"Related to Product: {get_col_value(row, 'RELATED_TO_PRODUCT')}\n")
        buffer.write(f"Related to Service: {get_col_value(row, 'RELATED_TO_SERVICE')}\n")
        buffer.write("-" * 50 + "\n")
    
    return buffer.getvalue()

def get_default_prompt() -> str:
    """
    Get the default analysis prompt for CSAT trends analysis.
    """
    return """As an AI customer support supervisor for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others), you are assigned to review and analyze a comprehensive dataset of support interactions. The dataset contains the following fields:
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

"""

def analyze_with_openai(content: str, custom_prompt: str = None) -> str:
    """
    Send content to OpenAI API for CSAT trends analysis.
    """
    try:
        # Use shared OpenAI client for connection reuse
        client = get_openai_client(api_key=OPENAI_API_KEY)
        
        # Use custom prompt if provided, otherwise use default
        analysis_prompt = custom_prompt if custom_prompt else get_default_prompt()
        
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "user", "content": analysis_prompt + content}
            ],
            max_completion_tokens=5000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error in OpenAI API call: {str(e)}")
        raise

def save_analysis(analysis: str, output_file: str):
    """
    Save the analysis results to a file.
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(analysis)
        logger.info(f"Analysis saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving analysis: {str(e)}")
        raise

def main():
    try:
        # Set up argument parser
        parser = argparse.ArgumentParser(description='Process CSAT data and generate trends analysis')
        parser.add_argument('-file', type=str, help='Path to the CSV file to process')
        parser.add_argument('-limit', type=int, help='Maximum number of records to process (default: no limit)')
        parser.add_argument('-prompt', type=str, help='Custom analysis prompt to use instead of default')
        args = parser.parse_args()
        
        # Get input filename from command line argument or prompt
        if args.file:
            input_filename = normalize_file_path(args.file)
        else:
            input_filename = normalize_file_path(input("Please enter the CSV filename to process: "))
        
        # Read and process CSV
        df = read_csv_data(input_filename)
        logger.info(f"CSV data loaded successfully from {input_filename}")

        # Prepare content for analysis
        if args.limit:
            logger.info(f"Processing limited to {args.limit} records")
            content = prepare_content_for_analysis(df, args.limit)
        else:
            logger.info("Processing all records (no limit specified)")
            content = prepare_content_for_analysis(df)
        logger.info("Content prepared for analysis")

        # Get analysis from OpenAI
        custom_prompt = args.prompt if args.prompt else None
        if custom_prompt:
            logger.info("Using custom analysis prompt")
        else:
            logger.info("Using default analysis prompt")
        
        analysis = analyze_with_openai(content, custom_prompt)
        logger.info("OpenAI analysis completed")

        # Generate timestamp-based filename
        current_time = datetime.now()
        timestamp = f"{current_time.year}-{current_time.month:02d}-{current_time.day:02d}-{current_time.strftime('%H%M')}"
        
        # Extract directory from input file path
        input_dir = os.path.dirname(input_filename)
        base_output_name = f"csat-trends-{timestamp}.txt"
        
        # Combine directory with new filename
        if input_dir:
            output_filename = os.path.join(input_dir, base_output_name)
        else:
            # If no directory specified (just filename), use current directory
            output_filename = base_output_name

        # Save results
        save_analysis(analysis, output_filename)
        logger.info(f"Analysis saved to {output_filename}")

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()