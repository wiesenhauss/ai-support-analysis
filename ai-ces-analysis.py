#!/usr/bin/env python3
"""
AI CES (Customer Experience Standard) Quality Analysis
by @wiesenhauss

This script evaluates AI support conversations across six quality dimensions,
producing per-ticket numeric scores that capture how well the AI handled each
interaction. It operates independently of the Core Analysis and only requires
a conversation column in the input CSV.

Quality Dimensions:
  TASK_COMPLETION      (0-2)  Did the AI help the customer accomplish their goal?
  USER_COMPREHENSION   (0-2)  Did the user understand the AI's guidance?
  TONE                 (0-2)  Was the AI's communication style appropriate?
  ESCALATION_HANDLING  (-1-1) Did the AI handle escalation correctly?
  PROACTIVITY          (0-2)  Did the AI go beyond the immediate question?
  COHERENCE            (0-2)  Did the conversation flow naturally and consistently?

Usage:
  python ai-ces-analysis.py -file="path/to/input.csv" [--local] [--threads=50]
  python ai-ces-analysis.py  # Interactive mode

Arguments:
  -file, --input-file    Path to the input CSV file
  --local                Use local AI server (localhost:1234) instead of OpenAI API
  --threads              Number of concurrent processing threads (default: 50)
  --column-mapping       JSON mapping of CSV column names to expected names

Required CSV Columns:
  - Interaction Message Body (or "conversation", or mapped via --column-mapping)

Environment Variables:
  OPENAI_API_KEY  Required unless using --local flag

Output:
  Creates a timestamped CSV with CES_ prefixed analysis columns:
  ai-ces-analysis-output-YYYY-MM-DD_HHhMM.csv
"""

import pandas as pd
import openai
import time
from typing import Optional
import datetime
import os
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import gc
import json

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

# ---------------------------------------------------------------------------
# JSON Schema for Structured Outputs
# ---------------------------------------------------------------------------

CES_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "ai_ces_analysis",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "task_completion": {
                    "type": "integer",
                    "enum": [0, 1, 2],
                    "description": (
                        "Task Completion score. "
                        "0 = Incomplete, 1 = Partially completed, 2 = Completed."
                    )
                },
                "user_comprehension": {
                    "type": "integer",
                    "enum": [0, 1, 2],
                    "description": (
                        "User Comprehension score. "
                        "0 = Did not understand, 1 = Unclear, 2 = Demonstrated understanding."
                    )
                },
                "tone": {
                    "type": "integer",
                    "enum": [0, 1, 2],
                    "description": (
                        "Tone score. "
                        "0 = Cold/robotic/inappropriate, 1 = Professional but neutral, "
                        "2 = Friendly/approachable/well-matched."
                    )
                },
                "escalation_handling": {
                    "type": "integer",
                    "enum": [-1, 0, 1],
                    "description": (
                        "Escalation Handling score. "
                        "-1 = Missed or incorrect, 0 = Not applicable, 1 = Correctly handled."
                    )
                },
                "proactivity": {
                    "type": "integer",
                    "enum": [0, 1, 2],
                    "description": (
                        "Proactivity score. "
                        "0 = Missed obvious opportunity, 1 = Responsive only, 2 = Proactive."
                    )
                },
                "coherence": {
                    "type": "integer",
                    "enum": [0, 1, 2],
                    "description": (
                        "Coherence score. "
                        "0 = Disjointed, 1 = Minor friction, 2 = Seamless."
                    )
                },
            },
            "required": [
                "task_completion",
                "user_comprehension",
                "tone",
                "escalation_handling",
                "proactivity",
                "coherence",
            ],
            "additionalProperties": False,
        },
    },
}

RESPONSE_TO_COLUMN_MAP = {
    "task_completion": "CES_TASK_COMPLETION",
    "user_comprehension": "CES_USER_COMPREHENSION",
    "tone": "CES_TONE",
    "escalation_handling": "CES_ESCALATION_HANDLING",
    "proactivity": "CES_PROACTIVITY",
    "coherence": "CES_COHERENCE",
}

# ---------------------------------------------------------------------------
# Evaluation rubric (embedded in the user prompt)
# ---------------------------------------------------------------------------

