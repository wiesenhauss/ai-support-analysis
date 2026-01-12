#!/usr/bin/env python3
from __future__ import annotations
"""
WordPress.com Product Feedback Trends Analysis
by @wiesenhauss

This script analyzes product feedback extracted from customer support interactions to identify
trends, patterns, and actionable insights for product development and enhancement. It processes
feedback comments and generates comprehensive analysis reports focusing on feature requests,
usability issues, and product improvement opportunities.

Features:
- Product feedback extraction and trend analysis
- Feature request categorization and prioritization
- User experience pain point identification  
- Product performance and usability insights
- Configurable Record processing limits via -limit parameter
- AI-powered analysis using OpenAI GPT models (gpt-4.1)
- Temporal trend analysis for product feedback evolution
- Filtering of meaningful feedback (excludes "NONE" entries)
- Handles file paths with spaces and special characters

Analysis Areas:
- Common product issues and pain points reported by users
- Feature requests and enhancement suggestions with frequency
- Product satisfaction patterns and user experience feedback
- Usability challenges and interface improvement opportunities
- Integration between product issues and support ticket resolution
- Temporal trends showing evolving product feedback patterns

Usage:
  python product-feedback-trends.py -file="path/to/analysis_output.csv" [-limit=40000]
  python product-feedback-trends.py  # Interactive mode - prompts for file path

Arguments:
  -file     Path to CSV file containing analysis results with product feedback
  -limit    Maximum number of records to analyze (optional, default: all records)

Required CSV Columns:
  - Created Date, Zendesk Ticket URL, PRODUCT_FEEDBACK
  - Optional: CSAT Rating, INTERACTION_TOPICS, ISSUE_RESOLVED

Environment Variables:
  OPENAI_API_KEY  Required for AI-powered product feedback analysis

Output:
  Creates a detailed product insights report:
  product-feedback-trends-YYYY-MM-DD-HHMM.txt
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
    extract_ticket_id,
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
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='Process product feedback data from CSV file.')
    parser.add_argument('-file', type=str, help='Path to the CSV file containing product feedback data')
    parser.add_argument('-limit', type=int, help='Maximum number of records to process (default: no limit)')
    parser.add_argument('-prompt', type=str, help='Custom analysis prompt to use instead of default')
    return parser.parse_args()

def get_csv_file_path():
    """
    Ask the user for the CSV file path or use command line argument if provided.
    """
    args = parse_arguments()
    
    if args.file:
        return args.file.strip()
    else:
        file_path = input("Please enter the path to the CSV file containing product feedback data: ")
        return file_path.strip()

def read_csv_data(file_path: str) -> pd.DataFrame:
    """
    Read the CSV file, extract required columns, and filter out rows with "NONE" in PRODUCT_FEEDBACK.
    """
    try:
        df = pd.read_csv(file_path)
        
        # Find PRODUCT_FEEDBACK column using fuzzy matching
        product_feedback_col = find_column_by_substring(df, "PRODUCT_FEEDBACK")
        if not product_feedback_col:
            raise ValueError("Required column 'PRODUCT_FEEDBACK' not found in the CSV file")
            
        # Filter out rows with "NONE" in PRODUCT_FEEDBACK
        df = df[df[product_feedback_col].notna() & (df[product_feedback_col].str.upper() != "NONE")]
        
        if df.empty:
            raise ValueError("No valid product feedback data found after filtering")
        
        # Verify optional columns exist (for compatibility checking)
        optional_columns = ["CSAT Rating", "INTERACTION_TOPICS", "ISSUE_RESOLVED"]
        for col in optional_columns:
            find_column_by_substring(df, col)  # Just verify, don't filter
                
        # Return full DataFrame to avoid breaking existing code
        return df
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        raise

def prepare_content_for_analysis(df: pd.DataFrame, limit: int = None) -> str:
    """
    Prepare the content from DataFrame for analysis.
    Extract ticket ID from Zendesk URL.
    
    Uses StringIO for efficient string building on large datasets.
    """
    from io import StringIO
    
    buffer = StringIO()
    
    # Find columns using fuzzy matching
    created_date_col = find_column_by_substring(df, 'Created Date')
    ticket_url_col = find_column_by_substring(df, 'Zendesk Ticket URL')
    product_feedback_col = find_column_by_substring(df, 'PRODUCT_FEEDBACK')
    csat_rating_col = find_column_by_substring(df, 'CSAT Rating')
    interaction_topics_col = find_column_by_substring(df, 'INTERACTION_TOPICS')
    issue_resolved_col = find_column_by_substring(df, 'ISSUE_RESOLVED')
    
    # Apply limit if specified, otherwise process all records
    data_to_process = df.head(limit) if limit else df
    
    for idx, (_, row) in enumerate(data_to_process.iterrows(), 1):
        buffer.write(f"Record {idx}:\n")
        buffer.write(f"Created Date: {row.get(created_date_col, 'N/A')}\n")
        
        # Extract and include only the ticket ID
        ticket_url = row.get(ticket_url_col, 'N/A')
        ticket_id = extract_ticket_id(ticket_url)
        buffer.write(f"Ticket ID: {ticket_id}\n")
        
        buffer.write(f"Product Feedback: {row.get(product_feedback_col, 'N/A')}\n")
        
        # Add optional fields if available
        if csat_rating_col:
            buffer.write(f"CSAT Rating: {row.get(csat_rating_col, 'N/A')}\n")
        if interaction_topics_col:
            buffer.write(f"Interaction Topics: {row.get(interaction_topics_col, 'N/A')}\n")
        if issue_resolved_col:
            buffer.write(f"Issue Resolved: {row.get(issue_resolved_col, 'N/A')}\n")
            
        buffer.write("-" * 50 + "\n")
    
    return buffer.getvalue()

def get_default_prompt() -> str:
    """
    Get the default analysis prompt for product feedback trends analysis.
    """
    return """As a product insights analyst for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others), you are assigned to review and analyze a dataset of customer product feedback collected from support interactions. The dataset contains the following fields:
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

"""

def analyze_with_openai(content: str, custom_prompt: str = None) -> str:
    """
    Send content to OpenAI API for product feedback analysis.
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
            max_completion_tokens=25000
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
        # Parse arguments
        args = parse_arguments()
        
        # Get file path
        if args.file:
            file_path = normalize_file_path(args.file.strip())
        else:
            file_path = normalize_file_path(input("Please enter the path to the CSV file containing product feedback data: ").strip())
        
        # Read and process CSV
        df = read_csv_data(file_path)
        logger.info(f"CSV data loaded successfully. Found {len(df)} records with valid product feedback.")

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
        
        # Get the directory of the input file
        input_directory = os.path.dirname(file_path)
        if input_directory == "":
            input_directory = "."  # Use current directory if no directory specified
            
        output_filename = f"product-feedback-trends-{current_time.year}-{current_time.month:02d}-{current_time.day:02d}-{current_time.strftime('%H%M')}.txt"
        
        # Create full output path in the same directory as input file
        output_path = os.path.join(input_directory, output_filename)

        # Save results
        save_analysis(analysis, output_path)
        logger.info(f"Analysis saved to {output_path}")
        print(f"\nAnalysis complete! Results saved to: {output_path}")

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()