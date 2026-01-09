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
		
def clean_sentiment_analysis(sentiment: str) -> str:
	"""Clean sentiment analysis text to ensure only allowed values are used."""
	# Convert to lowercase and remove leading/trailing whitespace to standardize the input
	sentiment = sentiment.lower().strip()
	
	# Check for keywords in the text and map to one of the three allowed values
	# This handles cases where the LLM includes additional text like 
	# "The overall sentiment was Negative" -> will return "Negative"
	if "negative" in sentiment:
		return "Negative"
	elif "positive" in sentiment:
		return "Positive"
	else:
		# Default to Neutral if no clear positive/negative sentiment is found
		return "Neutral"

def clean_issue_resolved(resolved: str) -> str:
	"""Clean issue resolved text to ensure only TRUE or FALSE values are used."""
	# Convert to lowercase and remove leading/trailing whitespace to standardize the input
	resolved = resolved.lower().strip()
	
	# Check for any variation of "true" in the text
	# This handles cases where the LLM includes additional text like 
	# "The issue was resolved: True" -> will return "TRUE"
	if any(word in resolved for word in ['true', 'yes', 'resolved', 'fixed']):
		return "TRUE"
	else:
		# Default to FALSE for any other response
		return "FALSE"

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
	csat_bad = """You are an AI customer support supervisor for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others) communicating with customers via email. Your goal is to analyze support emails from users that gave us a bad CSAT and understand what motivated them to do so. You'll read the entire context, think carefully about the support interaction between the customer and the Happiness Engineer (support agent) and the comment the user left on the CSAT survey, and then generate a detailed report.
									
**Guidelines for your replies:**
- Remember: your goal here isn't to provide technical support: instead, you are a supervisor that is creating an internal report on the support interaction.
- The report must be in English. Don't use any text formatting.
- If you can't create a comprehensive analysis for the criteria of the report structure due to lack of context, just say "I couldn't analyze this ticket because I don't have all the information I need"
- Please use this structure for your report:

**Report structure:**
- [DETAIL_SUMMARY] Short summary of the interaction (if multiple issues were discussed, separate by issue)
- [CUSTOMER_GOAL] State the customer's main goal in a concise format (e.g., "Import subscribers to WordPress.com" rather than "The customer was trying to import subscribers"). Use an action verb and be specific but brief.
- [SENTIMENT_ANALYSIS] The overall sentiment of the customer during the support interaction. Allowed responses are: "Negative", "Neutral", or "Positive".
- [WHAT_HAPPENED] Develop a comprehensive hypothesis explaining the user's bad rating, considering the entire context and potential external influences.
- [ISSUE_RESOLVED] Issue is resolved? Respond with "TRUE" or "FALSE" based on their CSAT comment and interaction content
- [INTERACTION_TOPICS] List the main topics discussed. Break down the topics into concise and specific categories. Avoid generalizations and ensure topics are clear and actionable. If possible, group related subtopics under broader categories. Final result is a list of one or more topics, separated by commas.
- [PRODUCT_FEEDBACK] If the interaction contains any feedback about the product (feature requests, complaints about functionality, suggestions for improvement, etc.), summarize it concisely and include direct quotes from the customer that provide context for the feedback. Format as: "Feedback summary - 'relevant customer quote'". If no product feedback is present, return "NONE"
- [RELATED_TO_PRODUCT] Return "TRUE" if the negative sentiment comes from product issues (Feedback related to the product's functionality, usability, complexity, or feature limitations, even if the issue was reported during a support interaction. This includes concerns about features not working as expected, difficulties navigating the platform, or frustrations with the product's design or capabilities.), else return "FALSE"
- [RELATED_TO_SERVICE] Return "TRUE" if the negative sentiment comes from support service issues (Feedback related to the interaction with support agents, response times, communication quality, or the overall customer service experience. This includes issues like perceived rudeness, lack of helpfulness, delays, or process dissatisfaction.), else return "FALSE"
- [AI_FEEDBACK] Return "TRUE" only if the customer explicitly provided feedback (positive or negative) about the AI support assistant based on their own words and experience. Look for customer comments expressing opinions about the AI quality, helpfulness, understanding, accuracy, or frustrations with AI responses. DO NOT return TRUE just because "AI" or "AI assistant" appears in the conversation - the mention must indicate the customer's feedback or opinion about it. Return "FALSE" if there is no explicit customer feedback about the AI assistant, even if AI-related terms appear.
- [MAIN_TOPIC] Select one or more topics from this predefined list that best describe the main purpose of this support interaction. Separate multiple topics with commas if the interaction covers multiple topics. Available topics: Account, Creating & editing the site, Domains, Downtime, Email issues, Error on their site, General billing, General plan questions, Hosting, Integrations, Jetpack issues, Monetization, Plan Cancelation/refund request, Plan Downgrade request, Plan Upgrade request, Plugin support, Presales opportunity, Site performance issues, Theme support, User wanted to speak with an agent/human, WooCommerce-related, SEO, Security, Other. If none of these fit, use "Other".

Stick to the start marker structure and don't add any formatting so that I can easily extract the data.
"""

	csat_good = """You are an AI customer support supervisor for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others) communicating with customers via email. Your goal is to analyze support emails from users that gave us a good CSAT and understand what made their experience positive. You'll read the entire context, think carefully about the support interaction between the customer and the Happiness Engineer (support agent) and the comment the user left on the CSAT survey, and then generate a detailed report.
									
**Guidelines for your replies:**
- Remember: your goal here isn't to provide technical support: instead, you are a supervisor that is creating an internal report on the support interaction.
- The report must be in English. Don't use any text formatting.
- If you can't create a comprehensive analysis for the criteria of the report structure due to lack of context, just say "I couldn't analyze this ticket because I don't have all the information I need"
- Please use this structure for your report:

**Report structure:**
- [DETAIL_SUMMARY] Short summary of the interaction (if multiple issues were discussed, separate by issue)
- [CUSTOMER_GOAL] State the customer's main goal in a concise format (e.g., "Import subscribers to WordPress.com" rather than "The customer was trying to import subscribers"). Use an action verb and be specific but brief.
- [SENTIMENT_ANALYSIS] The overall sentiment of the customer during the support interaction. Allowed responses are: "Negative", "Neutral", or "Positive".
- [WHAT_HAPPENED] Develop a comprehensive hypothesis explaining the user's good rating, considering the entire context and potential external influences.
- [ISSUE_RESOLVED] Issue is resolved? Respond with "TRUE" or "FALSE" based on their CSAT comment and interaction content
- [INTERACTION_TOPICS] List the main topics discussed. Break down the topics into concise and specific categories. Avoid generalizations and ensure topics are clear and actionable. If possible, group related subtopics under broader categories. Final result is a list of one or more topics, separated by commas.
- [PRODUCT_FEEDBACK] If the interaction contains any feedback about the product (feature requests, complaints about functionality, suggestions for improvement, etc.), summarize it concisely and include direct quotes from the customer that provide context for the feedback. Format as: "Feedback summary - 'relevant customer quote'". If no product feedback is present, return "NONE"
- [RELATED_TO_PRODUCT] Return "TRUE" if the positive sentiment comes from product satisfaction (features, functionality, usability, etc), else return "FALSE"
- [RELATED_TO_SERVICE] Return "TRUE" if the positive sentiment comes from support service satisfaction (agent interaction, response time, etc), else return "FALSE"
- [AI_FEEDBACK] Return "TRUE" only if the customer explicitly provided feedback (positive or negative) about the AI support assistant based on their own words and experience. Look for customer comments expressing opinions about the AI quality, helpfulness, understanding, accuracy, or frustrations with AI responses. DO NOT return TRUE just because "AI" or "AI assistant" appears in the conversation - the mention must indicate the customer's feedback or opinion about it. Return "FALSE" if there is no explicit customer feedback about the AI assistant, even if AI-related terms appear.
- [MAIN_TOPIC] Select one or more topics from this predefined list that best describe the main purpose of this support interaction. Separate multiple topics with commas if the interaction covers multiple topics. Available topics: Account, Creating & editing the site, Domains, Downtime, Email issues, Error on their site, General billing, General plan questions, Hosting, Integrations, Jetpack issues, Monetization, Plan Cancelation/refund request, Plan Downgrade request, Plan Upgrade request, Plugin support, Presales opportunity, Site performance issues, Theme support, User wanted to speak with an agent/human, WooCommerce-related, SEO, Security, Other. If none of these fit, use "Other".

Stick to the start marker structure and don't add any formatting so that I can easily extract the data.
"""

	csat_missing = """You are an AI customer support supervisor for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others) communicating with customers via email. Your goal is to analyze support emails and understand the nature of the interaction when no CSAT rating was provided. You'll read the entire context, think carefully about the support interaction between the customer and the Happiness Engineer (support agent), and then generate a detailed report.
									
**Guidelines for your replies:**
- Remember: your goal here isn't to provide technical support: instead, you are a supervisor that is creating an internal report on the support interaction.
- The report must be in English. Don't use any text formatting.
- If you can't create a comprehensive analysis for the criteria of the report structure due to lack of context, just say "I couldn't analyze this ticket because I don't have all the information I need"
- Please use this structure for your report:

**Report structure:**
- [DETAIL_SUMMARY] Short summary of the interaction (if multiple issues were discussed, separate by issue)
- [CUSTOMER_GOAL] State the customer's main goal in a concise format (e.g., "Import subscribers to WordPress.com" rather than "The customer was trying to import subscribers"). Use an action verb and be specific but brief.
- [SENTIMENT_ANALYSIS] The overall sentiment of the customer during the support interaction. Allowed responses are: "Negative", "Neutral", or "Positive".
- [WHAT_HAPPENED] Analyze the interaction and identify any potential issues or positive aspects of the support experience, even though no CSAT was provided.
- [ISSUE_RESOLVED] Issue is resolved? Respond with "TRUE" or "FALSE" based on the interaction content
- [INTERACTION_TOPICS] List the main topics discussed. Break down the topics into concise and specific categories. Avoid generalizations and ensure topics are clear and actionable. If possible, group related subtopics under broader categories. Final result is a list of one or more topics, separated by commas.
- [PRODUCT_FEEDBACK] If the interaction contains any feedback about the product (feature requests, complaints about functionality, suggestions for improvement, etc.), summarize it concisely and include direct quotes from the customer that provide context for the feedback. Format as: "Feedback summary - 'relevant customer quote'". If no product feedback is present, return "NONE"
- [RELATED_TO_PRODUCT] Return "TRUE" if there were product-related issues (Feedback related to the product's functionality, usability, complexity, or feature limitations, even if the issue was reported during a support interaction. This includes concerns about features not working as expected, difficulties navigating the platform, or frustrations with the product's design or capabilities.), else return "FALSE"
- [RELATED_TO_SERVICE] Return "TRUE" if there were support service-related issues (Feedback related to the interaction with support agents, response times, communication quality, or the overall customer service experience. This includes issues like perceived rudeness, lack of helpfulness, delays, or process dissatisfaction.), else return "FALSE"
- [AI_FEEDBACK] Return "TRUE" only if the customer explicitly provided feedback (positive or negative) about the AI support assistant based on their own words and experience. Look for customer comments expressing opinions about the AI quality, helpfulness, understanding, accuracy, or frustrations with AI responses. DO NOT return TRUE just because "AI" or "AI assistant" appears in the conversation - the mention must indicate the customer's feedback or opinion about it. Return "FALSE" if there is no explicit customer feedback about the AI assistant, even if AI-related terms appear.
- [MAIN_TOPIC] Select one or more topics from this predefined list that best describe the main purpose of this support interaction. Separate multiple topics with commas if the interaction covers multiple topics. Available topics: Account, Creating & editing the site, Domains, Downtime, Email issues, Error on their site, General billing, General plan questions, Hosting, Integrations, Jetpack issues, Monetization, Plan Cancelation/refund request, Plan Downgrade request, Plan Upgrade request, Plugin support, Presales opportunity, Site performance issues, Theme support, User wanted to speak with an agent/human, WooCommerce-related, SEO, Security, Other. If none of these fit, use "Other".

Stick to the start marker structure and don't add any formatting so that I can easily extract the data.
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
	
def clean_boolean_response(value: str) -> str:
	"""Clean boolean responses to ensure only TRUE or FALSE values are used."""
	# Convert to lowercase and remove leading/trailing whitespace to standardize the input
	value = value.lower().strip()
	
	# Check for any variation of "true" in the text
	if any(word in value for word in ['true', 'yes']):
		return "TRUE"
	else:
		return "FALSE"

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
                    'SENTIMENT_ANALYSIS': "Skipped - closed by automerge",
                    'WHAT_HAPPENED': "Skipped - closed by automerge",
                    'ISSUE_RESOLVED': "Skipped - closed by automerge",
                    'INTERACTION_TOPICS': "Skipped - closed by automerge",
                    'PRODUCT_FEEDBACK': "Skipped - closed by automerge",
                    'RELATED_TO_PRODUCT': "Skipped - closed by automerge",
                    'RELATED_TO_SERVICE': "Skipped - closed by automerge",
                    'AI_FEEDBACK': "FALSE",
                    'MAIN_TOPIC': "Skipped - closed by automerge"
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
	"""Get response from OpenAI API with retry logic and intelligent error handling."""
	# Use shared OpenAI client for connection reuse
	client = get_openai_client(api_key=api_key, use_local=use_local)
	
	for attempt in range(max_retries):
		try:
			response = openai.chat.completions.create(
				model="gpt-4.1-mini",
				messages=[
					{"role": "system", "content": "You are a customer support supervisor analyzing support interactions."},
					{"role": "user", "content": prompt}
				],
				temperature=0.7,
				max_tokens=1000,
				timeout=30  # 30 second timeout per request
			)
			
			content = response.choices[0].message.content
			
			# Debug: Print the raw response content
			print("\nRaw API Response:")
			print(content)
			print("\n" + "="*50 + "\n")
			
			# Helper function to safely extract sections
			def extract_section(content: str, start_marker: str, end_marker: str) -> str:
				try:
					if start_marker not in content:
						print(f"Error: Missing start marker '{start_marker}' in response")
						return "Analysis incomplete"
					
					start_idx = content.index(start_marker) + len(start_marker)
					
					# If this is the last section (RELATED_TO_SERVICE), take everything until the end
					if end_marker == "":
						return content[start_idx:].strip()
					
					if end_marker not in content[start_idx:]:
						print(f"Error: Missing end marker '{end_marker}' in response")
						return "Analysis incomplete"
					
					end_idx = content.index(end_marker, start_idx)
					return content[start_idx:end_idx].strip()
				except ValueError as e:
					print(f"Error extracting section: {str(e)}")
					return "Analysis incomplete"
			
			# Define all section markers
			sections = {
				"DETAIL_SUMMARY": ("[DETAIL_SUMMARY]", "[CUSTOMER_GOAL]"),
				"CUSTOMER_GOAL": ("[CUSTOMER_GOAL]", "[SENTIMENT_ANALYSIS]"),
				"SENTIMENT_ANALYSIS": ("[SENTIMENT_ANALYSIS]", "[WHAT_HAPPENED]"),
				"WHAT_HAPPENED": ("[WHAT_HAPPENED]", "[ISSUE_RESOLVED]"),
				"ISSUE_RESOLVED": ("[ISSUE_RESOLVED]", "[INTERACTION_TOPICS]"),
				"INTERACTION_TOPICS": ("[INTERACTION_TOPICS]", "[PRODUCT_FEEDBACK]"),
				"PRODUCT_FEEDBACK": ("[PRODUCT_FEEDBACK]", "[RELATED_TO_PRODUCT]"),
				"RELATED_TO_PRODUCT": ("[RELATED_TO_PRODUCT]", "[RELATED_TO_SERVICE]"),
				"RELATED_TO_SERVICE": ("[RELATED_TO_SERVICE]", "[AI_FEEDBACK]"),
				"AI_FEEDBACK": ("[AI_FEEDBACK]", "[MAIN_TOPIC]"),
				"MAIN_TOPIC": ("[MAIN_TOPIC]", "")  # Empty string for last section
			}
			
			# Extract all sections with error handling
			result = {}
			missing_sections = []
			
			for section_name, (start_marker, end_marker) in sections.items():
				raw_value = extract_section(content, start_marker, end_marker)
				
				if raw_value == "Analysis incomplete":
					missing_sections.append(section_name)
				
				# Apply appropriate cleaning function based on section
				if section_name == "SENTIMENT_ANALYSIS":
					result[section_name] = clean_sentiment_analysis(raw_value)
				elif section_name == "ISSUE_RESOLVED":
					result[section_name] = clean_issue_resolved(raw_value)
				elif section_name in ["RELATED_TO_PRODUCT", "RELATED_TO_SERVICE", "AI_FEEDBACK"]:
					result[section_name] = clean_boolean_response(raw_value)
				else:
					result[section_name] = raw_value
			
			if missing_sections:
				print(f"\nWarning: Missing or incomplete sections: {', '.join(missing_sections)}")
				print("Retrying request...")
				if attempt < max_retries - 1:
					time.sleep(2 ** attempt)
					continue
			
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
			if attempt == max_retries - 1:
				print("Response content that caused the error:", 
					  response.choices[0].message.content if 'response' in locals() else "No response received")
				return None
			time.sleep(2 ** attempt)  # Exponential backoff

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
		df['MAIN_TOPIC'] = None
		
		# Initialize progress tracker and rate limiter
		progress_tracker = ThreadSafeProgressTracker(total_rows)
		
		# Set rate limit based on API type and thread count
		if use_local:
			rate_limit = 50.0  # Local server can handle more requests
		else:
			rate_limit = 15.0  # Conservative for OpenAI API with multiple threads
		
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
					# Handle errors
					progress_tracker.update(errors=1)
					error_msg = f"Error: {result.error}" if result.error else "Error generating report"
					
					for col in ['DETAIL_SUMMARY', 'CUSTOMER_GOAL', 'SENTIMENT_ANALYSIS', 
							   'WHAT_HAPPENED', 'ISSUE_RESOLVED', 'INTERACTION_TOPICS', 
							   'PRODUCT_FEEDBACK', 'RELATED_TO_PRODUCT', 'RELATED_TO_SERVICE', 'AI_FEEDBACK', 'MAIN_TOPIC']:
						df.at[result.index, col] = error_msg
				
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
	parser.add_argument('--threads', type=int, default=5, help='Number of concurrent processing threads (default: 5)')
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