CES_PROMPT = """You are an AI quality evaluator for Automattic (maker of WordPress.com, Jetpack, WooCommerce, and others). Your job is to evaluate the following support conversation between a customer and an AI support assistant across six quality dimensions.

Read the entire conversation carefully, then score each dimension using the rubrics below.

---

**TASK_COMPLETION** — Did the AI help the customer accomplish what they came to do?
0 — Incomplete. The customer's need was not addressed, or the interaction ended with the customer no further along than when they started. The customer would need to reach out again about the same issue.
1 — Partially completed. The customer made progress but doesn't yet have everything they need. The AI provided some useful information or correct next steps, but gaps remain. Also applies to correct handoffs to human agents where the AI provided appropriate context.
2 — Completed. The customer received what they needed — whether that's a direct answer, a working solution, clear and sufficient guidance to act independently, or productive help with an exploratory question. If the user stopped replying after receiving a substantive, actionable response, default to this score unless there are signals of confusion or dissatisfaction.

**USER_COMPREHENSION** — Did the user understand the AI's guidance? Look for observable signals in the transcript.
0 — User did not understand. Evidence: the user asked the same question again, expressed confusion ("I don't get it," "what do you mean?"), took an incorrect action based on the AI's guidance, or asked follow-ups that indicate they misunderstood the instructions.
1 — Unclear whether the user understood. Limited signal in the transcript — the user may have gone silent after a response, gave brief acknowledgments, or the conversation was too short to judge. When in doubt between 0 and 1, choose 1.
2 — User demonstrated understanding. Evidence: the user confirmed the steps, asked relevant follow-up questions that build on the AI's response, reported success, or proceeded correctly to a next step consistent with the AI's guidance.

**TONE** — Was the AI's communication style appropriate and approachable?
0 — Cold, robotic, dismissive, or inappropriate. The customer would feel like they're talking to a broken machine, or the tone is mismatched to the situation (e.g., overly casual when the customer is frustrated and losing business, overly formal when the customer is being playful).
1 — Professional but neutral. Polite and functional, but lacking warmth. The customer wouldn't complain, but wouldn't feel particularly cared for either. This is an acceptable baseline.
2 — Friendly, approachable, and well-matched. The AI feels like a helpful person — empathetic when the customer is frustrated, encouraging when they're exploring, natural and conversational throughout. This reflects the WordPress.com support identity.

**ESCALATION_HANDLING** — Did the AI handle escalation correctly?
-1 — Missed or incorrect. The AI should have escalated but didn't, escalated to the wrong channel, escalated prematurely when it could have resolved the issue, or suggested a channel unavailable to the customer's support tier.
0 — Not applicable. No escalation was needed and none was attempted.
1 — Correctly handled. The AI escalated at the right time, to the right channel, with appropriate context. Or the AI correctly identified that escalation was available but resolved the issue without needing it.

**PROACTIVITY** — Did the AI go beyond the immediate question?
0 — Missed obvious opportunity. There was a clear, natural chance to add value (e.g., the customer's question implied a deeper misunderstanding, a related problem was visible, or a known follow-up issue was foreseeable) and the AI ignored it.
1 — Responsive only. The AI answered what was asked, competently, but didn't look further. This is the expected baseline and is not a negative score.
2 — Proactive. The AI anticipated related needs, prevented a foreseeable follow-up problem, suggested useful related resources, or found a creative solution. This must be genuinely helpful — do not reward generic closers like "Is there anything else I can help with?"

**COHERENCE** — Did the conversation flow naturally and consistently?
0 — Disjointed. The AI contradicted itself, repeated the same information unnecessarily, lost track of what was already discussed, or produced confusing conversation flow.
1 — Minor friction. Mostly smooth, but with small issues like slight repetition, an awkward transition, or a minor inconsistency that didn't cause real confusion.
2 — Seamless. The conversation reads naturally. The AI maintains context throughout, builds on earlier parts of the conversation, and transitions smoothly between topics.

---

Return your evaluation as a JSON object with integer scores for each dimension."""

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TicketTask:
    index: int
    row: dict

@dataclass
class ProcessingResult:
    index: int
    success: bool
    report: Optional[dict]
    error: Optional[str] = None

# ---------------------------------------------------------------------------
# Threading helpers (same pattern as main-analysis-process.py)
# ---------------------------------------------------------------------------

class ThreadSafeProgressTracker:
    def __init__(self, total_items: int):
        self.total_items = total_items
        self.processed = 0
        self.skipped = 0
        self.errors = 0
        self.lock = threading.Lock()
        self.start_time = datetime.datetime.now()

    def update(self, processed: int = 0, skipped: int = 0, errors: int = 0):
        with self.lock:
            self.processed += processed
            self.skipped += skipped
            self.errors += errors

    def get_stats(self):
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
                "processed": self.processed,
                "skipped": self.skipped,
                "errors": self.errors,
                "completed": completed,
                "remaining": remaining,
                "elapsed": elapsed,
                "rate": rate,
                "remaining_time": datetime.timedelta(seconds=remaining_time),
            }


class RateLimiter:
    def __init__(self, max_requests_per_second: float = 10.0):
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()

    def wait_if_needed(self):
        with self.lock:
            now = time.time()
            gap = now - self.last_request_time
            if gap < self.min_interval:
                time.sleep(self.min_interval - gap)
            self.last_request_time = time.time()

