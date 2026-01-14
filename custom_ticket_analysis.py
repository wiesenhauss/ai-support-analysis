#!/usr/bin/env python3
"""
AI Support Analyzer - Custom Per-Ticket Analysis Module
by @wiesenhauss

This module provides custom per-ticket analysis capabilities, allowing users to:
- Define multiple custom AI analyses with custom prompts
- Process each ticket with custom prompts concurrently
- Add results as new columns to the output CSV
- Support both string and boolean result types

Features:
- Concurrent processing with configurable thread count
- OpenAI structured outputs for reliable parsing
- Rate limiting and retry logic
- Progress saving during processing

Usage:
  python custom_ticket_analysis.py -file="path/to/data.csv" -config="path/to/config.json"
  
Arguments:
  -file     Path to CSV file containing the data to analyze
  -config   Path to JSON file with custom analysis configurations

Config JSON format:
  {
    "analyses": [
      {
        "name": "IS_REFUND_REQUEST",
        "prompt": "Determine if this ticket is a refund request",
        "result_type": "boolean",
        "description": "Identifies refund requests",
        "columns": ["Interaction Message Body", "CSAT Comment"]
      },
      {
        "name": "CUSTOMER_MOOD",
        "prompt": "Describe the customer's emotional state in one word",
        "result_type": "string",
        "description": "Captures customer mood",
        "columns": ["Interaction Message Body", "CSAT Rating"]
      }
    ]
  }

  Note: The "columns" field is optional. If not specified, default columns
  (Message Body, CSAT Rating, CSAT Comment) will be used.

Environment Variables:
  OPENAI_API_KEY  Required for AI-powered analysis

Output:
  Creates an enriched CSV file with new CUSTOM_* columns:
  custom-ticket-analysis-output_YYYY-MM-DD_HHhMM.csv
"""

import pandas as pd
import openai
import time
from typing import Optional, List, Dict, Any
import datetime
import os
import argparse
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import gc

# Import shared utilities
from utils import (
    normalize_file_path,
    find_column_by_substring,
    get_openai_client,
)

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        pass


@dataclass
class CustomAnalysisConfig:
    """Configuration for a single custom analysis."""
    name: str
    prompt: str
    result_type: str  # "string" or "boolean"
    description: str = ""
    columns: List[str] = field(default_factory=list)  # Columns to include in analysis context
    
    @property
    def column_name(self) -> str:
        """Get the output column name with CUSTOM_ prefix."""
        # Clean the name to be a valid column name
        clean_name = self.name.upper().replace(" ", "_").replace("-", "_")
        return f"CUSTOM_{clean_name}"
    
    def get_json_schema(self) -> dict:
        """Generate JSON schema for this analysis based on result type."""
        if self.result_type == "boolean":
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": f"custom_analysis_{self.name.lower()}",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "result": {
                                "type": "boolean",
                                "description": f"Boolean result for: {self.prompt}"
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Brief explanation for the result"
                            }
                        },
                        "required": ["result", "reasoning"],
                        "additionalProperties": False
                    }
                }
            }
        else:  # string type
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": f"custom_analysis_{self.name.lower()}",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "result": {
                                "type": "string",
                                "description": f"String result for: {self.prompt}"
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Brief explanation for the result"
                            }
                        },
                        "required": ["result", "reasoning"],
                        "additionalProperties": False
                    }
                }
            }


@dataclass
class TicketTask:
    """Data class for ticket processing tasks."""
    index: int
    row: dict
    analyses: List[CustomAnalysisConfig]


@dataclass
class ProcessingResult:
    """Data class for processing results."""
    index: int
    success: bool
    results: Optional[Dict[str, Any]]  # column_name -> value
    error: Optional[str] = None


