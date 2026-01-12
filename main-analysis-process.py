#!/usr/bin/env python3
"""
WordPress.com Support Interaction Analysis - Main Processing Engine
by @wiesenhauss

This script is the core analysis engine that processes CSAT survey data and support ticket 
interactions to generate detailed analytical reports using AI. It performs comprehensive 
analysis of customer support interactions across three scenarios: good CSAT ratings, 
bad CSAT ratings, and missing CSAT data.

Features:
- AI-powered analysis using OpenAI GPT models (gpt-4.1-mini)
- Support for local AI servers as alternative to OpenAI API
- Batch processing with progress tracking and rate limit management
- Comprehensive error handling with retry logic
- Automatic progress saving during processing
- Handles file paths with spaces and special characters

Analysis Output (for each ticket):
- Detailed summary of the customer interaction
- Customer's primary goal or objective
- Overall sentiment analysis (Positive/Neutral/Negative)
- Analysis of what happened during the interaction
- Issue resolution status (TRUE/FALSE)
- Main interaction topics categorization
- Product feedback extraction with quotes
- Classification: product-related vs service-related issues
- AI feedback detection (TRUE/FALSE)
- Main topic categorization (from predefined list)

Usage:
  python main-analysis-process.py -file="path/to/input.csv" [--local]
  python main-analysis-process.py  # Interactive mode

Arguments:
  -file, --input-file    Path to the input CSV file containing support data
  --local               Use local AI server (localhost:1234) instead of OpenAI API

Required CSV Columns:
  - CSAT Rating, CSAT Reason, CSAT Comment
  - Interaction Message Body

Environment Variables:
  OPENAI_API_KEY  Required unless using --local flag

Output:
  Creates a timestamped CSV file with analysis results:
  support-analysis-output_v12-YYYY-MM-DD_HHhMM.csv
"""

import pandas as pd
import openai
import time
from typing import Optional
import datetime
import os
import argparse
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import gc
import json

# Import shared utilities
from utils import (
    normalize_file_path,
    find_column_by_substring,
    get_openai_client,
)

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm is not available
    def tqdm(iterable, *args, **kwargs):
        return iterable

# JSON Schema for Structured Outputs - ensures reliable, type-safe API responses
ANALYSIS_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "support_analysis",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "detail_summary": {
                    "type": "string",
                    "description": "Short summary of the interaction (if multiple issues, separate by issue)"
                },
                "customer_goal": {
                    "type": "string",
                    "description": "Customer's main goal in concise format using an action verb (e.g., 'Import subscribers to WordPress.com')"
                },
                "sentiment_analysis": {
                    "type": "string",
                    "enum": ["Positive", "Neutral", "Negative"],
                    "description": "Overall sentiment of the customer during the support interaction"
                },
                "what_happened": {
                    "type": "string",
                    "description": "Comprehensive hypothesis explaining the user's rating or experience"
                },
                "issue_resolved": {
                    "type": "boolean",
                    "description": "Whether the issue was resolved based on interaction content"
                },
                "interaction_topics": {
                    "type": "string",
                    "description": "Main topics discussed, as comma-separated list of concise, specific categories"
                },
                "product_feedback": {
                    "type": "string",
                    "description": "Product feedback summary with customer quotes, or 'NONE' if no feedback present"
                },
                "related_to_product": {
                    "type": "boolean",
                    "description": "Whether sentiment relates to product issues (functionality, usability, features)"
                },
                "related_to_service": {
                    "type": "boolean",
                    "description": "Whether sentiment relates to support service issues (agent interaction, response time)"
                },
                "ai_feedback": {
                    "type": "boolean",
                    "description": "Whether customer explicitly provided feedback about AI support assistant"
                },
                "main_topic": {
                    "type": "string",
                    "description": "One or more topics from predefined list, comma-separated"
                },
                "product_area": {
                    "type": "string",
                    "enum": ["Domains", "Email", "Themes", "Plugins", "Billing", "Plans", "Editor", "Media", "SEO", "Security", "Performance", "Migration", "Support", "Account", "AI Features", "Mobile", "Other"],
                    "description": "Primary product area this ticket relates to"
                },
                "feature_requests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of specific feature requests mentioned by the customer, empty array if none"
                },
                "pain_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of specific pain points or frustrations expressed by the customer, empty array if none"
                }
            },
            "required": [
                "detail_summary",
                "customer_goal", 
                "sentiment_analysis",
                "what_happened",
                "issue_resolved",
                "interaction_topics",
                "product_feedback",
                "related_to_product",
                "related_to_service",
                "ai_feedback",
                "main_topic",
                "product_area",
                "feature_requests",
                "pain_points"
            ],
            "additionalProperties": False
        }
    }
}