# ---------------------------------------------------------------------------
# CSV reading
# ---------------------------------------------------------------------------

def read_csv_file(file_path: str, column_mapping: dict = None) -> pd.DataFrame:
    """Read CSV and locate the conversation column."""
    try:
        df = pd.read_csv(file_path)

        if column_mapping:
            rename_map = {v: k for k, v in column_mapping.items() if v in df.columns}
            if rename_map:
                df = df.rename(columns=rename_map)
                print(f"Applied column mapping: {', '.join(f'{old} -> {new}' for old, new in rename_map.items())}")

        # Try several common names for the conversation column
        conversation_col = find_column_by_substring(df, "Interaction Message Body")
        if not conversation_col:
            conversation_col = find_column_by_substring(df, "Ticket Message Body")
        if not conversation_col:
            conversation_col = find_column_by_substring(df, "conversation")

        if not conversation_col:
            raise Exception(
                "Could not find conversation column. "
                "Looking for 'Interaction Message Body', 'Ticket Message Body', or 'conversation'."
            )

        df.attrs["conversation_column"] = conversation_col
        return df

    except Exception as e:
        raise Exception(f"Error reading CSV file: {str(e)}")

# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def create_ces_prompt(row: dict, conversation_col: str) -> str:
    """Build the evaluation prompt for a single ticket."""
    conversation = row.get(conversation_col, "Not provided")
    if pd.isna(conversation):
        conversation = "Not provided"

    context = f"Support Conversation:\n{conversation}"
    return context + "\n\n" + CES_PROMPT

# ---------------------------------------------------------------------------
# OpenAI call
# ---------------------------------------------------------------------------

