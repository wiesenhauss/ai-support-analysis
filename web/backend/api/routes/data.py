"""
Data Management API routes.
Provides endpoints for importing, querying, and managing data.
"""

import sys
import os
from pathlib import Path
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Form

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web.backend.schemas.data import (
    BatchInfo, BatchListResponse, ImportResult, TicketInfo,
    TicketListResponse, DatabaseStats
)
from web.backend.api.deps import get_data_store_dep
from web.backend.core.config import get_settings

router = APIRouter()


@router.get("/stats", response_model=DatabaseStats)
async def get_database_stats(
    data_store=Depends(get_data_store_dep)
):
    """Get overall database statistics."""
    try:
        stats = data_store.get_database_stats()
        return DatabaseStats(
            total_tickets=stats.get("total_tickets", 0),
            total_batches=stats.get("total_batches", 0),
            date_range_start=stats.get("date_range_start"),
            date_range_end=stats.get("date_range_end"),
            sentiment_distribution=stats.get("sentiment_distribution", {}),
            resolution_rate=stats.get("resolution_rate", 0.0),
            db_path=stats.get("db_path", ""),
            db_size_mb=stats.get("db_size_mb", 0.0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches", response_model=BatchListResponse)
async def list_batches(
    data_store=Depends(get_data_store_dep)
):
    """List all import batches."""
    try:
        batches = data_store.get_all_batches()
        return BatchListResponse(
            batches=[BatchInfo(**b) for b in batches],
            total_count=len(batches)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/batches/{batch_id}")
async def delete_batch(
    batch_id: int,
    data_store=Depends(get_data_store_dep)
):
    """Delete a batch and all associated tickets."""
    try:
        success = data_store.delete_batch(batch_id)
        if not success:
            raise HTTPException(status_code=404, detail="Batch not found")
        return {"message": f"Batch {batch_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import", response_model=ImportResult)
async def import_csv(
    file: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    data_store=Depends(get_data_store_dep)
):
    """
    Import an analyzed CSV file into the database.
    
    The CSV should contain analysis results from main-analysis-process.py.
    """
    settings = get_settings()
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Create upload directory
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded file
    file_path = upload_dir / file.filename
    try:
        content = await file.read()
        
        # Check file size
        size_mb = len(content) / (1024 * 1024)
        if size_mb > settings.max_upload_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB"
            )
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Import into database
        result = data_store.import_csv(str(file_path), notes)
        
        return ImportResult(
            batch_id=result["batch_id"],
            total_rows=result["total_rows"],
            imported=result["imported"],
            duplicates=result["duplicates"],
            period_start=result.get("period_start"),
            period_end=result.get("period_end")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    finally:
        # Clean up uploaded file
        if file_path.exists():
            os.remove(file_path)


@router.get("/tickets", response_model=TicketListResponse)
async def list_tickets(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    sentiment: Optional[str] = Query(None),
    csat_rating: Optional[str] = Query(None),
    main_topic: Optional[str] = Query(None),
    product_area: Optional[str] = Query(None),
    issue_resolved: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    data_store=Depends(get_data_store_dep)
):
    """
    Query tickets with filters.
    
    Supports filtering by date range, sentiment, CSAT rating, topic,
    product area, and resolution status.
    """
    try:
        # Get tickets as DataFrame for flexible filtering
        df = data_store.get_tickets_dataframe(start_date, end_date)
        
        if df.empty:
            return TicketListResponse(
                tickets=[],
                total_count=0,
                page=page,
                page_size=page_size
            )
        
        # Apply filters
        if sentiment:
            df = df[df['sentiment'] == sentiment]
        
        if csat_rating:
            df = df[df['csat_rating'].str.lower() == csat_rating.lower()]
        
        if main_topic:
            df = df[df['main_topic'].str.contains(main_topic, case=False, na=False)]
        
        if product_area:
            df = df[df.get('product_area', '') == product_area]
        
        if issue_resolved is not None:
            df = df[df['issue_resolved'] == issue_resolved]
        
        if search:
            # Search in summary and goal
            mask = (
                df['detail_summary'].str.contains(search, case=False, na=False) |
                df['customer_goal'].str.contains(search, case=False, na=False)
            )
            df = df[mask]
        
        # Get total count before pagination
        total_count = len(df)
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        df_page = df.iloc[start_idx:end_idx]
        
        # Convert to response
        tickets = []
        for _, row in df_page.iterrows():
            tickets.append(TicketInfo(
                id=int(row['id']),
                ticket_id=row.get('ticket_id'),
                created_date=row.get('created_date'),
                csat_rating=row.get('csat_rating'),
                sentiment=row.get('sentiment'),
                issue_resolved=row.get('issue_resolved'),
                main_topic=row.get('main_topic'),
                customer_goal=row.get('customer_goal'),
                detail_summary=row.get('detail_summary'),
                product_area=row.get('product_area') if 'product_area' in row else None
            ))
        
        return TicketListResponse(
            tickets=tickets,
            total_count=total_count,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/date-range")
async def get_date_range(
    data_store=Depends(get_data_store_dep)
):
    """Get the date range of all tickets in the database."""
    try:
        min_date, max_date = data_store.get_date_range()
        return {
            "min_date": str(min_date) if min_date else None,
            "max_date": str(max_date) if max_date else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics")
async def get_unique_topics(
    data_store=Depends(get_data_store_dep)
):
    """Get list of unique topics in the database."""
    try:
        df = data_store.get_tickets_dataframe()
        if df.empty:
            return {"topics": []}
        
        topics = df['main_topic'].dropna().unique().tolist()
        # Clean up topics (take primary topic from comma-separated)
        unique_topics = set()
        for topic in topics:
            primary = topic.split(',')[0].strip()
            if primary:
                unique_topics.add(primary)
        
        return {"topics": sorted(list(unique_topics))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/product-areas")
async def get_product_areas(
    data_store=Depends(get_data_store_dep)
):
    """Get list of unique product areas in the database."""
    try:
        df = data_store.get_tickets_dataframe()
        if df.empty or 'product_area' not in df.columns:
            return {"product_areas": []}
        
        areas = df['product_area'].dropna().unique().tolist()
        return {"product_areas": sorted(areas)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