# Mapping from JSON response keys to CSV column names
RESPONSE_TO_COLUMN_MAP = {
    "detail_summary": "DETAIL_SUMMARY",
    "customer_goal": "CUSTOMER_GOAL",
    "sentiment_analysis": "SENTIMENT_ANALYSIS",
    "what_happened": "WHAT_HAPPENED",
    "issue_resolved": "ISSUE_RESOLVED",
    "interaction_topics": "INTERACTION_TOPICS",
    "product_feedback": "PRODUCT_FEEDBACK",
    "related_to_product": "RELATED_TO_PRODUCT",
    "related_to_service": "RELATED_TO_SERVICE",
    "ai_feedback": "AI_FEEDBACK",
    "main_topic": "MAIN_TOPIC",
    "product_area": "PRODUCT_AREA",
    "feature_requests": "FEATURE_REQUESTS",
    "pain_points": "PAIN_POINTS"
}

@dataclass
class TicketTask:
    """Data class for ticket processing tasks"""
    index: int
    row: pd.Series
    
@dataclass
class ProcessingResult:
    """Data class for processing results"""
    index: int
    success: bool
    report: Optional[dict]
    error: Optional[str] = None

class ThreadSafeProgressTracker:
    """Thread-safe progress tracking for concurrent processing"""
    def __init__(self, total_items: int):
        self.total_items = total_items
        self.processed = 0
        self.skipped = 0
        self.errors = 0
        self.lock = threading.Lock()
        self.start_time = datetime.datetime.now()
        
    def update(self, processed: int = 0, skipped: int = 0, errors: int = 0):
        """Thread-safe update of counters"""
        with self.lock:
            self.processed += processed
            self.skipped += skipped
            self.errors += errors
            
    def get_stats(self):
        """Get current statistics"""
        with self.lock:
            elapsed = datetime.datetime.now() - self.start_time
            completed = self.processed + self.skipped + self.errors
            remaining = max(0, self.total_items - completed)
            
            if completed > 0:
                rate = completed / elapsed.total_seconds()
                remaining_time = remaining / rate if rate > 0 else 0
            else:
                rate = 0
                remaining_time = 0
                
            return {
                'processed': self.processed,
                'skipped': self.skipped,
                'errors': self.errors,
                'completed': completed,
                'remaining': remaining,
                'elapsed': elapsed,
                'rate': rate,
                'remaining_time': datetime.timedelta(seconds=remaining_time)
            }
from datetime import timedelta
try:
    from dotenv import load_dotenv
except ImportError:
    # Fallback if python-dotenv is not available
    def load_dotenv():
        pass

# normalize_file_path and find_column_by_substring are now imported from utils