def get_openai_response(prompt: str, api_key: str, max_retries: int = 3, use_local: bool = False) -> Optional[dict]:
    """Get structured JSON response from the API with retry logic."""
    client = get_openai_client(api_key=api_key, use_local=use_local)

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AI quality evaluator scoring support conversations. "
                            "Provide accurate numeric scores based strictly on the rubrics provided."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format=CES_RESPONSE_SCHEMA,
                temperature=0.4,
                max_tokens=500,
                timeout=60,
            )

            content = response.choices[0].message.content

            try:
                json_result = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"\nJSON parsing error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None

            result = {}
            for json_key, csv_column in RESPONSE_TO_COLUMN_MAP.items():
                if json_key in json_result:
                    result[csv_column] = json_result[json_key]
                else:
                    print(f"Warning: Missing key '{json_key}' in response")
                    result[csv_column] = None

            print(f"\n✓ CES scores: "
                  f"TC={result.get('CES_TASK_COMPLETION')} "
                  f"UC={result.get('CES_USER_COMPREHENSION')} "
                  f"T={result.get('CES_TONE')} "
                  f"EH={result.get('CES_ESCALATION_HANDLING')} "
                  f"P={result.get('CES_PROACTIVITY')} "
                  f"C={result.get('CES_COHERENCE')}")

            return result

        except openai.RateLimitError as e:
            print(f"\nRate limit hit on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = min(60, 2 ** attempt * 5)
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

# ---------------------------------------------------------------------------
# Single-ticket processing
# ---------------------------------------------------------------------------

def process_single_ticket(
    task: TicketTask,
    api_key: str,
    use_local: bool,
    rate_limiter: RateLimiter,
    conversation_col: str,
) -> ProcessingResult:
    try:
        row = task.row

        conversation = row.get(conversation_col, "")
        if not conversation or (isinstance(conversation, float) and pd.isna(conversation)):
            return ProcessingResult(
                index=task.index,
                success=True,
                report={col: None for col in RESPONSE_TO_COLUMN_MAP.values()},
            )

        rate_limiter.wait_if_needed()

        prompt = create_ces_prompt(row, conversation_col)
        report = get_openai_response(prompt, api_key, use_local=use_local)

        if report:
            return ProcessingResult(index=task.index, success=True, report=report)
        else:
            return ProcessingResult(
                index=task.index,
                success=False,
                report=None,
                error="Failed to get valid API response",
            )

    except Exception as e:
        return ProcessingResult(
            index=task.index, success=False, report=None, error=str(e)
        )

# ---------------------------------------------------------------------------
# CSV processing (concurrent)
# ---------------------------------------------------------------------------

def process_csv(
    input_file: str,
    output_file: str,
    api_key: str,
    use_local: bool = False,
    max_workers: int = 50,
    column_mapping: dict = None,
) -> None:
    """Process the CSV with concurrent threads."""
    try:
        df = read_csv_file(input_file, column_mapping=column_mapping)
        total_rows = len(df)
        conversation_col = df.attrs["conversation_column"]

        print(f"🚀 Starting AI CES analysis with {max_workers} threads")
        print(f"📊 Processing {total_rows:,} tickets...")
        print(f"💬 Conversation column: {conversation_col}")

        for csv_col in RESPONSE_TO_COLUMN_MAP.values():
            df[csv_col] = None

        progress_tracker = ThreadSafeProgressTracker(total_rows)

        rate_limit = 200.0 if use_local else 100.0
        rate_limiter = RateLimiter(rate_limit)

        pbar = tqdm(
            total=total_rows,
            desc="CES analysis",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} tickets "
            "[{elapsed}<{remaining}, {rate_fmt}{postfix}]",
        )

        tasks = []
        for idx in df.index:
            row_dict = df.loc[idx].to_dict()
            tasks.append(TicketTask(index=idx, row=row_dict))

        results_lock = threading.Lock()
        save_counter = 0

        def update_dataframe_with_result(result: ProcessingResult):
            nonlocal save_counter

            with results_lock:
                if result.success and result.report:
                    progress_tracker.update(processed=1)
                    for key, value in result.report.items():
                        df.at[result.index, key] = value
                else:
                    progress_tracker.update(errors=1)
                    error_msg = f"Error: {result.error}" if result.error else "Error"
                    for csv_col in RESPONSE_TO_COLUMN_MAP.values():
                        df.at[result.index, csv_col] = error_msg

                stats = progress_tracker.get_stats()
                pbar.update(1)
                pbar.set_postfix(
                    {
                        "Processed": stats["processed"],
                        "Errors": stats["errors"],
                        "Rate": f"{stats['rate']:.1f}/s",
                        "Remaining": str(stats["remaining_time"]).split(".")[0],
                    }
                )

                save_counter += 1
                if save_counter >= 50:
                    df.to_csv(output_file, index=False)
                    save_counter = 0
                    gc.collect()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(
                    process_single_ticket,
                    task,
                    api_key,
                    use_local,
                    rate_limiter,
                    conversation_col,
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
                        report=None,
                        error=f"Unexpected error: {str(e)}",
                    )
                    update_dataframe_with_result(error_result)

        df.to_csv(output_file, index=False)
        pbar.close()

        del tasks
        del future_to_task
        gc.collect()

        final_stats = progress_tracker.get_stats()
        print(f"\n✅ AI CES analysis completed!")
        print(f"📊 Tickets processed: {final_stats['processed']:,}")
        print(f"❌ Errors encountered: {final_stats['errors']:,}")
        print(f"⏱️  Total time: {str(final_stats['elapsed']).split('.')[0]}")
        print(f"🚀 Average speed: {final_stats['rate']:.2f} tickets/second")
        print(f"💾 Output saved to: {output_file}")

    except Exception as e:
        print(f"❌ Error in AI CES processing: {str(e)}")
        df.to_csv(output_file, index=False)
        raise

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    load_dotenv()

    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%Hh%M")

    parser = argparse.ArgumentParser(
        description="AI CES Quality Analysis — score support conversations on six quality dimensions."
    )
    parser.add_argument("-file", "--input-file", type=str, help="Path to the input CSV file")
    parser.add_argument("--local", action="store_true", help="Use local AI server instead of OpenAI API")
    parser.add_argument("--threads", type=int, default=50, help="Number of concurrent processing threads (default: 50)")
    parser.add_argument(
        "--column-mapping",
        type=str,
        default=None,
        help='JSON mapping of CSV column names to expected names',
    )
    args = parser.parse_args()

    INPUT_FILE = args.input_file
    if not INPUT_FILE:
        INPUT_FILE = input("Enter the full path to the CSV file to process: ")

    INPUT_FILE = normalize_file_path(INPUT_FILE)

    file_dir = os.path.dirname(INPUT_FILE)
    OUTPUT_FILE = os.path.join(file_dir, f"ai-ces-analysis-output-{current_time}.csv")

    API_KEY = os.getenv("OPENAI_API_KEY")

    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Input file not found at: {INPUT_FILE}")

    if not args.local and not API_KEY:
        raise ValueError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")

    MAX_WORKERS = args.threads

    if args.local:
        print(f"Using local AI server at http://localhost:1234/v1 with {MAX_WORKERS} threads")
    else:
        print(f"Using OpenAI API with {MAX_WORKERS} concurrent threads")

    col_mapping = None
    if args.column_mapping:
        try:
            col_mapping = json.loads(args.column_mapping)
            print(f"Column mapping provided: {col_mapping}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid --column-mapping JSON: {e}")

    process_csv(INPUT_FILE, OUTPUT_FILE, API_KEY, use_local=args.local, max_workers=MAX_WORKERS, column_mapping=col_mapping)


if __name__ == "__main__":
    main()