class ThreadSafeProgressTracker:
    """Thread-safe progress tracking for concurrent processing."""
    def __init__(self, total_items: int):
        self.total_items = total_items
        self.processed = 0
        self.errors = 0
        self.lock = threading.Lock()
        self.start_time = datetime.datetime.now()
        
    def update(self, processed: int = 0, errors: int = 0):
        """Thread-safe update of counters."""
        with self.lock:
            self.processed += processed
            self.errors += errors
            
    def get_stats(self):
        """Get current statistics."""
        with self.lock:
            elapsed = datetime.datetime.now() - self.start_time
            completed = self.processed + self.errors
            remaining = max(0, self.total_items - completed)
            
            if completed > 0:
                rate = completed / elapsed.total_seconds()
                remaining_time = remaining / rate if rate > 0 else 0
            else:
                rate = 0
                remaining_time = 0
                
            return {
                'processed': self.processed,
                'errors': self.errors,
                'completed': completed,
                'remaining': remaining,
                'elapsed': elapsed,
                'rate': rate,
                'remaining_time': datetime.timedelta(seconds=remaining_time)
            }


class RateLimiter:
    """Thread-safe rate limiter for API calls."""
    def __init__(self, max_requests_per_second: float = 10.0):
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()
        
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
                
            self.last_request_time = time.time()


def read_csv_file(file_path: str) -> pd.DataFrame:
    """Read the CSV file into a pandas DataFrame."""
    try:
        df = pd.read_csv(file_path)
        
        # Check for message body column
        message_body_column = find_column_by_substring(df, 'Interaction Message Body')
        if not message_body_column:
            message_body_column = find_column_by_substring(df, 'Ticket Message Body')
        
        if message_body_column:
            df.attrs['message_body_column'] = message_body_column
        
        return df
        
    except Exception as e:
        raise Exception(f"Error reading CSV file: {str(e)}")


def create_custom_prompt(row: dict, analysis: CustomAnalysisConfig, df_attrs: dict = None) -> str:
    """Create the prompt for a custom analysis using selected columns."""
    # Build context from selected columns
    context_parts = []
    
    if analysis.columns:
        # Use user-selected columns
        for col in analysis.columns:
            value = row.get(col, "")
            if value and not pd.isna(value):
                # Format the value with column name as label
                context_parts.append(f"{col}:\n{value}")
    else:
        # Fallback to default columns if none selected (backwards compatibility)
        message_body_col = df_attrs.get('message_body_column', 'Interaction Message Body') if df_attrs else 'Interaction Message Body'
        
        ticket_body = row.get(message_body_col, "")
        if ticket_body and not pd.isna(ticket_body):
            context_parts.append(f"Ticket Content:\n{ticket_body}")
        
        csat_rating = row.get('CSAT Rating', row.get('csat_rating', ''))
        if csat_rating and not pd.isna(csat_rating):
            context_parts.append(f"CSAT Rating: {csat_rating}")
        
        csat_comment = row.get('CSAT Comment', row.get('csat_comment', ''))
        if csat_comment and not pd.isna(csat_comment):
            context_parts.append(f"CSAT Comment: {csat_comment}")

    context = "\n\n".join(context_parts) if context_parts else "No data available for selected columns."

    # Build the full prompt
    result_instruction = ""
    if analysis.result_type == "boolean":
        result_instruction = "Respond with true or false."
    else:
        result_instruction = "Provide a concise response."

    prompt = f"""You are analyzing a customer support ticket. {result_instruction}

ANALYSIS TASK:
{analysis.prompt}

TICKET DATA:
{context}

Analyze the ticket and provide your response."""

    return prompt


