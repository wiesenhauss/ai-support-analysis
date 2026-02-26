# AI Support Analyzer

> **An AI-powered customer support analysis tool that transforms support ticket data into actionable insights**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![OpenAI API](https://img.shields.io/badge/OpenAI-GPT--4.1-green.svg)](https://platform.openai.com/)
[![License](https://img.shields.io/badge/license-Automattic-orange.svg)](https://automattic.com/)

Built for Automattic Inc. (makers of WordPress.com, Jetpack, WooCommerce, and more) to analyze customer support interactions and extract meaningful patterns, sentiment, and product feedback.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [User Interfaces](#user-interfaces)
- [Features in Detail](#features-in-detail)
- [Data Requirements](#data-requirements)
- [Configuration](#configuration)
- [Use Cases](#use-cases)
- [Architecture](#architecture)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Support](#support)

---

## 🎯 Overview

**AI Support Analyzer** uses OpenAI's GPT-4.1-mini to automatically analyze customer support tickets, extracting:

- **Sentiment** (Positive, Neutral, Negative)
- **Topics and product areas** mentioned
- **Customer goals** (what they're trying to achieve)
- **Resolution status** (did we solve the issue?)
- **Product feedback** (feature requests, pain points)
- **CSAT predictions** (predict satisfaction before surveys)
- **Trends and anomalies** over time

The tool processes thousands of tickets concurrently (50 threads), generates structured JSON outputs, and stores results in a SQLite database for historical trend analysis.

### Problem It Solves

| Challenge | Solution |
|-----------|----------|
| **Manual ticket analysis is slow** | AI processes thousands of tickets concurrently |
| **Inconsistent categorization** | Structured JSON schema ensures consistent outputs |
| **Understanding CSAT drivers** | AI analyzes conversations to identify root causes |
| **Detecting trends early** | Automated anomaly detection surfaces emerging issues |
| **Extracting product feedback** | AI mines interactions for feature requests and pain points |
| **Predicting satisfaction** | Sentiment analysis predicts CSAT before surveys |

---

## ✨ Key Features

### 🤖 AI-Powered Analysis
- **Automated Ticket Analysis** - Extract sentiment, topics, goals, and resolution status from support conversations
- **Custom Per-Ticket Analysis** - Define your own AI analyses with custom prompts and result types
- **CSAT Prediction** - Predict customer satisfaction based on interaction sentiment
- **Natural Language Querying** - Ask questions about your data in plain English ("Talk to Data")

### 📊 Analytics & Insights
- **Trend Detection** - Identify emerging issues and sentiment shifts over time
- **Anomaly Detection** - Automatically flag unusual patterns in metrics
- **Product Feedback Mining** - Extract feature requests and pain points
- **Historical Analytics** - Track changes week-over-week and month-over-month

### 🖥️ Multiple Interfaces
- **Desktop GUI** - Beautiful native application (macOS .app bundle)
- **Web Interface** - Modern React-based web UI with interactive dashboards
- **Command Line** - Scriptable for automation and batch processing

### 🔒 Security & Data Management
- **Secure API Key Storage** - macOS Keychain integration for API keys
- **Local Database** - SQLite database with automatic deduplication
- **Export/Import** - Share analysis history between team members
- **No Permanent External Storage** - Your data stays on your machine

---

## 🚀 How It Works

```
┌─────────────────────┐
│  Zendesk CSV Export │
│   (Support Tickets) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Data Cleanup      │  ← Validate and filter data
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   AI Analysis       │  ← GPT-4.1-mini analyzes each ticket
│   (50 concurrent    │     Extracts sentiment, topics, goals
│    API threads)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Enriched CSV       │  ← Original data + AI insights
│  + Analysis Results │
└──────────┬──────────┘
           │
           ├──────────────────────┬──────────────────────┐
           ▼                      ▼                      ▼
    ┌──────────┐         ┌──────────────┐      ┌──────────────┐
    │  CSAT    │         │   Topic      │      │   Product    │
    │  Trends  │         │ Aggregation  │      │   Feedback   │
    └──────────┘         └──────────────┘      └──────────────┘
           │                      │                      │
           └──────────────────────┼──────────────────────┘
                                  ▼
                         ┌──────────────┐
                         │  SQLite DB   │  ← Historical storage
                         │  + Insights  │     Trend analysis
                         └──────────────┘
```

### Processing Steps

1. **Import** - Load CSV file with support ticket data
2. **Cleanup** - Validate, filter, and prepare data
3. **AI Analysis** - Process tickets concurrently through GPT-4.1-mini
4. **Enrichment** - Add sentiment, topics, goals, and more to each ticket
5. **Aggregation** - Generate topic trends, CSAT analysis, product feedback
6. **Storage** - Save to SQLite database for historical tracking
7. **Insights** - Generate anomaly detection and trend comparisons

---

## 📦 Installation

### Prerequisites

- **Python 3.12+** ([Download](https://www.python.org/downloads/))
- **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))
- **Node.js 18+** (only for Web UI) ([Download](https://nodejs.org/))

### Clone the Repository

```bash
git clone https://github.com/Automattic/ai-support-analysis.git
cd ai-support-analysis
```

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### For Web UI (Optional)

```bash
cd web/frontend
npm install
cd ../..
```

---

## 🎬 Quick Start

### Option 1: Desktop GUI (Easiest)

1. **Run the application:**
   ```bash
   python gui_app.py
   ```

2. **Enter your OpenAI API key** (stored securely in macOS Keychain)

3. **Select your CSV file** with support ticket data

4. **Choose analyses** to run (all selected by default)

5. **Click "Start Analysis"** and monitor progress

> **Tip:** The Desktop GUI also has an **"Open Web UI"** button that launches the full Web UI in your browser with a single click — no need to start servers manually.

### Option 2: Web UI (Best for Teams)

**Quick launch from Desktop GUI:** Click the **"Open Web UI"** button — it starts the backend server automatically and opens your browser.

**Manual launch (for development):**

1. **Start the backend:**
   ```bash
   cd web/backend
   uvicorn main:app --reload --port 8000
   ```

2. **Start the frontend** (in a new terminal):
   ```bash
   cd web/frontend
   npm run dev
   ```

3. **Open browser** to `http://localhost:5173`

4. **Configure API key** in Settings (first time only)

### Option 3: Command Line (Best for Automation)

```bash
# Set your API key
export OPENAI_API_KEY="sk-proj-your-key-here"

# Run the full pipeline with the orchestrator (recommended)
python orchestrator.py -file="data/support-tickets.csv"

# Or run individual stages manually
python main-analysis-process.py -file="data/support-tickets.csv"
python predict_csat.py -file="support-analysis-output_*.csv"
python topic-aggregator.py -file="support-analysis-output-predictive-csat_*.csv"
python csat-trends.py -file="support-analysis-output-predictive-csat_*.csv"
```

---

## 🖥️ User Interfaces

### Desktop GUI

<details>
<summary><b>Features</b></summary>

- 🔐 **Secure API Key Management** - macOS Keychain integration
- 📁 **File Selection** - Drag & drop support
- ⚙️ **Module Selection** - Choose which analyses to run
- 📊 **Real-time Progress** - Live progress bars and log display
- 🛑 **Cancel Support** - Stop analysis anytime (with force stop option)
- 💾 **Settings Persistence** - Remember your preferences
- 📤 **Export/Import** - Share analysis history with team members
- 🔧 **Custom Analyses** - Define your own per-ticket AI analyses
- 🌐 **One-Click Web UI** - Launch the Web UI directly from the desktop app
- 🔄 **CSV Column Mapping** - Map non-standard CSV columns to expected names via dropdown selectors

</details>

<details>
<summary><b>Usage</b></summary>

```bash
# Run the GUI
python gui_app.py

# Or use the macOS app bundle (if built)
open "dist/AI Support Analyzer.app"
```

The GUI provides:
- Visual file selection and validation
- Checkbox selection for analysis modules
- Real-time log output with auto-scroll
- Progress indicators for each stage
- Automatic output folder opening on completion

</details>

### Web Interface

<details>
<summary><b>Features</b></summary>

- 📊 **Dashboard** - Key metrics, sentiment trends, topic charts, critical alerts
- 📤 **Analyze** - Upload CSV files, configure options, monitor progress
- 🔍 **Explore** - Search and filter tickets with advanced filtering
- 💡 **Insights** - AI-generated insights, anomaly detection, recommendations
- 💬 **Talk to Data** - Chat interface for natural language queries
- ⚙️ **Settings** - API key configuration, database management, import history
- 🔄 **CSV Column Mapping** - Map non-standard CSV columns with fuzzy matching suggestions
- 💾 **Auto-Import to History** - Automatically import analysis results into the database (enabled by default)

</details>

<details>
<summary><b>Pages</b></summary>

| Page | Path | Description |
|------|------|-------------|
| Dashboard | `/` | Overview with metrics and trends |
| Analyze | `/analyze` | Upload and analyze CSV files |
| Explore | `/explore` | Search and filter tickets |
| Insights | `/insights` | AI-generated insights and anomalies |
| Talk | `/talk` | Natural language data queries |
| Settings | `/settings` | Configuration and management |

</details>

<details>
<summary><b>API Endpoints</b></summary>

**Analysis**
```
POST /api/analysis/validate-columns      - Validate & fuzzy-match CSV columns
POST /api/analysis/start                 - Start new analysis (with column mapping & auto-import options)
GET  /api/analysis/{job_id}/status       - Poll job status
GET  /api/analysis/{job_id}/logs         - Stream job logs
GET  /api/analysis/{job_id}/files        - List output files
GET  /api/analysis/{job_id}/files/{name} - Download an output file
DELETE /api/analysis/{job_id}            - Cancel a running job
GET  /api/analysis/                      - List all jobs
```

**Analytics**
```
GET  /api/analytics/summary              - Summary statistics
GET  /api/analytics/sentiment-distribution - Sentiment breakdown
GET  /api/analytics/sentiment-trend      - Sentiment over time
GET  /api/analytics/topic-distribution   - Topic breakdown
GET  /api/analytics/topic-trend          - Topic changes over time
GET  /api/analytics/csat-distribution    - CSAT score distribution
GET  /api/analytics/csat-trend           - CSAT over time
GET  /api/analytics/resolution-rate      - Resolution rate
GET  /api/analytics/resolution-trend     - Resolution rate over time
GET  /api/analytics/compare-periods      - Compare two time periods
```

**Data**
```
GET  /api/data/stats                     - Database statistics
GET  /api/data/batches                   - List import batches
DELETE /api/data/batches/{batch_id}      - Delete a batch
POST /api/data/import                    - Import analyzed CSV
GET  /api/data/tickets                   - Search/filter tickets
GET  /api/data/date-range                - Available date range
GET  /api/data/topics                    - List all topics
GET  /api/data/product-areas             - List all product areas
GET  /api/data/export-database           - Export full database
POST /api/data/import-database           - Import database backup
```

**Insights**
```
GET  /api/insights/weekly                - Week-over-week insights
GET  /api/insights/monthly               - Month-over-month insights
GET  /api/insights/emerging-topics       - Emerging product insights
POST /api/insights/compare               - Compare custom periods
GET  /api/insights/anomalies             - Detected anomalies
```

**Talk to Data**
```
POST /api/talk/question                  - Ask a natural language question
GET  /api/talk/columns                   - Available data columns
POST /api/talk/reset                     - Reset conversation context
```

**Settings**
```
GET  /api/settings/                      - Current settings
GET  /api/settings/api-key/status        - API key status
POST /api/settings/api-key               - Set API key
DELETE /api/settings/api-key             - Remove API key
POST /api/settings/api-key/validate      - Validate an API key
GET  /api/settings/custom-ticket-analyses - List custom analyses
POST /api/settings/custom-ticket-analyses - Create custom analysis
DELETE /api/settings/custom-ticket-analyses/{name} - Delete custom analysis
GET  /api/settings/custom-prompts        - List custom prompts
POST /api/settings/custom-prompts/{name} - Create/update custom prompt
DELETE /api/settings/custom-prompts/{name} - Delete custom prompt
GET  /api/settings/advanced              - Advanced settings
POST /api/settings/advanced              - Update advanced settings
```

Full interactive API documentation available at `http://localhost:8000/api/docs` (Swagger UI).

</details>

---

## 🎯 Features in Detail

### 1. Main Ticket Analysis

**What it does:** Analyzes each support ticket to extract structured insights

**Outputs:**

| Field | Type | Description |
|-------|------|-------------|
| `DETAIL_SUMMARY` | string | Short summary of the interaction |
| `CUSTOMER_GOAL` | string | What the customer is trying to achieve |
| `SENTIMENT_ANALYSIS` | enum | Positive, Neutral, or Negative |
| `WHAT_HAPPENED` | string | Hypothesis explaining the customer's experience |
| `ISSUE_RESOLVED` | boolean | Whether the issue was resolved |
| `INTERACTION_TOPICS` | string | Comma-separated list of topics discussed |
| `PRODUCT_FEEDBACK` | string | Feature requests, pain points, or NONE |
| `MAIN_TOPIC` | string | Primary categorized topic |
| `PRODUCT_AREA` | enum | Domains, Email, Themes, Plugins, Billing, etc. |
| `FEATURE_REQUESTS` | array | Specific features requested |
| `PAIN_POINTS` | array | Customer frustrations |

**Example:**
```json
{
  "CUSTOMER_GOAL": "Import email subscribers to WordPress.com",
  "SENTIMENT_ANALYSIS": "Negative",
  "WHAT_HAPPENED": "Customer struggled with CSV import format...",
  "ISSUE_RESOLVED": true,
  "MAIN_TOPIC": "Email issues",
  "PRODUCT_AREA": "Email",
  "FEATURE_REQUESTS": ["Better CSV import validation"],
  "PAIN_POINTS": ["Unclear error messages", "No format examples"]
}
```

### 2. Custom Per-Ticket Analysis

**What it does:** Define your own AI analyses with custom prompts

**Use Cases:**
- Identify refund requests: `CUSTOM_IS_REFUND_REQUEST` (boolean)
- Detect escalation needs: `CUSTOM_NEEDS_ESCALATION` (boolean)
- Classify urgency: `CUSTOM_URGENCY_LEVEL` (string: low/medium/high)
- Extract customer mood: `CUSTOM_CUSTOMER_MOOD` (string)

**Configuration Example:**
```json
{
  "custom_ticket_analyses": [
    {
      "name": "IS_REFUND_REQUEST",
      "prompt": "Determine if this ticket is a refund or cancellation request.",
      "result_type": "boolean",
      "columns": ["Interaction Message Body", "CSAT Comment"]
    },
    {
      "name": "URGENCY_LEVEL",
      "prompt": "Rate urgency as: low, medium, high, or critical.",
      "result_type": "string",
      "columns": ["Interaction Message Body", "CSAT Rating"]
    }
  ]
}
```

### 3. CSAT Prediction

**What it does:** Predict customer satisfaction based on sentiment analysis

**How it works:**
- Compares initial sentiment (from tags) with final sentiment (from AI analysis)
- Tracks sentiment changes during interactions
- Calculates prediction accuracy against actual CSAT scores

**Outputs:**
- `PREDICTED_CSAT`: Predicted satisfaction rating
- `SENTIMENT_CHANGE`: Initial → Final sentiment progression
- `ACCURACY_SCORE`: How well prediction matches actual CSAT

### 4. Talk to Data

**What it does:** Ask questions about your data in natural language

**Example Questions:**
- "What are the main factors affecting customer satisfaction?"
- "Which product areas have the lowest CSAT scores and why?"
- "What are the top feature requests from customers?"
- "How have support metrics changed over the past quarter?"

**How it works:**
1. AI analyzes your question to understand intent
2. Automatically selects relevant data columns
3. Samples data if needed (handles up to 5,000 rows)
4. Generates comprehensive analysis with:
   - Executive summary
   - Detailed insights
   - Key metrics and percentages
   - Actionable recommendations

### 5. Trend Analysis

**What it does:** Track metrics over time and detect anomalies

**Analyses:**
- **CSAT Trends** - Satisfaction scores and drivers over time
- **Topic Trends** - Emerging issues and declining topics
- **Sentiment Trends** - Mood changes across product areas
- **Goals Trends** - What customers are trying to accomplish
- **Product Feedback Trends** - Feature requests and pain points

**Anomaly Detection:**
- Automatically flags unusual spikes or drops in metrics
- Compares week-over-week and month-over-month
- Identifies emerging topics (new issues gaining traction)
- Highlights critical changes requiring attention

### 6. Product Feedback Mining

**What it does:** Extract and categorize product feedback

**Extracts:**
- **Feature Requests** - Specific features customers want
- **Pain Points** - Frustrations and obstacles
- **Product Issues** - Bugs, performance problems, UX issues
- **Competitive Mentions** - References to competitor features

**Outputs:**
- Aggregated feedback by product area
- Frequency of each feature request
- Sentiment associated with each pain point
- Trends in feedback over time

---

## 📊 Data Requirements

### Required CSV Columns

Your CSV file should include these columns:

| Column | Description | Example |
|--------|-------------|---------|
| `Created Date` | Ticket creation timestamp | `2024-01-15 10:30:00` |
| `Interaction Message Body` | Full conversation text | (support conversation) |

### Optional CSV Columns

These columns enhance the analysis but are not required. If they are missing, the tool will proceed gracefully and report which analyses will have limited data (e.g., CSAT trend reports are skipped when CSAT columns are absent).

| Column | Purpose | Impact When Missing |
|--------|---------|---------------------|
| `CSAT Rating` | Customer satisfaction rating | CSAT trends and prediction unavailable |
| `CSAT Reason` | Reason for rating | CSAT driver analysis limited |
| `CSAT Comment` | Customer's comment | Comment-based insights unavailable |
| `Tags` | Zendesk tags | Tag-based sentiment comparison unavailable |
| `Ticket ID` | Unique identifier | Deduplication uses row hash instead |
| `Assignee` | Support agent name | Per-agent breakdown unavailable |
| `Group` | Support team | Per-team breakdown unavailable |
| `Priority` | Ticket priority | Priority-based filtering unavailable |
| `Channel` | Contact method (email, chat) | Channel breakdown unavailable |

### CSV Column Mapping

If your CSV uses different column names (e.g., `Date Created` instead of `Created Date`), the tool can map them automatically:

- **Desktop GUI** - A mapping panel with dropdown selectors appears when column names don't match. Required columns must be mapped before analysis can start.
- **Web UI** - The `ColumnMappingCard` component uses fuzzy matching to suggest mappings and lets you confirm or adjust them.
- **CLI** - Pass a JSON mapping via the `--column-mapping` argument to `main-analysis-process.py`.

Both interfaces validate columns on file load and show which mappings are required vs. optional.

### Data Export

**From Zendesk:**
1. Go to Explore (Analytics) → Create Report
2. Select tickets with required columns
3. Export as CSV
4. Load into AI Support Analyzer

---

## ⚙️ Configuration

### API Key Setup

**Desktop GUI:**
- Enter API key in the application
- Stored securely in macOS Keychain (service: `AI Support Analyzer`, account: `openai-api-key`)

**Web UI:**
- Configure in Settings page
- Stored in `~/.ai_support_analyzer/web_settings.json`

**Command Line:**
```bash
export OPENAI_API_KEY="sk-proj-your-key-here"
```

### Settings Location

- **macOS**: `~/Library/Application Support/AI Support Analyzer/settings.json`
- **Windows**: `%APPDATA%/AI Support Analyzer/settings.json`
- **Linux**: `~/.config/AI Support Analyzer/settings.json`

### Advanced Settings

```json
{
  "advanced_settings": {
    "api_timeout": 60,
    "max_retries": 3,
    "batch_size": 100,
    "concurrent_threads": 50
  }
}
```

### Database Location

Default: `~/.ai_support_analyzer/analytics.db`

Contains:
- `analysis_batches` - Import metadata
- `ticket_analyses` - Individual ticket results
- `trend_snapshots` - Pre-computed aggregations

---

## 💼 Use Cases

### Support Team Leaders

**Challenge:** "I need to understand why our CSAT scores dropped last month"

**Solution:**
1. Import last month's tickets into AI Support Analyzer
2. Run CSAT Trends analysis
3. Use Talk to Data: "What caused the drop in CSAT scores last month?"
4. Review anomaly detection for specific issues
5. Get actionable recommendations

### Product Managers

**Challenge:** "What features are customers requesting most?"

**Solution:**
1. Analyze recent support tickets
2. Review Product Feedback Trends report
3. Use Talk to Data: "What are the top 10 feature requests?"
4. Filter by product area to prioritize roadmap
5. Track trends over time to validate demand

### Support Agents

**Challenge:** "I want to see examples of how other agents resolved similar issues"

**Solution:**
1. Use Explore page to search tickets
2. Filter by topic and "Issue Resolved = true"
3. Review successful resolution patterns
4. Use Talk to Data: "What approaches worked best for billing issues?"

### Data Analysts

**Challenge:** "I need to track support metrics and report on trends"

**Solution:**
1. Set up automated weekly analysis via command line
2. Use Historical Analytics to track week-over-week changes
3. Export insights to share with leadership
4. Build custom analyses for specific metrics

---

## 🏗️ Architecture

### Technology Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.12+ |
| **AI/ML** | OpenAI API (GPT-4.1-mini, GPT-4.1) |
| **Data Processing** | Pandas, NumPy |
| **Database** | SQLAlchemy + SQLite |
| **Desktop GUI** | Tkinter (cross-platform) |
| **Web Backend** | FastAPI, Uvicorn |
| **Web Frontend** | React 18, TypeScript, Tailwind CSS |
| **Visualization** | Matplotlib, Seaborn, Plotly, Recharts |
| **Distribution** | PyInstaller (macOS .app) |

### Core Components

```
ai-support-analysis/
├── gui_app.py                      # Desktop GUI application
├── orchestrator.py                 # CLI pipeline orchestrator (runs all stages in sequence)
├── main-analysis-process.py        # Core AI analysis engine
├── custom_ticket_analysis.py       # Custom per-ticket analyses
├── predict_csat.py                 # CSAT prediction
├── csat-trends.py                  # CSAT trend analysis
├── topic-aggregator.py             # Topic categorization
├── talktodata.py                   # Natural language queries
├── analytics_engine.py             # Historical analytics
├── insights_engine.py              # Anomaly detection
├── data_store.py                   # SQLite database interface
├── models.py                       # SQLAlchemy models
├── utils.py                        # Shared utilities
├── web/
│   ├── backend/                    # FastAPI backend
│   │   ├── main.py                # App entry point (also serves built frontend)
│   │   ├── api/routes/            # API endpoints
│   │   ├── core/                  # Configuration
│   │   ├── schemas/               # Pydantic models
│   │   └── services/              # Business logic
│   └── frontend/                   # React frontend
│       ├── src/
│       │   ├── pages/             # Dashboard, Analyze, etc.
│       │   ├── components/        # Reusable UI components
│       │   └── api/               # API client
│       └── dist/                  # Production build
└── requirements.txt                # Python dependencies
```

### Data Flow

1. **Input** - CSV file with support tickets
2. **Validation** - Check required columns, data types
3. **Cleanup** - Filter, deduplicate, prepare for AI
4. **Parallel Processing** - 50 concurrent API calls to OpenAI
5. **Structured Outputs** - JSON schema ensures consistency
6. **Enrichment** - Add AI insights to original data
7. **Aggregation** - Generate topic trends, CSAT analysis
8. **Storage** - Save to SQLite with deduplication
9. **Analytics** - Generate insights and anomalies
10. **Visualization** - Dashboard charts and reports

---

## 📚 Documentation

### Detailed Guides

- **[DOCUMENTATION.md](DOCUMENTATION.md)** - Complete technical documentation
- **[TALK_TO_DATA_README.md](TALK_TO_DATA_README.md)** - Talk to Data feature guide
- **[BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)** - Build native applications
- **[web/README.md](web/README.md)** - Web UI setup and API reference

### Quick References

- **[requirements.txt](requirements.txt)** - Python dependencies
- **[web/requirements.txt](web/requirements.txt)** - Web-specific dependencies
- **[version.json](version.json)** - Current version info

---

## 🚢 Building & Distribution

### Build Desktop Application (macOS)

```bash
# Build macOS .app bundle
python build_executable.py

# Or use the shell script
./build.sh

# Output: dist/AI Support Analyzer.app
```

### Build Web Application

```bash
# Build frontend for production
cd web/frontend
npm run build

# Frontend bundle: web/frontend/dist/

# Deploy backend with:
cd web/backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 🤝 Contributing

This project is maintained by Automattic for internal use. If you're an Automattician:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone the repo
git clone https://github.com/Automattic/ai-support-analysis.git
cd ai-support-analysis

# Install dependencies
pip install -r requirements.txt

# For web development
cd web/frontend
npm install

# Run tests (if available)
python -m pytest tests/
```

---

## 🐛 Support

### Getting Help

- **Issues** - For bugs and feature requests, open an issue on GitHub
- **Questions** - Ask in #support-tools Slack channel (Automattic)
- **Documentation** - Check [DOCUMENTATION.md](DOCUMENTATION.md) for technical details

### Common Issues

<details>
<summary><b>API Key Not Working</b></summary>

**Problem:** "Invalid API key" error

**Solution:**
- Verify your key starts with `sk-proj-`
- Check that the key is active at https://platform.openai.com/api-keys
- Ensure the key has sufficient credits
- Re-enter the key in Settings

</details>

<details>
<summary><b>Analysis Running Slowly</b></summary>

**Problem:** Analysis takes a long time

**Solution:**
- Reduce concurrent threads if you hit rate limits (default: 50)
- Process smaller batches (use record limit in GUI)
- Check your internet connection
- Verify OpenAI API status at https://status.openai.com/

</details>

<details>
<summary><b>CSV Import Errors</b></summary>

**Problem:** "Missing required columns" error

**Solution:**
- Use the **column mapping** feature to map your CSV columns to the expected names (see [CSV Column Mapping](#csv-column-mapping))
- Only `Created Date` and `Interaction Message Body` are strictly required; all other columns are optional
- If optional columns are missing, a confirmation dialog lists which reports will have limited data
- Ensure data is properly formatted (dates, text encoding)
- Try opening CSV in Excel to verify structure

</details>

<details>
<summary><b>Web UI Won't Start</b></summary>

**Problem:** Backend or frontend fails to start

**Solution:**
- Backend: Check Python version is 3.12+, install dependencies
- Frontend: Check Node.js version is 18+, run `npm install`
- Port conflicts: Ensure ports 8000 and 5173 are available
- Check error logs for specific issues

</details>

---

## 📝 License

Copyright © 2024-2026 Automattic Inc.

This software is proprietary and confidential. Unauthorized copying, distribution, or modification is prohibited.

For licensing inquiries, contact Automattic Legal.

---

## 👏 Acknowledgments

**Created by:** [@wiesenhauss](https://github.com/wiesenhauss) for Automattic Inc.

**Built with:**
- [OpenAI API](https://platform.openai.com/) - AI analysis
- [FastAPI](https://fastapi.tiangolo.com/) - Web backend
- [React](https://react.dev/) - Web frontend
- [Pandas](https://pandas.pydata.org/) - Data processing
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM

**Special thanks to:**
- Automattic Support Team for feedback and testing
- OpenAI for GPT-4.1 capabilities
- The open-source community for excellent tools

---

## 🗺️ Roadmap

### Current Version: 12.x

**Completed:**
- ✅ Desktop GUI with macOS Keychain integration
- ✅ Web interface with interactive dashboards
- ✅ Custom per-ticket analysis feature
- ✅ Talk to Data natural language queries
- ✅ Historical analytics and trend detection
- ✅ Anomaly detection and insights engine
- ✅ Export/import database functionality
- ✅ One-click Web UI launch from Desktop GUI
- ✅ Auto-import to database for Web UI
- ✅ CSV column mapping with fuzzy matching (Web UI & Desktop GUI)
- ✅ Graceful handling of missing optional CSV columns

**Planned:**
- [ ] Real-time Zendesk integration (API sync)
- [ ] Custom AI model fine-tuning
- [ ] Multi-language support (Spanish, French, etc.)
- [ ] Team collaboration features
- [ ] Advanced visualization exports (PowerPoint, PDF)
- [ ] Scheduled automated reports
- [ ] Mobile-responsive improvements
- [ ] Packaged web app (standalone .app with embedded server)

---

## 📊 Performance

- **Processing Speed** - 50 concurrent threads process ~100-200 tickets/minute
- **API Efficiency** - Structured outputs reduce token usage by ~30%
- **Database** - SQLite handles millions of tickets with sub-second queries
- **Memory** - Garbage collection keeps memory usage under 500MB
- **Scalability** - Tested with datasets up to 100,000 tickets

---

## 🔐 Privacy & Security

- ✅ **API keys stored securely** (macOS Keychain)
- ✅ **Local database only** (no external storage)
- ✅ **OpenAI DPA compliant** (Data Processing Agreement)
- ✅ **No PII sent to AI** (configurable column selection)
- ✅ **SSL/TLS for API calls** (encrypted in transit)
- ✅ **Export/import with validation** (prevent data corruption)

---

**Questions? Issues? Feedback?** Open an issue or contact [@wiesenhauss](https://github.com/wiesenhauss)

---

<div align="center">

[Documentation](DOCUMENTATION.md) • [Web UI Guide](web/README.md) • [Talk to Data](TALK_TO_DATA_README.md) • [Build Guide](BUILD_INSTRUCTIONS.md)

</div>
