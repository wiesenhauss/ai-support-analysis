# AI Support Analyzer - Web UI

A modern web interface for the AI Support Analyzer, built with FastAPI (Python backend) and React (TypeScript frontend).

## Features

- **Dashboard**: View key metrics, sentiment trends, topic distribution, and critical insights at a glance
- **Analyze**: Upload CSV files and run AI-powered analysis with real-time progress tracking
- **Explore**: Search and filter tickets with advanced filtering options
- **Insights**: View AI-generated insights, anomaly detection, and trend comparisons
- **Talk to Data**: Ask questions about your data in natural language
- **Settings**: Manage database, view import history, and configure the application

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- OpenAI API key

### 1. Install Backend Dependencies

```bash
cd web
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd web/frontend
npm install
```

### 3. Set Environment Variables

Create a `.env` file in the project root or set the environment variable:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 4. Run the Backend

```bash
cd web/backend
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000` with docs at `http://localhost:8000/api/docs`.

### 5. Run the Frontend

In a new terminal:

```bash
cd web/frontend
npm run dev
```

The frontend will be available at `http://localhost:5173`.

## Architecture

```
web/
├── backend/                 # FastAPI backend
│   ├── api/
│   │   ├── routes/         # API route handlers
│   │   │   ├── analytics.py
│   │   │   ├── analysis.py
│   │   │   ├── data.py
│   │   │   ├── insights.py
│   │   │   └── talk.py
│   │   └── deps.py         # Dependencies
│   ├── core/
│   │   ├── config.py       # Settings
│   │   └── security.py     # API key management
│   ├── schemas/            # Pydantic models
│   ├── services/           # Business logic
│   │   ├── analysis_runner.py
│   │   └── talk_service.py
│   └── main.py             # FastAPI app
│
├── frontend/               # React frontend
│   ├── src/
│   │   ├── api/           # API client
│   │   ├── components/    # Reusable components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── pages/         # Page components
│   │   └── lib/           # Utilities
│   └── ...
│
└── requirements.txt        # Python dependencies
```

## API Endpoints

### Analytics
- `GET /api/analytics/summary` - Get summary statistics
- `GET /api/analytics/sentiment-trend` - Get sentiment over time
- `GET /api/analytics/topic-distribution` - Get topic breakdown
- `GET /api/analytics/csat-trend` - Get CSAT trend
- `GET /api/analytics/compare-periods` - Compare two time periods

### Insights
- `GET /api/insights/weekly` - Week-over-week insights
- `GET /api/insights/monthly` - Month-over-month insights
- `GET /api/insights/anomalies` - Detected anomalies
- `GET /api/insights/emerging-topics` - Emerging product areas

### Data Management
- `GET /api/data/stats` - Database statistics
- `GET /api/data/batches` - List import batches
- `POST /api/data/import` - Import analyzed CSV
- `GET /api/data/tickets` - Query tickets

### Analysis
- `POST /api/analysis/start` - Start new analysis job
- `GET /api/analysis/{job_id}/status` - Get job status
- `DELETE /api/analysis/{job_id}` - Cancel job

### Talk to Data
- `POST /api/talk/question` - Ask a question
- `WebSocket /api/talk/ws` - Real-time conversation

## Development

### Backend

```bash
# Run with auto-reload
uvicorn web.backend.main:app --reload --port 8000

# View API docs
open http://localhost:8000/api/docs
```

### Frontend

```bash
# Development server
npm run dev

# Build for production
npm run build

# Type check
npm run lint
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `DEBUG` | Enable debug mode | `false` |
| `MAX_UPLOAD_SIZE_MB` | Max file upload size | `100` |
| `CORS_ORIGINS` | Allowed CORS origins | `localhost:5173` |

### Settings File

The backend loads settings from environment variables and `.env` file. See `web/backend/core/config.py` for all options.

## Tech Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **Pydantic** - Data validation
- **SQLAlchemy** - Database ORM (uses existing SQLite DB)
- **OpenAI** - AI analysis and Talk to Data

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Recharts** - Charts and visualizations
- **Lucide React** - Icons

## Integration with Existing Code

The web backend imports and uses the existing Python modules directly:
- `analytics_engine.py` - Historical trend analysis
- `insights_engine.py` - Anomaly detection
- `data_store.py` - SQLite database interface
- `main-analysis-process.py` - Analysis job runner

No changes to the existing code are required. The web UI provides an alternative interface alongside the desktop GUI.
