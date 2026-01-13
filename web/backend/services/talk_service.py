"""
Talk to Data Service.
Provides natural language querying of support data.
"""

import sys
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import openai


# Column metadata for intelligent selection
COLUMN_METADATA = {
    "created_date": {
        "description": "Date ticket was created - for trend analysis",
        "priority": "high"
    },
    "ticket_id": {
        "description": "Unique ticket identifier",
        "priority": "low"
    },
    "csat_rating": {
        "description": "Customer satisfaction rating (good/bad)",
        "priority": "high"
    },
    "sentiment": {
        "description": "Overall sentiment (Positive/Neutral/Negative)",
        "priority": "very_high"
    },
    "issue_resolved": {
        "description": "Whether the issue was resolved",
        "priority": "high"
    },
    "main_topic": {
        "description": "Main categorized topic",
        "priority": "very_high"
    },
    "customer_goal": {
        "description": "What the customer wanted to achieve",
        "priority": "very_high"
    },
    "detail_summary": {
        "description": "AI-generated summary of the interaction",
        "priority": "very_high"
    },
    "what_happened": {
        "description": "AI analysis of what happened",
        "priority": "high"
    },
    "product_feedback": {
        "description": "Product feedback with customer quotes",
        "priority": "very_high"
    },
    "related_to_product": {
        "description": "Whether sentiment relates to product issues",
        "priority": "medium"
    },
    "related_to_service": {
        "description": "Whether sentiment relates to support service",
        "priority": "medium"
    },
    "product_area": {
        "description": "Product area (Domains, Email, Themes, etc.)",
        "priority": "high"
    },
    "feature_requests": {
        "description": "Feature requests mentioned",
        "priority": "high"
    },
    "pain_points": {
        "description": "Customer frustrations",
        "priority": "high"
    }
}


class TalkToDataService:
    """
    Service for natural language data querying.
    
    Analyzes support ticket data and answers questions using AI.
    """
    
    def __init__(self, api_key: str, data_store):
        self.api_key = api_key
        self.data_store = data_store
        self.client = openai.OpenAI(api_key=api_key)
        
        # Conversation management
        self.conversation_history = []
        self.current_context_columns = []
        self.conversation_summary = ""
        self.max_history_length = 3
        
        # Token limits
        self.MAX_TOKENS = 100000
        self.CHUNK_TOKEN_LIMIT = int(self.MAX_TOKENS * 0.7)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text (rough approximation)."""
        return len(text) // 4
    
    def _select_columns(self, question: str) -> List[str]:
        """
        Use AI to select relevant columns for the question.
        """
        available_columns = list(COLUMN_METADATA.keys())
        
        prompt = f"""Given this question about support ticket data:
"{question}"

Select the most relevant columns from this list to answer the question.
Available columns with descriptions:
{json.dumps(COLUMN_METADATA, indent=2)}

Return a JSON array of column names to use. Select 3-7 most relevant columns.
Example: ["sentiment", "main_topic", "detail_summary"]

