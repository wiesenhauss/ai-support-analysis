"""
Talk to Data API routes.
Provides endpoints for natural language data querying.
"""

import sys
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web.backend.schemas.data import TalkToDataQuestion, TalkToDataResponse
from web.backend.api.deps import get_data_store_dep, require_api_key
from web.backend.services.talk_service import TalkToDataService, get_talk_service

router = APIRouter()


@router.post("/question", response_model=TalkToDataResponse)
async def ask_question(
    request: TalkToDataQuestion,
    api_key: str = Depends(require_api_key),
    data_store=Depends(get_data_store_dep)
):
    """
    Ask a question about the data.
    
    Uses AI to analyze the data and answer questions in natural language.
    """
    try:
        service = get_talk_service(api_key, data_store)
        
        result = await service.ask_question(
            question=request.question,
            columns=request.columns,
            is_follow_up=request.is_follow_up
        )
        
        return TalkToDataResponse(
            answer=result["answer"],
            selected_columns=result.get("selected_columns", []),
            token_count=result.get("token_count", 0),
            conversation_id=result.get("conversation_id")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@router.get("/columns")
async def get_available_columns(
    data_store=Depends(get_data_store_dep)
):
    """Get list of available columns for querying."""
    try:
        df = data_store.get_tickets_dataframe(limit=1)
        if df.empty:
            return {"columns": []}
        
        return {"columns": list(df.columns)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_conversation():
    """Reset the conversation history."""
    try:
        # Get global service instance and reset
        from web.backend.services.talk_service import _talk_service_instance
        if _talk_service_instance:
            _talk_service_instance.reset_conversation()
        return {"message": "Conversation reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws")
async def talk_websocket(
    websocket: WebSocket,
    api_key: Optional[str] = None
):
    """
    WebSocket endpoint for streaming Talk to Data responses.
    
    Allows real-time conversation with streaming AI responses.
    """
    await websocket.accept()
    
    try:
        # Get API key from query params or first message
        if not api_key:
            # Expect first message to be auth
            data = await websocket.receive_json()
            api_key = data.get("api_key")
            
            if not api_key:
                await websocket.send_json({
                    "type": "error",
                    "message": "API key required"
                })
                await websocket.close()
                return
        
        # Get data store
        from web.backend.api.deps import get_data_store_dep
        data_store = get_data_store_dep()
        
        # Initialize service
        service = get_talk_service(api_key, data_store)
        
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Talk to Data"
        })
        
        while True:
            # Receive question
            data = await websocket.receive_json()
            
            if data.get("type") == "question":
                question = data.get("question", "")
                columns = data.get("columns")
                is_follow_up = data.get("is_follow_up", False)
                
                # Send thinking indicator
                await websocket.send_json({
                    "type": "thinking",
                    "message": "Analyzing your question..."
                })
                
                try:
                    # Get answer (streaming not implemented in basic version)
                    result = await service.ask_question(
                        question=question,
                        columns=columns,
                        is_follow_up=is_follow_up
                    )
                    
                    # Send complete response
                    await websocket.send_json({
                        "type": "answer",
                        "answer": result["answer"],
                        "selected_columns": result.get("selected_columns", []),
                        "token_count": result.get("token_count", 0)
                    })
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
            
            elif data.get("type") == "reset":
                service.reset_conversation()
                await websocket.send_json({
                    "type": "reset",
                    "message": "Conversation reset"
                })
            
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
