# AI Support Analyzer - Technical Documentation

> **Author**: @wiesenhauss for Automattic Inc.  
> **Last Updated**: January 2026  
> **Version**: 12.x

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Architecture](#architecture)
4. [Core Components](#core-components)
5. [Web UI](#web-ui)
6. [Data Flow](#data-flow)
7. [AI Analysis Output Schema](#ai-analysis-output-schema)
8. [Database Schema](#database-schema)
9. [Configuration](#configuration)
10. [Usage Guide](#usage-guide)
11. [File Reference](#file-reference)

---

## Overview

The **AI Support Analyzer** is an AI-powered customer support data analysis tool built for Automattic Inc. (makers of WordPress.com, Jetpack, WooCommerce, and others). It uses OpenAI's GPT-4.1-mini model to analyze support ticket data and CSAT (Customer Satisfaction) survey responses, generating actionable insights for support team optimization.

### Key Capabilities

- **Automated ticket analysis** - AI-powered extraction of sentiment, topics, customer goals, and resolution status
- **CSAT prediction** - Predict customer satisfaction based on interaction sentiment
- **Trend detection** - Identify emerging issues, sentiment shifts, and problematic product areas
- **Product feedback mining** - Extract feature requests, pain points, and product improvement opportunities
- **Natural language querying** - Ask questions about your data in plain English
- **Historical analytics** - Track trends over time with anomaly detection

---

## Problem Statement

Customer support teams face several challenges that this tool addresses:

| Challenge | Solution |
|-----------|----------|
| **Manual ticket analysis is slow** | AI processes thousands of tickets concurrently (50 threads) |
| **Inconsistent categorization** | Structured JSON schema ensures consistent output format |
| **Understanding CSAT drivers** | AI analyzes conversations to identify root causes |
| **Detecting trends early** | Automated anomaly detection surfaces emerging issues |
| **Extracting product feedback** | AI mines interactions for feature requests and pain points |
| **Predicting satisfaction** | Sentiment analysis predicts CSAT before survey responses |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GUI Application                              │
│                          (gui_app.py)                                │
│   • File selection & validation                                      │
│   • API key management (macOS Keychain integration)                  │
│   • Real-time progress tracking                                      │
│   • Analysis module selection                                        │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Main Analysis Engine                            │
│                   (main-analysis-process.py)                         │
│   • GPT-4.1-mini with structured JSON outputs                        │
│   • Concurrent processing (50 threads default)                       │
│   • Rate limiting and retry logic                                    │
│   • Progress saving during processing                                │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────┬────────────────┬────────────────┬──────────────────┐
│   CSAT Trends  │     Topic      │    Product     │      Goals       │
│    Analysis    │  Aggregation   │    Feedback    │     Trends       │
│ (csat-trends)  │(topic-aggreg.) │ (prod-feed.)   │  (goals-trends)  │
└────────────────┴────────────────┴────────────────┴──────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                Historical Analytics & Storage                        │
│   • data_store.py (SQLite database with deduplication)              │
│   • analytics_engine.py (trend analysis, period comparisons)         │
│   • insights_engine.py (anomaly detection, automated insights)       │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Talk to Data Interface                          │
│                         (talktodata.py)                              │
│   • Natural language queries about analyzed data                     │
│   • Intelligent column selection                                     │
│   • GPT-4.1 powered analysis                                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12+ |
| AI/ML | OpenAI API (GPT-4.1-mini, GPT-4.1) |
| Data Processing | Pandas, NumPy |
| Database | SQLAlchemy + SQLite |
| Desktop GUI | Tkinter (cross-platform) |
| Web Backend | FastAPI, Uvicorn |
| Web Frontend | React 18, TypeScript, Tailwind CSS |
| Visualization | Matplotlib, Seaborn, Plotly, Recharts |
| Distribution | PyInstaller (macOS .app bundle) |

---

## Core Components

### 1. GUI Application (`gui_app.py`)

The main user interface providing:

- **Secure API key management** with macOS Keychain integration
- **Persistent settings** stored in `~/Library/Application Support/AI Support Analyzer/`
- **File selection** with drag & drop support
- **Analysis module selection** (choose which analyses to run)
- **Real-time progress tracking** with live log display
- **Cancel functionality** with force stop option

### 2. Main Analysis Engine (`main-analysis-process.py`)

The core AI processing engine:

- **Concurrent processing** with configurable thread count (default: 50)
- **Structured outputs** using OpenAI JSON schema for reliable parsing
- **Three analysis scenarios**:
  - Good CSAT ratings - understand what made experience positive
  - Bad CSAT ratings - understand what motivated negative feedback
  - Missing CSAT - analyze interaction when no rating provided
- **Rate limiting** with automatic retry logic
- **Progress saving** during long-running analyses

### 3. CSAT Prediction (`predict_csat.py`)

Predicts CSAT ratings based on sentiment analysis:

- Compares initial sentiment (from tags) with final sentiment (from analysis)
- Tracks sentiment changes during interactions
- Calculates prediction accuracy against actual CSAT scores

### 4. Analytics Engine (`analytics_engine.py`)

Historical trend analysis capabilities:

- Topic distribution over time
- Sentiment trend tracking
- Resolution rate calculations
- Period-over-period comparisons
- Pre-computed trend snapshots for fast dashboard rendering

### 5. Insights Engine (`insights_engine.py`)

Automated insight generation:

- **Anomaly detection** for sentiment, resolution rate, CSAT
- **Emerging topic identification**
- **Week-over-week** and **month-over-month** comparisons
- Configurable thresholds for warnings and critical alerts

### 6. Data Store (`data_store.py`)

SQLite-based historical storage:

- **Automatic deduplication** using ticket hash
- **CSV import** with column mapping
- **Query interface** for historical analysis
- Default location: `~/.ai_support_analyzer/analytics.db`

### 7. Talk to Data (`talktodata.py`)

Natural language data querying:

- Ask questions like "What are the main factors affecting CSAT scores?"
- Intelligent column selection based on question analysis
- Automatic data sampling for large datasets
- Comprehensive markdown-formatted results

---

## Web UI

The AI Support Analyzer includes a modern web-based interface as an alternative to the desktop GUI. The web UI provides a browser-based experience with interactive dashboards, real-time analysis, and a conversational data exploration interface.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Web Frontend (React + TypeScript)                │
│   • Dashboard with metrics and charts                               │
│   • File upload and analysis management                             │
│   • Interactive data exploration                                    │
│   • Talk to Data chat interface                                     │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ (REST API + WebSocket)
┌─────────────────────────────────────────────────────────────────────┐
│                     Web Backend (FastAPI + Python)                   │
│   • /api/analytics - Historical trend data                          │
│   • /api/insights - Anomaly detection and insights                  │
│   • /api/analysis - Run and monitor analysis jobs                   │
│   • /api/data - Import, query, and manage data                      │
│   • /api/talk - Natural language data querying                      │
│   • /api/settings - API key and configuration                       │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ (imports directly)
┌─────────────────────────────────────────────────────────────────────┐
│                     Existing Python Modules                          │
│   analytics_engine.py, insights_engine.py, data_store.py            │
│   main-analysis-process.py, models.py                               │
└─────────────────────────────────────────────────────────────────────┘
```

### Web UI Pages

| Page | Path | Description |
|------|------|-------------|
| Dashboard | `/` | Key metrics, sentiment trends, topic charts, critical alerts |
| Analyze | `/analyze` | Upload CSV files, configure options, monitor progress |
| Explore | `/explore` | Search and filter tickets with advanced filtering |
| Insights | `/insights` | AI-generated insights, anomaly detection, recommendations |
| Talk to Data | `/talk` | Chat interface for natural language data queries |
| Settings | `/settings` | API key configuration, database management, import history |

### Running the Web UI

**Prerequisites:**
- Python 3.12+
- Node.js 18+
- OpenAI API key 

**1. Start the Backend:**

```bash
cd web/backend
pip install -r ../requirements.txt
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/api/docs`.

**2. Start the Frontend:**

```bash
cd web/frontend
npm install
npm run dev
```

The web UI will be available at `http://localhost:5173`.

**3. Configure API Key:**

Navigate to Settings (`/settings`) and enter your OpenAI API key. The key is stored securely in `~/.ai_support_analyzer/web_settings.json`.

### Web API Endpoints

#### Analytics
- `GET /api/analytics/summary` - Summary statistics for date range
- `GET /api/analytics/sentiment-trend` - Sentiment over time
- `GET /api/analytics/topic-distribution` - Topic breakdown
- `GET /api/analytics/csat-trend` - CSAT satisfaction trend
- `GET /api/analytics/compare-periods` - Compare two time periods

#### Insights
- `GET /api/insights/weekly` - Week-over-week insights
- `GET /api/insights/monthly` - Month-over-month insights
- `GET /api/insights/anomalies` - Detected anomalies
- `GET /api/insights/emerging-topics` - Emerging product areas

#### Data Management
- `GET /api/data/stats` - Database statistics
- `GET /api/data/batches` - List import batches
- `POST /api/data/import` - Import analyzed CSV
- `GET /api/data/tickets` - Query tickets with filters
- `DELETE /api/data/batches/{id}` - Delete a batch

#### Analysis Jobs
- `POST /api/analysis/start` - Start new analysis (upload CSV)
- `GET /api/analysis/{job_id}/status` - Check job progress
- `DELETE /api/analysis/{job_id}` - Cancel running job

#### Talk to Data
- `POST /api/talk/question` - Ask a question about data
- `WebSocket /api/talk/ws` - Real-time conversation

#### Settings
- `GET /api/settings/api-key/status` - Check API key status
- `POST /api/settings/api-key` - Save API key
- `DELETE /api/settings/api-key` - Remove stored API key

### Integration with Existing Code

The web backend does not duplicate any analysis logic. Instead, it imports and wraps the existing Python modules:

```python
# Example: web/backend/api/routes/analytics.py
from analytics_engine import get_analytics_engine

@router.get("/summary")
async def get_summary(start_date: date = None, end_date: date = None):
    engine = get_analytics_engine()
    return engine.get_summary_stats(start_date, end_date)
```

This ensures:
- **Single source of truth** - Same analysis logic for both GUI and web
- **Shared database** - Both interfaces read/write to the same SQLite database
- **Consistent results** - Identical analytics and insights across interfaces

---

## Data Flow

```
┌──────────────────┐
│  Zendesk Export  │
│    (CSV file)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│  Data Cleanup    │────▶│  Main Analysis   │
│(support-data-    │     │    Engine        │
│  cleanup.py)     │     │                  │
└──────────────────┘     └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Enriched CSV    │
                         │  (with AI        │
                         │   analysis)      │
                         └────────┬─────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  CSAT Trends     │     │  Topic           │     │  Product         │
│  Analysis        │     │  Aggregation     │     │  Feedback        │
└──────────────────┘     └──────────────────┘     └──────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  SQLite Database │
                         │  (Historical     │
                         │   Storage)       │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Insights &      │
                         │  Dashboards      │
                         └──────────────────┘
```

---

## AI Analysis Output Schema

Each ticket is analyzed and the following fields are extracted:

| Field | Type | Description |
|-------|------|-------------|
| `DETAIL_SUMMARY` | string | Short summary of the interaction |
| `CUSTOMER_GOAL` | string | Customer's main goal using action verb (e.g., "Import subscribers to WordPress.com") |
| `SENTIMENT_ANALYSIS` | enum | `Positive`, `Neutral`, or `Negative` |
| `WHAT_HAPPENED` | string | Comprehensive hypothesis explaining the user's rating/experience |
| `ISSUE_RESOLVED` | boolean | Whether the issue was resolved |
| `INTERACTION_TOPICS` | string | Comma-separated list of topics discussed |
| `PRODUCT_FEEDBACK` | string | Feedback summary with customer quotes, or `NONE` |
| `RELATED_TO_PRODUCT` | boolean | Whether sentiment relates to product issues |
| `RELATED_TO_SERVICE` | boolean | Whether sentiment relates to support service |
| `AI_FEEDBACK` | boolean | Whether customer provided feedback about AI assistant |
| `MAIN_TOPIC` | string | Categorized topic from predefined list |
| `PRODUCT_AREA` | enum | Primary product area (Domains, Email, Themes, Plugins, Billing, Plans, Editor, Media, SEO, Security, Performance, Migration, Support, Account, AI Features, Mobile, Other) |
| `FEATURE_REQUESTS` | array | List of specific feature requests mentioned |
| `PAIN_POINTS` | array | List of frustrations expressed by customer |

### Main Topic Categories

- Account
- Creating & editing the site
- Domains
- Downtime
- Email issues
- Error on their site
- General billing
- General plan questions
- Hosting
- Integrations
- Jetpack issues
- Monetization
- Plan Cancelation/refund request
- Plan Downgrade request
- Plan Upgrade request
- Plugin support
- Presales opportunity
- Site performance issues
- Theme support
- WooCommerce-related
- SEO
- Security
- Other

---

## Database Schema

### Tables

#### `analysis_batches`
Metadata about each CSV import.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| import_date | DATETIME | When the batch was imported |
| source_file | VARCHAR(500) | Original CSV filename |
| period_start | DATE | Earliest ticket date in batch |
| period_end | DATE | Latest ticket date in batch |
| total_tickets | INTEGER | Total rows in CSV |
| new_tickets | INTEGER | Tickets not seen before |
| duplicate_tickets | INTEGER | Tickets already in DB |
| notes | TEXT | Optional notes |

#### `ticket_analyses`
Individual ticket analysis results.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| batch_id | INTEGER | Foreign key to analysis_batches |
| ticket_id | VARCHAR(100) | Zendesk ticket ID or URL |
| ticket_hash | VARCHAR(64) | SHA256 hash for deduplication |
| created_date | DATE | Ticket creation date |
| csat_rating | VARCHAR(20) | 'good', 'bad', or null |
| sentiment | VARCHAR(20) | 'Positive', 'Neutral', 'Negative' |
| issue_resolved | BOOLEAN | Resolution status |
| main_topic | VARCHAR(200) | Categorized topic |
| product_area | VARCHAR(100) | Product area classification |
| feature_requests | TEXT | JSON array of feature requests |
| pain_points | TEXT | JSON array of pain points |
| ... | ... | (additional analysis fields) |

#### `trend_snapshots`
Pre-computed aggregations for fast trending.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| batch_id | INTEGER | Foreign key to analysis_batches |
| period_date | DATE | Date this snapshot represents |
| metric_type | VARCHAR(50) | 'topic', 'sentiment', 'resolution_rate', etc. |
| metric_key | VARCHAR(200) | Specific value (e.g., topic name) |
| metric_value | FLOAT | Percentage or rate |
| ticket_count | INTEGER | Absolute count |

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes* | OpenAI API key (starts with `sk-proj-...`) |

*Not required if using `--local` flag for local AI server.

### Settings Location

- **macOS**: `~/Library/Application Support/AI Support Analyzer/settings.json`
- **Windows**: `%APPDATA%/AI Support Analyzer/settings.json`
- **Linux**: `~/.config/AI Support Analyzer/settings.json`

### Default Settings

```json
{
  "version": "1.0",
  "ui_preferences": {
    "limit": "No limit",
    "analysis_options": {
      "main_analysis": true,
      "data_cleanup": true,
      "predict_csat": true,
      "topic_aggregator": true,
      "csat_trends": true,
      "product_feedback": true,
      "goals_trends": true,
      "custom_analysis": false,
      "visualization": false
    }
  },
  "advanced_settings": {
    "api_timeout": 60,
    "max_retries": 3,
    "batch_size": 100,
    "concurrent_threads": 50
  }
}
```

---

## Usage Guide

### Desktop GUI Mode

1. **Launch** the application (double-click `AI Support Analyzer.app`)
2. **Enter API key** (stored securely in macOS Keychain)
3. **Select CSV file** using Browse button
4. **Choose analyses** to run (all selected by default)
5. **Click "Start Analysis"** and monitor progress

### Web UI Mode

1. **Start the backend**: `cd web/backend && uvicorn main:app --port 8000`
2. **Start the frontend**: `cd web/frontend && npm run dev`
3. **Open browser** to `http://localhost:5173`
4. **Configure API key** in Settings page (first time only)
5. **Use the dashboard** to view analytics and insights
6. **Upload files** in the Analyze page to run new analyses
7. **Explore data** with filters or use Talk to Data for natural language queries

### Command Line Mode

```bash
# Main analysis
python main-analysis-process.py -file="path/to/input.csv"

# With local AI server
python main-analysis-process.py -file="path/to/input.csv" --local

# With custom thread count
python main-analysis-process.py -file="path/to/input.csv" --threads=25

# CSAT prediction
python predict_csat.py -file="path/to/analysis_output.csv"

# Topic aggregation
python topic-aggregator.py -file="path/to/analysis_output.csv"

# CSAT trends analysis
python csat-trends.py -file="path/to/analysis_output.csv" -limit=1000
```

### Required CSV Columns

| Column | Description |
|--------|-------------|
| `Created Date` | Ticket creation timestamp |
| `Interaction Message Body` or `Ticket Message Body` | Full conversation text |
| `CSAT Rating` | Customer satisfaction rating (good/bad) |
| `CSAT Reason` | Reason for rating |
| `CSAT Comment` | Customer's comment |
| `Tags` | Zendesk tags (used for filtering and sentiment detection) |

---

## File Reference

| File | Description |
|------|-------------|
| `gui_app.py` | Main GUI application (3000+ lines) |
| `main-analysis-process.py` | Core AI analysis engine |
| `predict_csat.py` | CSAT prediction and accuracy analysis |
| `csat-trends.py` | CSAT trends and patterns analysis |
| `topic-aggregator.py` | AI-powered topic categorization |
| `goals-trends.py` | Customer goal analysis |
| `product-feedback-trends.py` | Product feedback trend analysis |
| `talktodata.py` | Natural language data querying |
| `analytics_engine.py` | Historical trend analysis |
| `insights_engine.py` | Automated anomaly detection |
| `data_store.py` | SQLite storage interface |
| `models.py` | SQLAlchemy ORM models |
| `utils.py` | Shared utilities module |
| `support-data-cleanup.py` | Data cleaning and filtering |
| `support-data-precleanup.py` | Pre-processing cleanup |
| `custom-analysis.py` | Custom analysis templates |
| `visualize-overall-sentiment.py` | Sentiment visualization |
| `aggregate-daily-reports.py` | Daily report aggregation |
| `orchestrator.py` | Multi-script orchestration |

### Build Files

| File | Description |
|------|-------------|
| `build_executable.py` | PyInstaller build script |
| `wordpress_support_analyzer.spec` | PyInstaller spec file |
| `build.sh` | Unix build script |
| `build.bat` | Windows build script |
| `verify_build.py` | Build verification |

### Web UI Files

| File/Directory | Description |
|----------------|-------------|
| `web/backend/main.py` | FastAPI application entry point |
| `web/backend/api/routes/` | API route handlers (analytics, insights, data, etc.) |
| `web/backend/core/config.py` | Application settings and configuration |
| `web/backend/core/security.py` | API key management and validation |
| `web/backend/schemas/` | Pydantic models for request/response validation |
| `web/backend/services/analysis_runner.py` | Background job manager for analyses |
| `web/backend/services/talk_service.py` | Natural language querying service |
| `web/frontend/src/pages/` | React page components (Dashboard, Analyze, etc.) |
| `web/frontend/src/components/` | Reusable UI components |
| `web/frontend/src/api/client.ts` | TypeScript API client |
| `web/frontend/src/hooks/` | Custom React hooks for data fetching |
| `web/requirements.txt` | Python dependencies for web backend |

---

## Performance Considerations

- **Concurrent processing**: Default 50 threads for API calls
- **Rate limiting**: 100 requests/second for OpenAI API
- **Memory management**: Garbage collection during batch processing
- **Progress saving**: Every 50 completions to prevent data loss
- **Context length handling**: Automatic retry with reduced data on context overflow

---

## Future Development

Areas for potential enhancement:

- [x] Dashboard web interface (implemented in `web/`)
- [ ] Real-time Zendesk integration
- [ ] Custom AI model fine-tuning
- [ ] Multi-language support
- [ ] Advanced visualization exports
- [ ] Team collaboration features
- [ ] Packaged web app (standalone .app with embedded server)

---

*Documentation generated from codebase analysis. Last updated: January 2026*
