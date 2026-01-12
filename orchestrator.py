#!/usr/bin/env python3
from __future__ import annotations
"""
WordPress.com Support Analysis Pipeline Orchestrator
by @wiesenhauss

This script orchestrates the complete support analysis pipeline by running all component scripts
in the correct sequence. It processes raw support data through multiple analysis stages to generate
comprehensive insights and reports.

Pipeline Stages:
1. support-data-precleanup.py - Initial data cleanup
2. main-analysis-process.py - Core CSAT and sentiment analysis
3. support-data-cleanup.py - Post-analysis data cleanup
4. predict_csat.py - CSAT prediction and accuracy analysis
5. topic-aggregator.py - Topic categorization and analysis
6. csat-trends.py - CSAT trends and patterns analysis
7. product-feedback-trends.py - Product feedback trends analysis
8. goals-trends.py - Customer goals and objectives analysis
9. custom-analysis.py - Custom user-defined analysis (optional)

Features:
- Automatic file detection and chaining between pipeline stages
- Support for configurable record limits via -limit parameter
- Comprehensive logging with timestamps and progress tracking
- Error handling with detailed debugging information
- Handles file paths with spaces and special characters

Usage:
  python orchestrator.py -file="path/to/input.csv" [-limit=5000]
  python orchestrator.py  # Interactive mode - prompts for file path

Arguments:
  -file    Path to the input CSV file containing support data
  -limit   Maximum number of records to process in analysis scripts (optional)

Output:
  Creates multiple output files in the same directory as the input file:
  - Cleaned data files (*-preclean*.csv, *-clean*.csv)
  - Analysis results (*support-analysis-output*.csv)
  - Prediction data (*predictive-csat*.csv)
  - Multiple trend analysis reports (*.txt files)
"""

import os
import subprocess
import glob
import sys
import time
import logging
import argparse

# Import shared utilities
from utils import normalize_file_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('orchestrator.log')
    ]
)

def find_latest_file(pattern):
    """Find the most recently created file matching the given pattern."""
    matching_files = glob.glob(pattern)
    if not matching_files:
        logging.error(f"No files found matching pattern: {pattern}")
        sys.exit(1)
    
    # Sort by creation time, newest first
    latest_file = max(matching_files, key=os.path.getctime)
    logging.info(f"Found latest file: {latest_file}")
    return latest_file

def get_python_executable():
    """Get the correct Python executable path for the current environment."""
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle
        # Use the bundled Python interpreter
        return sys.executable
    else:
        # Running in development mode
        return sys.executable

def get_script_path(script_name):
    """Get the correct path to a script file."""
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle - scripts are in the bundle directory
        bundle_dir = sys._MEIPASS
        script_path = os.path.join(bundle_dir, script_name)
        if os.path.exists(script_path):
            return script_path
        else:
            logging.error(f"Script {script_name} not found in bundle at {script_path}")
            return None
    else:
        # Running in development mode - scripts are in current directory
        if os.path.exists(script_name):
            return script_name
        else:
            logging.error(f"Script {script_name} not found in current directory")
            return None

