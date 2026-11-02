"""
Browser interaction models
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class BrowserSession(Base):
    """Browser session model"""
    __tablename__ = "browser_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    browser_type = Column(String(50), nullable=False)  # chromium, firefox, webkit
    user_agent = Column(String(500), nullable=True)
    viewport_width = Column(Integer, nullable=True)
    viewport_height = Column(Integer, nullable=True)
    is_headless = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    pages = relationship("BrowserPage", back_populates="browser_session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BrowserSession(id={self.id}, type='{self.browser_type}', active={self.is_active})>"


class BrowserPage(Base):
    """Browser page model"""
    __tablename__ = "browser_pages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    browser_session_id = Column(UUID(as_uuid=True), ForeignKey("browser_sessions.id"), nullable=False)
    page_id = Column(String(255), nullable=False)  # Playwright page ID
    url = Column(String(500), nullable=True)
    title = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    browser_session = relationship("BrowserSession", back_populates="pages")
    elements = relationship("PageElement", back_populates="page", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BrowserPage(id={self.id}, url='{self.url}', active={self.is_active})>"


class PageElement(Base):
    """Page element model for tracking DOM elements"""
    __tablename__ = "page_elements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(UUID(as_uuid=True), ForeignKey("browser_pages.id"), nullable=False)
    element_selector = Column(String(500), nullable=False)  # CSS selector, XPath, etc.
    element_type = Column(String(100), nullable=True)  # button, input, link, etc.
    text_content = Column(Text, nullable=True)
    attributes = Column(JSON, nullable=True)  # Element attributes
    position = Column(JSON, nullable=True)  # x, y coordinates
    size = Column(JSON, nullable=True)  # width, height
    is_visible = Column(Boolean, default=True, nullable=False)
    is_interactive = Column(Boolean, default=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    page = relationship("BrowserPage", back_populates="elements")
    
    def __repr__(self):
        return f"<PageElement(id={self.id}, selector='{self.element_selector}', type='{self.element_type}')>"


class BrowserAction(Base):
    """Browser action model for tracking browser interactions"""
    __tablename__ = "browser_actions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(UUID(as_uuid=True), ForeignKey("browser_pages.id"), nullable=False)
    action_type = Column(String(100), nullable=False)  # click, type, scroll, navigate, etc.
    target_element = Column(String(500), nullable=True)  # Element selector
    action_data = Column(JSON, nullable=False)  # Action parameters
    coordinates = Column(JSON, nullable=True)  # x, y coordinates
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    
    # Relationships
    page = relationship("BrowserPage")
    
    def __repr__(self):
        return f"<BrowserAction(id={self.id}, type='{self.action_type}', success={self.success})>"


class BrowserState(Base):
    """Browser state snapshot model"""
    __tablename__ = "browser_states"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(UUID(as_uuid=True), ForeignKey("browser_pages.id"), nullable=False)
    url = Column(String(500), nullable=False)
    title = Column(String(500), nullable=True)
    dom_snapshot = Column(Text, nullable=True)  # Simplified DOM representation
    screenshot_path = Column(String(500), nullable=True)  # Path to screenshot file
    scroll_position = Column(JSON, nullable=True)  # x, y scroll coordinates
    viewport_size = Column(JSON, nullable=True)  # width, height
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    page = relationship("BrowserPage")
    
    def __repr__(self):
        return f"<BrowserState(id={self.id}, url='{self.url}', timestamp={self.timestamp})>"