def read_csv_file(file_path: str) -> pd.DataFrame:
	"""Read the CSV file into a pandas DataFrame and ensure required columns exist."""
	try:
		df = pd.read_csv(file_path)
		
		# Define essential columns that must exist
		# Check for either old or new header name for message body using fuzzy matching
		message_body_column = find_column_by_substring(df, 'Interaction Message Body')
		if not message_body_column:
			message_body_column = find_column_by_substring(df, 'Ticket Message Body')
		
		if not message_body_column:
			raise Exception("Could not find message body column. Looking for 'Interaction Message Body' or 'Ticket Message Body'")
		
		# Check for Created Date column
		created_date_column = find_column_by_substring(df, 'Created Date')
		if not created_date_column:
			raise Exception("Could not find 'Created Date' column")
		
		# Store the actual column names for later use
		df.attrs['message_body_column'] = message_body_column
		df.attrs['created_date_column'] = created_date_column
		
		# Define expected columns that should exist for optimal analysis
		expected_columns = {
			'CSAT Rating': find_column_by_substring(df, 'CSAT Rating'),
			'CSAT Reason': find_column_by_substring(df, 'CSAT Reason'),
			'CSAT Comment': find_column_by_substring(df, 'CSAT Comment'),
			'Tags': find_column_by_substring(df, 'Tags')  # Used to skip auto-merged tickets
		}
		
		# Create missing columns with null values
		created_columns = []
		for expected_name, actual_column in expected_columns.items():
			if actual_column is None:
				df[expected_name] = None
				created_columns.append(expected_name)
			else:
				# Store mapping if column name doesn't match exactly
				if actual_column != expected_name:
					df.attrs[f'{expected_name}_column'] = actual_column
		
		# Inform user about created columns
		if created_columns:
			print(f"Info: Created missing columns with null values: {', '.join(created_columns)}")
			print("Analysis will continue with available data.")
		
		return df
		
	except Exception as e:
		raise Exception(f"Error reading CSV file: {str(e)}")
		
## Note: clean_sentiment_analysis, clean_issue_resolved, and clean_boolean_response
# functions have been removed. The JSON schema now enforces correct types and values
# directly from the API response, eliminating the need for post-processing cleanup.