def run_script(script_name, args):
    """Run a Python script with the given arguments."""
    python_exe = get_python_executable()
    script_path = get_script_path(script_name)
    
    if not script_path:
        return False
    
    if getattr(sys, 'frozen', False):
        # Running as bundled executable - use the same executable to run the script
        # This ensures all modules are available
        command = [python_exe, script_path] + args
        logging.info(f"🐍 Found Python: {python_exe} (Bundled)")
    else:
        # Running in development mode
        command = [python_exe, script_path] + args
        logging.info(f"🐍 Found Python: {python_exe} (Development)")
    
    logging.info(f"   Running: {script_name} {' '.join(args)}")
    
    start_time = time.time()
    try:
        process = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        elapsed_time = time.time() - start_time
        logging.info(f"   ✅ Completed {script_name} in {elapsed_time:.2f} seconds")
        if process.stdout:
            logging.info(f"   📋 Output: {process.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"   ❌ {script_name} failed with exit code {e.returncode}")
        if e.stdout:
            for line in e.stdout.strip().split('\n'):
                logging.error(f"   ⚠️  {line}")
        if e.stderr:
            for line in e.stderr.strip().split('\n'):
                logging.error(f"   ⚠️  {line}")
        return False

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run support analysis pipeline')
    parser.add_argument('-file', help='Path to the input CSV file')
    parser.add_argument('-limit', type=int, help='Maximum number of records to process in analysis scripts (default: no limit)')
    return parser.parse_args()

def get_input_file(args):
    """Get input file from command line arguments or user input."""
    input_file = args.file
    
    # If no file provided via command line, ask user
    if not input_file:
        input_file = input("Please enter the path to the input CSV file: ").strip()
    
    # Normalize the file path to handle spaces and special characters
    input_file = normalize_file_path(input_file)
    
    # Validate input file exists
    if not os.path.exists(input_file):
        logging.error(f"Input file '{input_file}' not found")
        sys.exit(1)
    
    if not input_file.endswith('.csv'):
        logging.warning(f"Input file '{input_file}' does not have a .csv extension")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            logging.info("Operation cancelled by user")
            sys.exit(0)
    
    return input_file

def main():
    """Main orchestration function."""
    print("🚀 WordPress.com Support Analysis Pipeline")
    print("=" * 50)
    logging.info("Starting support analysis pipeline")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Get input file from command line or user input
    input_file = get_input_file(args)
    input_dir = os.path.dirname(input_file)
    
    # Pre-Step: Run support data cleanup on the input file
    print("📋 Step 1: Running initial data cleanup...")
    logging.info("Running initial data cleanup on input file")
    if not run_script("support-data-precleanup.py", [f"-file={input_file}"]):
        sys.exit(1)
    
    # Find the cleaned input file
    cleaned_input = find_latest_file(os.path.join(input_dir, "*-preclean*.csv"))
    
    # Step 1: Run CSAT processing
    print("📋 Step 2: Running core CSAT analysis...")
    if not run_script("main-analysis-process.py", [f"-file={cleaned_input}"]):
        sys.exit(1)
    
    # Step 2: Run support data cleanup again
    print("📋 Step 3: Running post-analysis data cleanup...")
    output1 = find_latest_file(os.path.join(input_dir, "*support-analysis-output*.csv"))
    if not run_script("support-data-cleanup.py", [f"-file={output1}"]):
        sys.exit(1)
    
    # Step 3: Run CSAT prediction
    print("📋 Step 4: Running CSAT prediction analysis...")
    output2 = find_latest_file(os.path.join(input_dir, "*-clean*.csv"))
    if not run_script("predict_csat.py", [f"-file={output2}"]):
        sys.exit(1)
    
    # Step 4: Run topic aggregator
    print("📋 Step 5: Running topic categorization...")
    output3 = find_latest_file(os.path.join(input_dir, "*support-analysis-output-predictive-csat*.csv"))
    if not run_script("topic-aggregator.py", [f"-file={output3}"]):
        sys.exit(1)
    
    # Step 5: Run CSAT trends processing
    print("📋 Step 6: Running CSAT trends analysis...")
    limit_args = [f"-limit={args.limit}"] if args.limit else []
    if not run_script("csat-trends.py", [f"-file={output3}"] + limit_args):
        sys.exit(1)
    
    # Step 6: Run product feedback trends processing
    print("📋 Step 7: Running product feedback trends analysis...")
    if not run_script("product-feedback-trends.py", [f"-file={output3}"] + limit_args):
        sys.exit(1)
    
    # Step 7: Run goals trends
    print("📋 Step 8: Running customer goals analysis...")
    if not run_script("goals-trends.py", [f"-file={output3}"] + limit_args):
        sys.exit(1)
    
    print("🎉 Support analysis pipeline completed successfully!")
    logging.info("Support analysis pipeline completed successfully")

if __name__ == "__main__":
    main()
