#!/usr/bin/env python3
"""
WordPress.com Customer Goals and Objectives Analysis
by @wiesenhauss

This script analyzes customer goals extracted from support interactions to understand what 
customers are trying to accomplish and identify patterns in customer objectives, task completion
barriers, and journey insights. It provides actionable insights for improving user experience
and reducing friction in customer workflows.

Features:
- Customer goal categorization and pattern analysis
- Task completion obstacle identification
- Customer journey stage insights and mapping
- Goal complexity analysis and clarity assessment
- Configurable record processing limits via -limit parameter
- AI-powered analysis using OpenAI GPT models (gpt-4.1)
- Temporal trend analysis for evolving customer objectives
- Filtering of meaningful goals (excludes "NONE" and incomplete entries)
- Handles file paths with spaces and special characters

Analysis Areas:
- Most common customer objectives and intentions
- Customer goal clustering into broader categories and themes
- Customer journey stages represented in support interactions
- Task complexity distribution (basic vs advanced functions)
- Common barriers preventing independent goal completion
- Goal clarity and customer self-service opportunities
- Temporal trends in customer goal evolution

Usage:
  python goals-trends.py -file="path/to/analysis_output.csv" [-limit=40000]
  python goals-trends.py  # Interactive mode - prompts for file path

Arguments:
  -file     Path to CSV file containing analysis results with customer goals
  -limit    Maximum number of records to analyze (optional, default: all records)

Required CSV Columns:
  - Created Date, Zendesk Ticket URL, CUSTOMER_GOAL
  - Optional: CSAT Rating, INTERACTION_TOPICS, ISSUE_RESOLVED

Environment Variables:
  OPENAI_API_KEY  Required for AI-powered customer goal analysis

Output:
  Creates a comprehensive customer journey insights report:
  customer-goals-trends-YYYY-MM-DD-HHMM.txt
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
    analyze_with_context_retry,
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
    parser = argparse.ArgumentParser(description='Analyze customer goals from support interactions.')
    parser.add_argument('-file', type=str, help='Path to the CSV file containing customer goal data')
    parser.add_argument('-limit', type=int, help='Maximum number of records to process (default: no limit)')
    parser.add_argument('-prompt', type=str, help='Custom analysis prompt to use instead of default')
    return parser.parse_args()

def get_csv_file_path():
    """
    Ask the user for the CSV file path.
    """
    file_path = input("Please enter the path to the CSV file containing customer goal data: ")
    return file_path.strip()

def read_csv_data(file_path: str) -> pd.DataFrame:
    """
    Read the CSV file, extract required columns, and filter out rows with "NONE" or "Analysis incomplete" 
    in CUSTOMER_GOAL.
    """
    try:
        df = pd.read_csv(file_path)
        
        # Find CUSTOMER_GOAL column using fuzzy matching
        customer_goal_col = find_column_by_substring(df, "CUSTOMER_GOAL")
        if not customer_goal_col:
            raise ValueError("Required column 'CUSTOMER_GOAL' not found in the CSV file")
            
        # Filter out rows with "NONE" or "Analysis incomplete" in CUSTOMER_GOAL
        df = df[df[customer_goal_col].notna() & 
                (df[customer_goal_col].str.upper() != "NONE") & 
                (~df[customer_goal_col].str.contains("Analysis incomplete", case=False, na=False))]
        
        if df.empty:
            raise ValueError("No valid customer goal data found after filtering")
        
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
    customer_goal_col = find_column_by_substring(df, 'CUSTOMER_GOAL')
    csat_rating_col = find_column_by_substring(df, 'CSAT Rating')
    
    # Apply limit if specified, otherwise process all records
    data_to_process = df.head(limit) if limit else df
    
    for idx, (_, row) in enumerate(data_to_process.iterrows(), 1):
        buffer.write(f"Record {idx}:\n")
        buffer.write(f"Created Date: {row.get(created_date_col, 'N/A')}\n")
        
        # Extract and include only the ticket ID
        ticket_url = row.get(ticket_url_col, 'N/A')
        ticket_id = extract_ticket_id(ticket_url)
        buffer.write(f"Ticket ID: {ticket_id}\n")
        
        buffer.write(f"Customer Goal: {row.get(customer_goal_col, 'N/A')}\n")
        
        # Add optional fields if available (excluding INTERACTION_TOPICS)
        if csat_rating_col:
            buffer.write(f"CSAT Rating: {row.get(csat_rating_col, 'N/A')}\n")
            
        buffer.write("-" * 50 + "\n")
    
    return buffer.getvalue()

def get_default_prompt() -> str:
    """
    Get the default analysis prompt for customer goals analysis.
    """
    return """As a customer experience analyst for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others), you are assigned to review and analyze a dataset of customer goals collected from support interactions. The dataset contains the following fields:
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

def analyze_with_openai(content: str, custom_prompt: str = None) -> str:
    """
    Send content to OpenAI API for customer goals analysis.
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
        # Parse command line arguments
        args = parse_arguments()
        
        # Get file path from command line argument or user input
        if args.file:
            file_path = normalize_file_path(args.file)
            logger.info(f"Using file path from command line argument: {file_path}")
        else:
            # Ask for CSV file path if not provided as argument
            file_path = normalize_file_path(get_csv_file_path())
        
        # Read and process CSV
        df = read_csv_data(file_path)
        logger.info(f"CSV data loaded successfully. Found {len(df)} records with valid customer goals.")

        # Get custom prompt if provided
        custom_prompt = args.prompt if args.prompt else None
        if custom_prompt:
            logger.info("Using custom analysis prompt")
        else:
            logger.info("Using default analysis prompt")

        # Use retry mechanism to handle context length exceeded errors
        if args.limit:
            logger.info(f"Processing limited to {args.limit} records")
        else:
            logger.info("Processing all records (no limit specified)")
        
        analysis, rows_used = analyze_with_context_retry(
            df=df,
            prepare_func=lambda sample_df: prepare_content_for_analysis(sample_df),
            analyze_func=lambda content: analyze_with_openai(content, custom_prompt),
            initial_limit=args.limit,
            logger=logger
        )
        logger.info(f"OpenAI analysis completed using {rows_used} rows")

        # Generate timestamp-based filename
        current_time = datetime.now()
        
        # Extract directory from input file path and create output path
        input_dir = os.path.dirname(file_path)
        output_filename = f"customer-goals-trends-{current_time.year}-{current_time.month:02d}-{current_time.day:02d}-{current_time.strftime('%H%M')}.txt"
        
        # If input_dir is empty (current directory case), don't add path separator
        if input_dir:
            output_file_path = os.path.join(input_dir, output_filename)
        else:
            output_file_path = output_filename

        # Save results
        save_analysis(analysis, output_file_path)
        logger.info(f"Analysis saved to {output_file_path}")
        print(f"\nAnalysis complete! Results saved to: {output_file_path}")

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()