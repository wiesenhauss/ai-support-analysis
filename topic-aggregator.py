#!/usr/bin/env python3
"""
WordPress.com Support Topic Aggregation and Categorization Tool
by @wiesenhauss

This script analyzes interaction topics from processed support data to identify and categorize
the most common customer contact reasons. It processes INTERACTION_TOPICS data from the main
analysis pipeline and uses AI to group topics into logical categories with quantitative analysis.

Features:
- Topic frequency analysis with occurrence counts and percentages
- AI-powered topic categorization using OpenAI GPT models (gpt-4.1)
- Hierarchical grouping of related topics into broader categories
- Quantitative analysis with category-level statistics
- Automatic output file generation with timestamps
- Comprehensive error handling and logging
- Handles file paths with spaces and special characters

Analysis Output:
- Topics grouped into logical categories (e.g., Domain Issues, Plugin/Theme Issues)
- Each category shows total occurrences and percentage of all interactions
- Individual topics within categories sorted by frequency
- Clear hierarchical structure for support team analysis

Usage:
  python topic-aggregator.py -file="path/to/analysis_output.csv"
  python topic-aggregator.py  # Interactive mode - prompts for file path

Arguments:
  -file    Path to the CSV file containing analysis results with topic data

Required CSV Columns:
  - INTERACTION_TOPICS (main topics from analysis)
  - CSAT Reason, CSAT Comment, DETAIL_SUMMARY, WHAT_HAPPENED
  - CSAT Rating Date, Zendesk Ticket URL

Environment Variables:
  OPENAI_API_KEY  Required for AI-powered topic categorization

Output:
  Creates a timestamped text file with categorized topic analysis:
  topic-aggregation-YYYY-MM-DD-HHMM.txt
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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

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

def read_csv_data(file_path: str) -> pd.DataFrame:
    """
    Read the CSV file and verify required columns exist.
    """
    try:
        df = pd.read_csv(file_path)
        required_columns = [
            "INTERACTION_TOPICS",
            "CSAT Reason", 
            "CSAT Comment", 
            "DETAIL_SUMMARY", 
            "WHAT_HAPPENED",
            "CSAT Rating Date",
            "Zendesk Ticket URL"
        ]
        
        # Find actual column names using fuzzy matching
        missing_columns = []
        
        for col in required_columns:
            actual_col = find_column_by_substring(df, col)
            if not actual_col:
                missing_columns.append(col)
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
            
        # Return full DataFrame (not just selected columns) to avoid breaking code
        return df
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        raise

def prepare_content_for_analysis(df: pd.DataFrame) -> str:
    """
    Prepare the content from DataFrame for analysis, focusing on INTERACTION_TOPICS.
    Count occurrences of each topic for quantitative analysis.
    """
    # Find the actual column name using fuzzy matching
    topics_col = find_column_by_substring(df, 'INTERACTION_TOPICS')
    if not topics_col:
        raise ValueError("INTERACTION_TOPICS column not found")
    
    # Extract and count all topics
    topic_counts = {}
    for topics in df[topics_col].dropna():
        # Split topics if they're in a list format
        if isinstance(topics, str):
            # Remove brackets and quotes if present
            topics = topics.strip('[]').replace("'", "").replace('"', '')
            topic_list = [t.strip() for t in topics.split(',')]
            for topic in topic_list:
                if topic:  # Skip empty topics
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    # Sort topics by frequency (descending)
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    total_occurrences = sum(topic_counts.values())
    
    # Prepare the content for OpenAI
    content = "Here is a list of all interaction topics with their occurrence counts:\n\n"
    for topic, count in sorted_topics:
        percentage = (count / total_occurrences) * 100
        content += f"- {topic}: {count} occurrences ({percentage:.1f}%)\n"
    
    content += f"\nTotal topics analyzed: {len(sorted_topics)}"
    content += f"\nTotal occurrences: {total_occurrences}"
    
    return content

def get_default_prompt() -> str:
    """
    Get the default analysis prompt for topic categorization.
    """
    return """As an AI customer support supervisor for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others), analyze these interaction topics and group them into logical categories. 

Please organize these topics into broad categories with similar themes, including quantitative data. For example:

**Domain Issues (235 occurrences, 32%)**
- DNS configuration issues (78 occurrences, 10.6%)
- Domain connection problems (65 occurrences, 8.8%)
- Domain mapping issues (45 occurrences, 6.1%)
- Domain registration (25 occurrences, 3.4%)
- Domain renewals (12 occurrences, 1.6%)
- Domain transfers (10 occurrences, 1.4%)

**Plugin/Theme Issues (180 occurrences, 24.5%)**
- Plugin compatibility problems (85 occurrences, 11.6%)
- Theme customization (55 occurrences, 7.5%)
- Theme installation errors (40 occurrences, 5.4%)

For each category:
1. Calculate the total occurrences and percentage of all topics in that category
2. List each topic with its individual occurrence count and percentage
3. Sort categories from highest to lowest occurrence count
4. Within each category, sort topics from highest to lowest occurrence count

Make the categorization clear and intuitive for support team analysis.

Here are the topics to categorize with their occurrence counts:

"""

def analyze_with_openai(content: str, custom_prompt: str = None) -> str:
    """
    Send content to OpenAI API for topic categorization analysis.
    """
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Use custom prompt if provided, otherwise use default
        analysis_prompt = custom_prompt if custom_prompt else get_default_prompt()
        
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "user", "content": analysis_prompt + content}
            ],
            max_completion_tokens=15000
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
            f.write("# Automattic Support Interaction Topics Analysis\n\n")
            f.write("Generated on: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
            f.write(analysis)
        logger.info(f"Analysis saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving analysis: {str(e)}")
        raise

def get_input_filename() -> str:
    """
    Prompt the user to enter the filename to be processed.
    """
    while True:
        filename = input("Enter the CSV filename to process: ")
        if os.path.exists(filename):
            return filename
        else:
            print(f"File '{filename}' not found. Please enter a valid filename.")

def parse_command_line_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='Analyze CSAT data and interaction topics.')
    parser.add_argument('-file', type=str, help='Path to the CSV file to process')
    parser.add_argument('-prompt', type=str, help='Custom analysis prompt to use instead of default')
    return parser.parse_args()

def main():
    try:
        # Check for command line arguments first
        args = parse_command_line_args()
        
        if args.file:
            # Command line mode
            input_filename = normalize_file_path(args.file)
            if not os.path.exists(input_filename):
                logger.error(f"File '{input_filename}' not found.")
                sys.exit(1)
            logger.info(f"Processing file from command line: {input_filename}")
        else:
            # Interactive mode
            input_filename = normalize_file_path(get_input_filename())
            logger.info(f"Processing file from user input: {input_filename}")
        
        # Read and process CSV
        df = read_csv_data(input_filename)
        logger.info("CSV data loaded successfully")

        # Prepare content for analysis
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
        
        # Extract directory from input file and create output path
        input_dir = os.path.dirname(os.path.abspath(input_filename))
        output_filename = os.path.join(input_dir, f"topic-categories-{timestamp}.txt")

        # Save results
        save_analysis(analysis, output_filename)
        logger.info(f"Analysis saved to {output_filename}")

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()