def get_custom_analysis_response(
    prompt: str, 
    analysis: CustomAnalysisConfig,
    api_key: str, 
    max_retries: int = 3,
    use_local: bool = False
) -> Optional[Any]:
    """Get structured response from OpenAI API for a custom analysis."""
    client = get_openai_client(api_key=api_key, use_local=use_local)
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a customer support analyst. Analyze tickets and provide accurate, concise responses."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format=analysis.get_json_schema(),
                temperature=0.3,
                max_tokens=500,
                timeout=60
            )
            
            content = response.choices[0].message.content
            
            try:
                json_result = json.loads(content)
                return json_result.get("result")
            except json.JSONDecodeError as e:
                print(f"\nJSON parsing error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
                
        except openai.RateLimitError as e:
            print(f"\nRate limit hit on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = min(60, 2 ** attempt * 5)
                time.sleep(wait_time)
                continue
            return None
            
        except openai.APITimeoutError as e:
            print(f"\nAPI timeout on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None
            
        except openai.APIError as e:
            print(f"\nAPI error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None
            
        except Exception as e:
            print(f"\nUnexpected error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None
    
    return None


def process_single_ticket(
    task: TicketTask, 
    api_key: str, 
    use_local: bool, 
    rate_limiter: RateLimiter,
    df_attrs: dict = None
) -> ProcessingResult:
    """Process a single ticket with all custom analyses."""
    try:
        results = {}
        
        for analysis in task.analyses:
            # Rate limiting
            rate_limiter.wait_if_needed()
            
            # Create prompt and get response
            prompt = create_custom_prompt(task.row, analysis, df_attrs)
            result = get_custom_analysis_response(prompt, analysis, api_key, use_local=use_local)
            
            if result is not None:
                results[analysis.column_name] = result
            else:
                # Use appropriate default based on type
                if analysis.result_type == "boolean":
                    results[analysis.column_name] = False
                else:
                    results[analysis.column_name] = "Analysis failed"
        
        return ProcessingResult(index=task.index, success=True, results=results)
        
    except Exception as e:
        return ProcessingResult(
            index=task.index, 
            success=False, 
            results=None, 
            error=str(e)
        )


def process_csv(
    input_file: str, 
    output_file: str, 
    analyses: List[CustomAnalysisConfig],
    api_key: str, 
    use_local: bool = False, 
    max_workers: int = 25
) -> None:
    """Process the CSV file with custom analyses using concurrent threads."""
    try:
        df = read_csv_file(input_file)
        total_rows = len(df)
        
        print(f"🚀 Starting custom per-ticket analysis with {max_workers} threads")
        print(f"📊 Processing {total_rows:,} tickets with {len(analyses)} custom analyses...")
        
        # Initialize custom columns
        for analysis in analyses:
            if analysis.result_type == "boolean":
                df[analysis.column_name] = False
            else:
                df[analysis.column_name] = None
        
        # Initialize progress tracker and rate limiter
        progress_tracker = ThreadSafeProgressTracker(total_rows)
        
        # Rate limit based on number of analyses per ticket
        # Each ticket makes len(analyses) API calls
        rate_limit = 50.0 / len(analyses) if analyses else 50.0
        rate_limiter = RateLimiter(rate_limit)
        
        # Create progress bar
        pbar = tqdm(
            total=total_rows, 
            desc="Processing tickets",
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} tickets '
                       '[{elapsed}<{remaining}, {rate_fmt}{postfix}]'
        )
        
        # Create tasks
        tasks = []
        for idx in df.index:
            row_dict = df.loc[idx].to_dict()
            tasks.append(TicketTask(index=idx, row=row_dict, analyses=analyses))
        
        # Process results storage
        results_lock = threading.Lock()
        save_counter = 0
        
        def update_dataframe_with_result(result: ProcessingResult):
            """Thread-safe function to update DataFrame with result."""
            nonlocal save_counter
            
            with results_lock:
                if result.success and result.results:
                    progress_tracker.update(processed=1)
                    
                    # Update DataFrame
                    for column_name, value in result.results.items():
                        df.at[result.index, column_name] = value
                else:
                    progress_tracker.update(errors=1)
                    # Set default values for error cases
                    for analysis in analyses:
                        if analysis.result_type == "boolean":
                            df.at[result.index, analysis.column_name] = False
                        else:
                            df.at[result.index, analysis.column_name] = f"Error: {result.error}" if result.error else "Error"
                
                # Update progress bar
                stats = progress_tracker.get_stats()
                pbar.update(1)
                pbar.set_postfix({
                    'Processed': stats['processed'],
                    'Errors': stats['errors'],
                    'Rate': f"{stats['rate']:.1f}/s",
                    'Remaining': str(stats['remaining_time']).split('.')[0]
                })
                
                # Save progress every 50 completions
                save_counter += 1
                if save_counter >= 50:
                    df.to_csv(output_file, index=False)
                    save_counter = 0
                    gc.collect()
        
        # Get df attributes for column mapping
        df_attrs = df.attrs if hasattr(df, 'attrs') else {}
        
        # Process tickets concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(
                    process_single_ticket, task, api_key, use_local, rate_limiter, df_attrs
                ): task 
                for task in tasks
            }
            
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    update_dataframe_with_result(result)
                except Exception as e:
                    error_result = ProcessingResult(
                        index=task.index,
                        success=False,
                        results=None,
                        error=f"Unexpected error: {str(e)}"
                    )
                    update_dataframe_with_result(error_result)
        
        # Final save
        df.to_csv(output_file, index=False)
        pbar.close()
        
        # Cleanup
        del tasks
        del future_to_task
        gc.collect()
        
        # Final statistics
        final_stats = progress_tracker.get_stats()
        print(f"\n✅ Custom per-ticket analysis completed!")
        print(f"📊 Tickets processed: {final_stats['processed']:,}")
        print(f"❌ Errors encountered: {final_stats['errors']:,}")
        print(f"⏱️  Total time: {str(final_stats['elapsed']).split('.')[0]}")
        print(f"🚀 Average speed: {final_stats['rate']:.2f} tickets/second")
        print(f"💾 Output saved to: {output_file}")
        
        # Print new columns added
        print(f"\n📋 New columns added:")
        for analysis in analyses:
            print(f"   • {analysis.column_name} ({analysis.result_type})")
        
    except Exception as e:
        print(f"❌ Error in custom analysis processing: {str(e)}")
        df.to_csv(output_file, index=False)
        raise


def load_config(config_path: str) -> List[CustomAnalysisConfig]:
    """Load custom analysis configurations from a JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        analyses = []
        for item in config.get('analyses', []):
            analyses.append(CustomAnalysisConfig(
                name=item['name'],
                prompt=item['prompt'],
                result_type=item.get('result_type', 'string'),
                description=item.get('description', ''),
                columns=item.get('columns', [])
            ))

        return analyses
        
    except Exception as e:
        raise Exception(f"Error loading config file: {str(e)}")


def main():
    """Main function to run custom per-ticket analysis."""
    load_dotenv()
    
    # Get current date and time for the filename
    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%Hh%M")
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Run custom per-ticket analysis on CSV data.'
    )
    parser.add_argument('-file', '--input-file', type=str, help='Path to the input CSV file')
    parser.add_argument('-config', '--config-file', type=str, help='Path to JSON config file')
    parser.add_argument('--local', action='store_true', help='Use local AI server instead of OpenAI API')
    parser.add_argument('--threads', type=int, default=25, help='Number of concurrent processing threads (default: 25)')
    args = parser.parse_args()
    
    # Get input file path
    INPUT_FILE = args.input_file
    if not INPUT_FILE:
        INPUT_FILE = input("Enter the full path to the CSV file to process: ")
    
    INPUT_FILE = normalize_file_path(INPUT_FILE)
    
    # Get config file path
    CONFIG_FILE = args.config_file
    if not CONFIG_FILE:
        CONFIG_FILE = input("Enter the full path to the config JSON file: ")
    
    CONFIG_FILE = normalize_file_path(CONFIG_FILE)
    
    # Get directory and setup output file
    file_dir = os.path.dirname(INPUT_FILE)
    OUTPUT_FILE = os.path.join(file_dir, f"custom-ticket-analysis-output_{current_time}.csv")
    
    # Get API key
    API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Validate inputs
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Input file not found at: {INPUT_FILE}")
    
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Config file not found at: {CONFIG_FILE}")
    
    if not args.local and not API_KEY:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")
    
    # Load config
    analyses = load_config(CONFIG_FILE)
    
    if not analyses:
        raise ValueError("No custom analyses configured in the config file.")
    
    print(f"\n📋 Loaded {len(analyses)} custom analyses:")
    for analysis in analyses:
        print(f"   • {analysis.name} ({analysis.result_type}): {analysis.prompt[:50]}...")
    
    # Print which AI service is being used
    if args.local:
        print(f"\nUsing local AI server at http://localhost:1234/v1 with {args.threads} threads")
    else:
        print(f"\nUsing OpenAI API with {args.threads} concurrent threads")
    
    # Run processing
    process_csv(INPUT_FILE, OUTPUT_FILE, analyses, API_KEY, use_local=args.local, max_workers=args.threads)


if __name__ == "__main__":
    main()