def create_analysis_prompt(row: dict, df_attrs: dict = None) -> str:
	"""Create the prompt for OpenAI API using the row data based on CSAT rating."""
	# Handle missing values gracefully
	# Use stored column mappings if available
	if df_attrs:
		csat_rating_col = df_attrs.get('CSAT Rating_column', 'CSAT Rating')
		csat_reason_col = df_attrs.get('CSAT Reason_column', 'CSAT Reason')
		csat_comment_col = df_attrs.get('CSAT Comment_column', 'CSAT Comment')
		message_body_col = df_attrs.get('message_body_column', 'Interaction Message Body')
	else:
		csat_rating_col = 'CSAT Rating'
		csat_reason_col = 'CSAT Reason'
		csat_comment_col = 'CSAT Comment'
		message_body_col = 'Interaction Message Body'
	
	# Check if row is dict or Series
	is_dict = isinstance(row, dict)
	
	csat_rating = row.get(csat_rating_col, "Not provided") if is_dict else (row[csat_rating_col] if csat_rating_col in row.index and pd.notna(row[csat_rating_col]) else "Not provided")
	csat_reason = row.get(csat_reason_col, "Not provided") if is_dict else (row[csat_reason_col] if csat_reason_col in row.index and pd.notna(row[csat_reason_col]) else "Not provided")
	csat_comment = row.get(csat_comment_col, "Not provided") if is_dict else (row[csat_comment_col] if csat_comment_col in row.index and pd.notna(row[csat_comment_col]) else "Not provided")
	ticket_body = row.get(message_body_col, "Not provided") if is_dict else (row[message_body_col] if message_body_col in row.index and pd.notna(row[message_body_col]) else "Not provided")
	
	# Handle NaN values
	if pd.isna(csat_rating):
		csat_rating = "Not provided"
	if pd.isna(csat_reason):
		csat_reason = "Not provided"
	if pd.isna(csat_comment):
		csat_comment = "Not provided"
	if pd.isna(ticket_body):
		ticket_body = "Not provided"
	
	context = f"""
CSAT Rating: {csat_rating}
CSAT Reason: {csat_reason}
CSAT Comment: {csat_comment}
Interaction Message Body: {ticket_body}
"""

	# Define the different prompts based on CSAT rating
	# Note: Output format is controlled by JSON schema, not prompt instructions
	csat_bad = """You are an AI customer support supervisor for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others). Your goal is to analyze support emails from users that gave us a bad CSAT and understand what motivated them to do so.

Read the entire context, think carefully about the support interaction between the customer and the Happiness Engineer (support agent) and the comment the user left on the CSAT survey, then generate a detailed analysis.

**Guidelines:**
- Your goal is to create an internal report, not provide technical support.
- The report must be in English.
- If you can't create a comprehensive analysis due to lack of context, indicate this in the detail_summary field.

**Analysis criteria:**
- detail_summary: Short summary of the interaction (separate by issue if multiple)
- customer_goal: Customer's main goal using an action verb, concise format (e.g., "Import subscribers to WordPress.com")
- sentiment_analysis: Overall sentiment during the interaction - must be "Positive", "Neutral", or "Negative"
- what_happened: Comprehensive hypothesis explaining the user's bad rating, considering context and external influences
- issue_resolved: Whether the issue was resolved based on CSAT comment and interaction content
- interaction_topics: Main topics as comma-separated list of concise, specific categories
- product_feedback: Feedback summary with customer quotes (format: "Summary - 'quote'"), or "NONE" if no feedback
- related_to_product: True if negative sentiment comes from product issues (functionality, usability, complexity, feature limitations)
- related_to_service: True if negative sentiment comes from support service issues (agent interaction, response times, communication quality)
- ai_feedback: True ONLY if customer explicitly provided feedback about AI support assistant (not just mentions of AI)
- main_topic: Select from: Account, Creating & editing the site, Domains, Downtime, Email issues, Error on their site, General billing, General plan questions, Hosting, Integrations, Jetpack issues, Monetization, Plan Cancelation/refund request, Plan Downgrade request, Plan Upgrade request, Plugin support, Presales opportunity, Site performance issues, Theme support, User wanted to speak with an agent/human, WooCommerce-related, SEO, Security, Other
"""

	csat_good = """You are an AI customer support supervisor for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others). Your goal is to analyze support emails from users that gave us a good CSAT and understand what made their experience positive.

Read the entire context, think carefully about the support interaction between the customer and the Happiness Engineer (support agent) and the comment the user left on the CSAT survey, then generate a detailed analysis.

**Guidelines:**
- Your goal is to create an internal report, not provide technical support.
- The report must be in English.
- If you can't create a comprehensive analysis due to lack of context, indicate this in the detail_summary field.

**Analysis criteria:**
- detail_summary: Short summary of the interaction (separate by issue if multiple)
- customer_goal: Customer's main goal using an action verb, concise format (e.g., "Import subscribers to WordPress.com")
- sentiment_analysis: Overall sentiment during the interaction - must be "Positive", "Neutral", or "Negative"
- what_happened: Comprehensive hypothesis explaining the user's good rating, considering context and external influences
- issue_resolved: Whether the issue was resolved based on CSAT comment and interaction content
- interaction_topics: Main topics as comma-separated list of concise, specific categories
- product_feedback: Feedback summary with customer quotes (format: "Summary - 'quote'"), or "NONE" if no feedback
- related_to_product: True if positive sentiment comes from product satisfaction (features, functionality, usability)
- related_to_service: True if positive sentiment comes from support service satisfaction (agent interaction, response time)
- ai_feedback: True ONLY if customer explicitly provided feedback about AI support assistant (not just mentions of AI)
- main_topic: Select from: Account, Creating & editing the site, Domains, Downtime, Email issues, Error on their site, General billing, General plan questions, Hosting, Integrations, Jetpack issues, Monetization, Plan Cancelation/refund request, Plan Downgrade request, Plan Upgrade request, Plugin support, Presales opportunity, Site performance issues, Theme support, User wanted to speak with an agent/human, WooCommerce-related, SEO, Security, Other
"""

	csat_missing = """You are an AI customer support supervisor for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others). Your goal is to analyze support emails and understand the nature of the interaction when no CSAT rating was provided.

Read the entire context, think carefully about the support interaction between the customer and the Happiness Engineer (support agent), then generate a detailed analysis.

**Guidelines:**
- Your goal is to create an internal report, not provide technical support.
- The report must be in English.
- If you can't create a comprehensive analysis due to lack of context, indicate this in the detail_summary field.

**Analysis criteria:**
- detail_summary: Short summary of the interaction (separate by issue if multiple)
- customer_goal: Customer's main goal using an action verb, concise format (e.g., "Import subscribers to WordPress.com")
- sentiment_analysis: Overall sentiment during the interaction - must be "Positive", "Neutral", or "Negative"
- what_happened: Analyze the interaction and identify potential issues or positive aspects of the support experience
- issue_resolved: Whether the issue was resolved based on interaction content
- interaction_topics: Main topics as comma-separated list of concise, specific categories
- product_feedback: Feedback summary with customer quotes (format: "Summary - 'quote'"), or "NONE" if no feedback
- related_to_product: True if there were product-related issues (functionality, usability, complexity, feature limitations)
- related_to_service: True if there were support service-related issues (agent interaction, response times, communication quality)
- ai_feedback: True ONLY if customer explicitly provided feedback about AI support assistant (not just mentions of AI)
- main_topic: Select from: Account, Creating & editing the site, Domains, Downtime, Email issues, Error on their site, General billing, General plan questions, Hosting, Integrations, Jetpack issues, Monetization, Plan Cancelation/refund request, Plan Downgrade request, Plan Upgrade request, Plugin support, Presales opportunity, Site performance issues, Theme support, User wanted to speak with an agent/human, WooCommerce-related, SEO, Security, Other
"""

	# Select the appropriate prompt based on CSAT rating
	# Handle cases where CSAT Rating might be null/missing
	# Use the csat_rating_col we already determined above
	csat_rating_value = row.get(csat_rating_col) if is_dict else (row[csat_rating_col] if csat_rating_col in row.index else None)
	
	if csat_rating_value and pd.notna(csat_rating_value):
		csat_rating_str = str(csat_rating_value).lower().strip()
		if csat_rating_str == 'bad':
			prompt = csat_bad
		elif csat_rating_str == 'good':
			prompt = csat_good
		else:  # Any other value
			prompt = csat_missing
	else:
		# If CSAT Rating is null/missing, use the missing prompt
		prompt = csat_missing
	
	return context + "\n\n" + prompt
	