Only return the JSON array, nothing else."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            result = response.choices[0].message.content.strip()
            # Parse JSON array
            columns = json.loads(result)
            
            # Validate columns exist
            valid_columns = [c for c in columns if c in available_columns]
            
            # Always include some key columns if not present
            if "sentiment" not in valid_columns and len(valid_columns) < 7:
                valid_columns.append("sentiment")
            if "main_topic" not in valid_columns and len(valid_columns) < 7:
                valid_columns.append("main_topic")
            
            return valid_columns
            
        except Exception:
            # Default columns on error
            return ["sentiment", "main_topic", "detail_summary", "customer_goal", "csat_rating"]
    
    def _prepare_data_sample(self, df: pd.DataFrame, columns: List[str]) -> str:
        """Prepare a sample of data for the AI to analyze."""
        # Select only requested columns that exist
        available_cols = [c for c in columns if c in df.columns]
        sample_df = df[available_cols].copy()
        
        # Sample data if too large
        max_rows = 500
        if len(sample_df) > max_rows:
            sample_df = sample_df.sample(n=max_rows, random_state=42)
        
        # Convert to string representation
        data_str = sample_df.to_string(index=False)
        
        # Truncate if still too long
        max_chars = 50000
        if len(data_str) > max_chars:
            data_str = data_str[:max_chars] + "\n... (data truncated)"
        
        return data_str
    
    async def ask_question(
        self,
        question: str,
        columns: Optional[List[str]] = None,
        is_follow_up: bool = False
    ) -> Dict[str, Any]:
        """
        Answer a question about the data.
        
        Args:
            question: The question to answer
            columns: Optional list of columns to use (auto-selected if not provided)
            is_follow_up: Whether this is a follow-up question
            
        Returns:
            Dictionary with answer and metadata
        """
        # Get data
        df = self.data_store.get_tickets_dataframe()
        
        if df.empty:
            return {
                "answer": "No data available in the database. Please import analyzed CSV files first.",
                "selected_columns": [],
                "token_count": 0
            }
        
        # Select columns if not provided
        if not columns:
            columns = self._select_columns(question)
        
        self.current_context_columns = columns
        
        # Prepare data sample
        data_sample = self._prepare_data_sample(df, columns)
        
        # Build system prompt
        system_prompt = f"""You are a data analyst helping to analyze customer support ticket data.
You have access to {len(df)} support tickets with the following columns: {', '.join(columns)}.

Analyze the data provided and answer questions thoroughly with:
- Key statistics and numbers
- Clear insights and patterns
- Specific examples when relevant
- Recommendations if applicable

Be concise but comprehensive. Use markdown formatting for clarity."""

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history for follow-ups
        if is_follow_up and self.conversation_history:
            # Add summary if exists
            if self.conversation_summary:
                messages.append({
                    "role": "system",
                    "content": f"Previous conversation summary: {self.conversation_summary}"
                })
            
            # Add recent history
            for exchange in self.conversation_history[-self.max_history_length:]:
                messages.append({"role": "user", "content": exchange["question"]})
                messages.append({"role": "assistant", "content": exchange["answer"]})
        
        # Add current question with data
        user_message = f"""Data sample ({len(df)} total tickets):

{data_sample}

Question: {question}"""
        
        messages.append({"role": "user", "content": user_message})
        
        # Get AI response
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.5,
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            token_count = response.usage.total_tokens if response.usage else 0
            
            # Save to conversation history
            self.conversation_history.append({
                "question": question,
                "answer": answer,
                "columns": columns
            })
            
            # Summarize if history getting long
            if len(self.conversation_history) > self.max_history_length * 2:
                self._summarize_conversation()
            
            return {
                "answer": answer,
                "selected_columns": columns,
                "token_count": token_count
            }
            
        except Exception as e:
            return {
                "answer": f"Error processing question: {str(e)}",
                "selected_columns": columns,
                "token_count": 0
            }
    
    def _summarize_conversation(self):
        """Summarize old conversation history to save context space."""
        if len(self.conversation_history) <= self.max_history_length:
            return
        
        # Take older history to summarize
        to_summarize = self.conversation_history[:-self.max_history_length]
        
        summary_prompt = "Summarize these Q&A exchanges briefly:\n\n"
        for ex in to_summarize:
            summary_prompt += f"Q: {ex['question']}\nA: {ex['answer'][:200]}...\n\n"
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            self.conversation_summary = response.choices[0].message.content
            
            # Keep only recent history
            self.conversation_history = self.conversation_history[-self.max_history_length:]
            
        except Exception:
            # On error, just truncate without summary
            self.conversation_history = self.conversation_history[-self.max_history_length:]
    
    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history = []
        self.conversation_summary = ""
        self.current_context_columns = []


# Singleton instance
_talk_service_instance: Optional[TalkToDataService] = None


def get_talk_service(api_key: str, data_store) -> TalkToDataService:
    """Get or create the talk service instance."""
    global _talk_service_instance
    
    # Create new instance if API key changes or doesn't exist
    if _talk_service_instance is None or _talk_service_instance.api_key != api_key:
        _talk_service_instance = TalkToDataService(api_key, data_store)
    
    return _talk_service_instance
