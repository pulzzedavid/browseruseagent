"""
Agent state and session models
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AgentSession(Base):
    """Agent session model"""
    __tablename__ = "agent_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    task = Column(Text, nullable=False)
    initial_url = Column(String(500), nullable=True)
    status = Column(String(50), default="running", nullable=False)  # running, completed, failed, paused
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    actions = relationship("AgentAction", back_populates="session", cascade="all, delete-orphan")
    observations = relationship("AgentObservation", back_populates="session", cascade="all, delete-orphan")
    memory = relationship("AgentMemory", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgentSession(id={self.id}, task='{self.task[:50]}...', status='{self.status}')>"


class AgentAction(Base):
    """Agent action model"""
    __tablename__ = "agent_actions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("agent_sessions.id"), nullable=False)
    action_type = Column(String(100), nullable=False)  # click, type, scroll, navigate, etc.
    action_data = Column(JSON, nullable=False)  # Action-specific parameters
    target_element = Column(Text, nullable=True)  # Element selector or description
    coordinates = Column(JSON, nullable=True)  # x, y coordinates if applicable
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    success = Column(Boolean, nullable=True)  # Whether action succeeded
    error_message = Column(Text, nullable=True)  # Error details if failed
    execution_time_ms = Column(Integer, nullable=True)  # How long action took
    
    # Relationships
    session = relationship("AgentSession", back_populates="actions")
    
    def __repr__(self):
        return f"<AgentAction(id={self.id}, type='{self.action_type}', success={self.success})>"


class AgentObservation(Base):
    """Agent observation model"""
    __tablename__ = "agent_observations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("agent_sessions.id"), nullable=False)
    observation_type = Column(String(100), nullable=False)  # dom, screenshot, url_change, etc.
    observation_data = Column(JSON, nullable=False)  # Observation content
    url = Column(String(500), nullable=True)  # Current URL when observation was made
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    observation_metadata = Column(JSON, nullable=True)  # Additional metadata (renamed from 'metadata')
    
    # Relationships
    session = relationship("AgentSession", back_populates="observations")
    
    def __repr__(self):
        return f"<AgentObservation(id={self.id}, type='{self.observation_type}')>"


class AgentMemory(Base):
    """Agent memory model for storing context and learning"""
    __tablename__ = "agent_memory"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("agent_sessions.id"), nullable=False)
    memory_type = Column(String(100), nullable=False)  # context, learning, pattern, etc.
    key = Column(String(255), nullable=False)  # Memory key
    value = Column(JSON, nullable=False)  # Memory value
    importance = Column(Integer, default=1, nullable=False)  # Memory importance (1-10)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    access_count = Column(Integer, default=1, nullable=False)
    
    # Relationships
    session = relationship("AgentSession", back_populates="memory")
    
    def __repr__(self):
        return f"<AgentMemory(id={self.id}, key='{self.key}', type='{self.memory_type}')>"


class AgentTool(Base):
    """Agent tool model for managing available tools"""
    __tablename__ = "agent_tools"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    tool_type = Column(String(100), nullable=False)  # browser, system, custom
    parameters_schema = Column(JSON, nullable=True)  # JSON schema for tool parameters
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<AgentTool(id={self.id}, name='{self.name}', type='{self.tool_type}')>"
