"""
Agent API routes for the Browser Use Agent
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from pydantic import BaseModel, Field

from app.services.agent_service import AgentService
from app.services.tool_service import ToolService

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class StartSessionRequest(BaseModel):
    task: str = Field(..., description="The task to accomplish", min_length=1)
    initial_url: Optional[str] = Field(None, description="Initial URL to navigate to")


class StartSessionResponse(BaseModel):
    success: bool
    session_id: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class SessionStatusResponse(BaseModel):
    success: bool
    session_id: str
    status: str
    task: str
    created_at: str
    updated_at: str
    error: Optional[str] = None


class UpdateTaskRequest(BaseModel):
    new_task: str = Field(..., description="New task description", min_length=1)


class UpdateTaskResponse(BaseModel):
    success: bool
    session_id: str
    new_task: str
    message: str
    error: Optional[str] = None


class SessionHistoryResponse(BaseModel):
    success: bool
    session_id: str
    task: str
    status: str
    created_at: str
    updated_at: str
    message: str
    error: Optional[str] = None


class ActiveSessionsResponse(BaseModel):
    success: bool
    sessions: list
    total_count: int
    error: Optional[str] = None


# Dependency to get agent service
async def get_agent_service(request: Request) -> AgentService:
    """Get the agent service instance from app state"""
    return request.app.state.agent_service


@router.post("/start", response_model=StartSessionResponse)
async def start_agent_session(
    request: StartSessionRequest,
    background_tasks: BackgroundTasks,
    agent_service: AgentService = Depends(get_agent_service)
):
    """Start a new agent session"""
    try:
        logger.info(f"Starting agent session for task: {request.task[:50]}...")
        
        result = await agent_service.start_session(
            task=request.task,
            initial_url=request.initial_url
        )
        
        if result["success"]:
            return StartSessionResponse(
                success=True,
                session_id=result["session_id"],
                status=result["status"],
                message=result["message"]
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        logger.error(f"Failed to start agent session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    agent_service: AgentService = Depends(get_agent_service)
):
    """Get the status of an agent session"""
    try:
        result = await agent_service.get_session_status(session_id)
        
        if result["success"]:
            return SessionStatusResponse(
                success=True,
                session_id=result["session_id"],
                status=result["status"],
                task=result["task"],
                created_at=result["created_at"],
                updated_at=result["updated_at"]
            )
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/stop", response_model=StartSessionResponse)
async def stop_agent_session(
    session_id: str,
    agent_service: AgentService = Depends(get_agent_service)
):
    """Stop an agent session"""
    try:
        logger.info(f"Stopping agent session: {session_id}")
        
        result = await agent_service.stop_session(session_id)
        
        if result["success"]:
            return StartSessionResponse(
                success=True,
                session_id=result["session_id"],
                status=result["status"],
                message=result["message"]
            )
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop agent session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}/task", response_model=UpdateTaskResponse)
async def update_session_task(
    session_id: str,
    request: UpdateTaskRequest,
    agent_service: AgentService = Depends(get_agent_service)
):
    """Update the task for an existing session"""
    try:
        logger.info(f"Updating task for session {session_id}: {request.new_task[:50]}...")
        
        result = await agent_service.update_session_task(session_id, request.new_task)
        
        if result["success"]:
            return UpdateTaskResponse(
                success=True,
                session_id=result["session_id"],
                new_task=result["new_task"],
                message=result["message"]
            )
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str,
    agent_service: AgentService = Depends(get_agent_service)
):
    """Get the action and observation history for a session"""
    try:
        result = await agent_service.get_session_history(session_id)
        
        if result["success"]:
            return SessionHistoryResponse(
                success=True,
                session_id=result["session_id"],
                task=result["task"],
                status=result["status"],
                created_at=result["created_at"],
                updated_at=result["updated_at"],
                message=result["message"]
            )
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/active", response_model=ActiveSessionsResponse)
async def get_active_sessions(
    agent_service: AgentService = Depends(get_agent_service)
):
    """Get list of all active sessions"""
    try:
        sessions = agent_service.get_active_sessions()
        
        return ActiveSessionsResponse(
            success=True,
            sessions=sessions,
            total_count=len(sessions)
        )
        
    except Exception as e:
        logger.error(f"Failed to get active sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    agent_service: AgentService = Depends(get_agent_service)
):
    """Delete an agent session"""
    try:
        logger.info(f"Deleting agent session: {session_id}")
        
        # First stop the session if it's running
        await agent_service.stop_session(session_id)
        
        # Here you would also delete from database
        # For now, just return success
        
        return {
            "success": True,
            "message": f"Session {session_id} deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to delete agent session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume/{session_id}")
async def resume_agent_session(session_id: str):
    """Resume agent execution after human intervention"""
    try:
        agent_service = get_agent_service()
        result = await agent_service.resume_after_human_intervention(session_id)
        return result
    except Exception as e:
        logger.error(f"Failed to resume agent session: {e}")
        return {"success": False, "error": str(e)}
