#!/usr/bin/env python3
"""
WordPress.com Daily Reports Aggregation Tool
by @wiesenhauss

This script combines multiple daily analysis reports into a unified weekly report using AI
to identify trends, patterns, and insights across all reports. It provides comprehensive
cross-report analysis that synthesizes findings from multiple analysis periods into
actionable weekly insights for support team management.

Features:
- Multi-file report combination and analysis
- Cross-report trend identification and pattern analysis
- AI-powered synthesis using OpenAI GPT models (gpt-4.1)
- Consistent formatting preservation from original reports
- Quantitative summary generation with percentage changes
- Timeline-based development tracking across reports
- Handles file paths with spaces and special characters
- Flexible input via command line or interactive prompts

Analysis Capabilities:
- Identifies recurring issues across multiple reporting periods
- Tracks progression of support metrics and customer satisfaction
- Highlights significant changes or developments over time
- Provides topic frequency analysis across all reports
- Generates cohesive narrative from disparate data points
- Creates actionable recommendations based on trend analysis

Usage:
  python aggregate-daily-reports.py -files="report1.txt,report2.txt,report3.txt"
  python aggregate-daily-reports.py  # Interactive mode - prompts for file list

Arguments:
  -files    Comma-separated list of report files to aggregate and analyze

Input:
  Multiple text files containing analysis reports from trend analysis scripts
  (e.g., csat-trends, product-feedback-trends, goals-trends outputs)

Output:
  Creates a comprehensive weekly synthesis report:
  unified-report-YYYY-MM-DD-HHMM.txt

Environment Variables:
  OPENAI_API_KEY  Required for AI-powered report synthesis
"""

import os
import sys
import argparse
import logging
import openai
from datetime import datetime
from typing import List
from dotenv import load_dotenv

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

def read_file_content(file_path: str) -> str:
    """
    Read the content of a file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        raise

def combine_report_contents(file_paths: List[str]) -> str:
    """
    Combine the contents of multiple report files.
    """
    combined_content = ""
    
    for i, file_path in enumerate(file_paths):
        # Normalize file path
        normalized_path = normalize_file_path(file_path)
        
        if not os.path.exists(normalized_path):
            logger.error(f"File '{normalized_path}' not found.")
            raise FileNotFoundError(f"File '{normalized_path}' not found.")
        
        content = read_file_content(normalized_path)
        file_name = os.path.basename(normalized_path)
        
        combined_content += f"\n\n{'='*50}\n"
        combined_content += f"REPORT {i+1}: {file_name}\n"
        combined_content += f"{'='*50}\n\n"
        combined_content += content
    
    return combined_content

def analyze_with_openai(content: str) -> str:
    """
    Send content to OpenAI API for comprehensive analysis and report generation.
    """
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        analysis_prompt = """As an AI analyst, create a comprehensive weekly report by analyzing the following daily reports from customer support data for WordPress.com. 

Your task is to:
1. Identify key trends, patterns, and insights across all reports
2. Highlight consistent issues or topics that appear in multiple reports
3. Note any significant changes or developments over time
4. Provide a quantitative summary where possible (e.g., topic frequencies, percentage changes)
5. Organize the information into logical categories
6. Create a cohesive narrative that synthesizes all the information

IMPORTANT: Maintain the same structure and formatting style as found in the individual reports. 
If the reports follow a specific format or have consistent section headings, preserve this structure 
in your unified report. The final report should feel like a natural extension of the individual reports.
If examples were shared, include them in your report (or a sample of them, if there are many).

Format your response as a professional weekly report with:
- An executive summary at the beginning
- The same section headings used in the original reports
- Bullet points for key findings where appropriate
- Recommendations based on the data (if appropriate)

Here are the daily reports to analyze:

"""

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
            f.write("# Unified Weekly Report\n\n")
            f.write("Generated on: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
            f.write(analysis)
        logger.info(f"Unified report saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving report: {str(e)}")
        raise

def get_input_filenames() -> List[str]:
    """
    Prompt the user to enter the filenames to be processed.
    """
    while True:
        filenames_input = input("Enter the report filenames to process (comma-separated): ")
        filenames = [filename.strip() for filename in filenames_input.split(',')]
        
        # Check if all files exist
        missing_files = [filename for filename in filenames if not os.path.exists(filename)]
        if missing_files:
            print(f"The following files were not found: {', '.join(missing_files)}")
            print("Please enter valid filenames.")
        else:
            return filenames

def parse_command_line_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='Aggregate daily reports into a unified weekly report.')
    parser.add_argument('-files', type=str, help='Comma-separated list of files to process')
    return parser.parse_args()

def main():
    try:
        # Check for command line arguments first
        args = parse_command_line_args()
        
        if args.files:
            # Command line mode
            input_filenames = [filename.strip() for filename in args.files.split(',')]
            logger.info(f"Processing files from command line: {', '.join(input_filenames)}")
        else:
            # Interactive mode
            input_filenames = get_input_filenames()
            logger.info(f"Processing files from user input: {', '.join(input_filenames)}")
        
        # Combine report contents
        combined_content = combine_report_contents(input_filenames)
        logger.info("Report contents combined successfully")

        # Get analysis from OpenAI
        analysis = analyze_with_openai(combined_content)
        logger.info("OpenAI analysis completed")

        # Generate timestamp-based filename
        current_time = datetime.now()
        timestamp = f"{current_time.year}-{current_time.month:02d}-{current_time.day:02d}-{current_time.strftime('%H%M')}"
        
        # Extract directory from first input file and create output path
        input_dir = os.path.dirname(os.path.abspath(input_filenames[0]))
        output_filename = os.path.join(input_dir, f"unified-report-{timestamp}.txt")

        # Save results
        save_analysis(analysis, output_filename)
        logger.info(f"Unified report saved to {output_filename}")

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