class RateLimiter:
    """Thread-safe rate limiter for API calls"""
    def __init__(self, max_requests_per_second: float = 10.0):
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()
        
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits"""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
                
            self.last_request_time = time.time()

def process_single_ticket(task: TicketTask, api_key: str, use_local: bool, rate_limiter: RateLimiter, df_attrs: dict = None) -> ProcessingResult:
    """Process a single ticket with error handling and rate limiting"""
    try:
        # Get the row data - task.row is now a dict
        row = task.row
        
        # Check if should skip - use stored column mapping if available
        tags_col = df_attrs.get('Tags_column', 'Tags') if df_attrs else 'Tags'
        if tags_col in row and isinstance(row[tags_col], str) and 'closed_by_automerge' in row[tags_col]:
            return ProcessingResult(
                index=task.index,
                success=True,
                report={
                    'DETAIL_SUMMARY': "Skipped - closed by automerge",
                    'CUSTOMER_GOAL': "Skipped - closed by automerge",
                    'SENTIMENT_ANALYSIS': "Neutral",  # Use valid enum value
                    'WHAT_HAPPENED': "Skipped - closed by automerge",
                    'ISSUE_RESOLVED': False,  # Native boolean
                    'INTERACTION_TOPICS': "Skipped - closed by automerge",
                    'PRODUCT_FEEDBACK': "NONE",
                    'RELATED_TO_PRODUCT': False,  # Native boolean
                    'RELATED_TO_SERVICE': False,  # Native boolean
                    'AI_FEEDBACK': False,  # Native boolean
                    'MAIN_TOPIC': "Other",
                    'PRODUCT_AREA': "Other",
                    'FEATURE_REQUESTS': "[]",
                    'PAIN_POINTS': "[]"
                }
            )
        
        # Rate limiting
        rate_limiter.wait_if_needed()
        
        # Create prompt and get response
        prompt = create_analysis_prompt(row, df_attrs)
        report = get_openai_response(prompt, api_key, use_local=use_local)
        
        if report:
            return ProcessingResult(index=task.index, success=True, report=report)
        else:
            return ProcessingResult(
                index=task.index, 
                success=False, 
                report=None, 
                error="Failed to get valid API response"
            )
            
    except Exception as e:
        return ProcessingResult(
            index=task.index, 
            success=False, 
            report=None, 
            error=str(e)
        )

def get_openai_response(prompt: str, api_key: str, max_retries: int = 3, use_local: bool = False) -> Optional[dict]:
	"""Get structured JSON response from OpenAI API with retry logic.
	
	Uses OpenAI's Structured Outputs feature to guarantee response format compliance.
	This eliminates parsing errors and ensures type-safe responses.
	"""
	# Use shared OpenAI client for connection reuse
	client = get_openai_client(api_key=api_key, use_local=use_local)
	
	for attempt in range(max_retries):
		try:
			# Use structured outputs for guaranteed JSON schema compliance
			response = client.chat.completions.create(
				model="gpt-4.1-mini",
				messages=[
					{"role": "system", "content": "You are a customer support supervisor analyzing support interactions. Provide detailed, accurate analysis based on the interaction content."},
					{"role": "user", "content": prompt}
				],
				response_format=ANALYSIS_RESPONSE_SCHEMA,
				temperature=0.7,
				max_tokens=1500,
				timeout=60  # Increased timeout for structured output processing
			)
			
			content = response.choices[0].message.content
			
			# Parse the JSON response
			try:
				json_result = json.loads(content)
			except json.JSONDecodeError as e:
				print(f"\nJSON parsing error on attempt {attempt + 1}: {str(e)}")
				print(f"Raw content: {content[:500]}...")
				if attempt < max_retries - 1:
					time.sleep(2 ** attempt)
					continue
				return None
			
			# Map JSON keys to CSV column names
			result = {}
			for json_key, csv_column in RESPONSE_TO_COLUMN_MAP.items():
				if json_key in json_result:
					value = json_result[json_key]
					# Convert arrays to JSON strings for CSV storage
					if isinstance(value, list):
						result[csv_column] = json.dumps(value)
					else:
						result[csv_column] = value
				else:
					print(f"Warning: Missing key '{json_key}' in response")
					# Use appropriate default based on expected type
					if json_key in ['feature_requests', 'pain_points']:
						result[csv_column] = "[]"  # Empty JSON array
					else:
						result[csv_column] = "Analysis incomplete"
			
			# Debug: Print structured response summary
			print(f"\n✓ Structured response received:")
			print(f"  Sentiment: {result.get('SENTIMENT_ANALYSIS', 'N/A')}")
			print(f"  Resolved: {result.get('ISSUE_RESOLVED', 'N/A')}")
			print(f"  Topic: {result.get('MAIN_TOPIC', 'N/A')[:50]}...")
			print("=" * 50)
			
			return result
			
		except openai.RateLimitError as e:
			print(f"\nRate limit hit on attempt {attempt + 1}: {str(e)}")
			if attempt < max_retries - 1:
				wait_time = min(60, 2 ** attempt * 5)  # Cap at 60 seconds
				print(f"Waiting {wait_time} seconds before retry...")
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

def process_csv(input_file: str, output_file: str, api_key: str, batch_size: int = 25, use_local: bool = False, max_workers: int = 5) -> None:
	"""Process the CSV file using concurrent threads for improved performance."""
	try:
		# Read CSV (input file)
		df = read_csv_file(input_file)
		total_rows = len(df)
		
		print(f"🚀 Starting concurrent processing with {max_workers} threads")
		print(f"📊 Processing {total_rows:,} tickets...")
		
		# Initialize report columns
		df['DETAIL_SUMMARY'] = None
		df['CUSTOMER_GOAL'] = None
		df['SENTIMENT_ANALYSIS'] = None
		df['WHAT_HAPPENED'] = None
		df['ISSUE_RESOLVED'] = None
		df['INTERACTION_TOPICS'] = None
		df['PRODUCT_FEEDBACK'] = None
		df['RELATED_TO_PRODUCT'] = None
		df['RELATED_TO_SERVICE'] = None
		df['AI_FEEDBACK'] = None
		df['PRODUCT_AREA'] = None
		df['FEATURE_REQUESTS'] = None
		df['PAIN_POINTS'] = None
		df['MAIN_TOPIC'] = None
		
		# Initialize progress tracker and rate limiter
		progress_tracker = ThreadSafeProgressTracker(total_rows)
		
		# Set rate limit based on API type and thread count
		# With 50 threads, allow high throughput - retry logic handles rate limits
		if use_local:
			rate_limit = 200.0  # Local server can handle more requests
		else:
			rate_limit = 100.0  # Higher rate for OpenAI API with 50 threads
		
		rate_limiter = RateLimiter(rate_limit)
		
		# Create progress bar
		pbar = tqdm(total=total_rows, desc="Processing tickets", 
				   bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} tickets '
				   '[{elapsed}<{remaining}, {rate_fmt}{postfix}]')
		
		# Create tasks for all tickets - copy row data as a dict to avoid threading issues
		# This prevents race conditions with concurrent DataFrame access
		# Use loc for better performance with large DataFrames
		tasks = []
		for idx in df.index:
			row_dict = df.loc[idx].to_dict()
			tasks.append(TicketTask(index=idx, row=row_dict))
		
		# Free up memory by clearing DataFrame reference if not needed
		# Note: We keep df for updates, but tasks now have independent copies
		
		# Process results storage
		results_lock = threading.Lock()
		save_counter = 0
		
		def update_dataframe_with_result(result: ProcessingResult):
			"""Thread-safe function to update DataFrame with result"""
			nonlocal save_counter
			
			with results_lock:
				if result.success and result.report:
					# Check if this was a skipped ticket
					if result.report.get('DETAIL_SUMMARY') == "Skipped - closed by automerge":
						progress_tracker.update(skipped=1)
					else:
						progress_tracker.update(processed=1)
						
					# Update DataFrame
					for key, value in result.report.items():
						df.at[result.index, key] = value
				else:
					# Handle errors with appropriate default values for each field type
					progress_tracker.update(errors=1)
					error_msg = f"Error: {result.error}" if result.error else "Error generating report"
					
					# Set error message for string fields
					for col in ['DETAIL_SUMMARY', 'CUSTOMER_GOAL', 'WHAT_HAPPENED', 
							   'INTERACTION_TOPICS', 'PRODUCT_FEEDBACK', 'MAIN_TOPIC']:
						df.at[result.index, col] = error_msg
					
					# Set appropriate defaults for typed fields
					df.at[result.index, 'SENTIMENT_ANALYSIS'] = "Neutral"  # Valid enum value
					df.at[result.index, 'ISSUE_RESOLVED'] = False
					df.at[result.index, 'RELATED_TO_PRODUCT'] = False
					df.at[result.index, 'RELATED_TO_SERVICE'] = False
					df.at[result.index, 'AI_FEEDBACK'] = False
				
				# Update progress bar
				stats = progress_tracker.get_stats()
				pbar.update(1)
				pbar.set_postfix({
					'Processed': stats['processed'],
					'Skipped': stats['skipped'], 
					'Errors': stats['errors'],
					'Rate': f"{stats['rate']:.1f}/s",
					'Remaining': str(stats['remaining_time']).split('.')[0]
				})
				
				# Save progress every 50 completions
				save_counter += 1
				if save_counter >= 50:
					df.to_csv(output_file, index=False)
					save_counter = 0
					# Force garbage collection to free memory
					gc.collect()
		
		# Process tickets concurrently
		# Get df attributes for column mapping
		df_attrs = df.attrs if hasattr(df, 'attrs') else {}
		
		with ThreadPoolExecutor(max_workers=max_workers) as executor:
			# Submit all tasks - row data is now copied in the task itself
			future_to_task = {
				executor.submit(process_single_ticket, task, api_key, use_local, rate_limiter, df_attrs): task 
				for task in tasks
			}
			
			# Process completed tasks as they finish
			for future in as_completed(future_to_task):
				task = future_to_task[future]
				try:
					result = future.result()
					update_dataframe_with_result(result)
				except Exception as e:
					# Handle unexpected errors
					error_result = ProcessingResult(
						index=task.index,
						success=False,
						report=None,
						error=f"Unexpected error: {str(e)}"
					)
					update_dataframe_with_result(error_result)
		
		# Final save
		df.to_csv(output_file, index=False)
		pbar.close()
		
		# Clean up memory by removing references
		del tasks
		del future_to_task
		gc.collect()
		
		# Final statistics
		final_stats = progress_tracker.get_stats()
		print(f"\n✅ Concurrent processing completed!")
		print(f"📊 Tickets processed: {final_stats['processed']:,}")
		print(f"⏭️  Tickets skipped: {final_stats['skipped']:,}")
		print(f"❌ Errors encountered: {final_stats['errors']:,}")
		print(f"⏱️  Total time: {str(final_stats['elapsed']).split('.')[0]}")
		print(f"🚀 Average speed: {final_stats['rate']:.2f} tickets/second")
		print(f"🎯 Effective throughput: {final_stats['processed'] / final_stats['elapsed'].total_seconds():.2f} successful analyses/second")
		print(f"💾 Output saved to: {output_file}")
		
	except Exception as e:
		print(f"❌ Error in concurrent processing: {str(e)}")
		# Save progress even if there's an error
		df.to_csv(output_file, index=False)
		raise

def main():
	# Load environment variables from .env file
	load_dotenv()
	
	# Get current date and time for the filename
	current_time = datetime.datetime.now().strftime("%Y-%m-%d_%Hh%M")
	
	# Set up argument parser
	parser = argparse.ArgumentParser(description='Process CSAT survey data and support ticket interactions.')
	parser.add_argument('-file', '--input-file', type=str, help='Path to the input CSV file')
	parser.add_argument('--local', action='store_true', help='Use local AI server instead of OpenAI API')
	parser.add_argument('--threads', type=int, default=50, help='Number of concurrent processing threads (default: 50)')
	args = parser.parse_args()
	
	# Get input file path from command line argument or user input
	INPUT_FILE = args.input_file
	if not INPUT_FILE:
		INPUT_FILE = input("Enter the full path to the CSV file to process: ")
	
	# Normalize the file path to handle spaces and special characters
	INPUT_FILE = normalize_file_path(INPUT_FILE)
	
	# Get the directory from the input file for the output file
	file_dir = os.path.dirname(INPUT_FILE)
	file_name = os.path.basename(INPUT_FILE)
	
	# Configuration
	# Ensure output file is in the same directory as the input file
	OUTPUT_FILE = os.path.join(file_dir, f"support-analysis-output_v12-{current_time}.csv")
	API_KEY = os.getenv('OPENAI_API_KEY')  # Get API key from environment variable
	
	# Validate input file exists
	if not os.path.exists(INPUT_FILE):
		raise FileNotFoundError(f"Input file not found at: {INPUT_FILE}")
	
	# Validate API key exists if not using local server
	if not args.local and not API_KEY:
		raise ValueError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")
		
	BATCH_SIZE = 25  # Increased batch size for better performance
	MAX_WORKERS = args.threads
	
	# Print which AI service is being used
	if args.local:
		print(f"Using local AI server at http://localhost:1234/v1 with {MAX_WORKERS} threads")
	else:
		print(f"Using OpenAI API with {MAX_WORKERS} concurrent threads")
	
	process_csv(INPUT_FILE, OUTPUT_FILE, API_KEY, BATCH_SIZE, use_local=args.local, max_workers=MAX_WORKERS)
	
if __name__ == "__main__":
	main()