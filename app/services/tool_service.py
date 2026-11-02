"""
Tool management service for the Browser Use Agent
"""

import logging
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass
from datetime import datetime

from app.core.config import settings
from app.models.agent import AgentTool
from app.tools.browser_tools import BrowserTools
from app.tools.system_tools import SystemTools
from app.tools.custom_tools import CustomTools

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Tool definition structure"""
    name: str
    description: str
    tool_type: str
    function: Callable
    parameters_schema: Optional[Dict[str, Any]] = None
    is_active: bool = True


class ToolService:
    """Service for managing and executing agent tools"""
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self.browser_tools: Optional[BrowserTools] = None
        self.system_tools: Optional[SystemTools] = None
        self.custom_tools: Optional[CustomTools] = None
        
    async def initialize(self, browser_tools: Optional[BrowserTools] = None):
        """Initialize all tool categories"""
        try:
            # Debug logging
            logger.info(f"Tool service initialize called with browser_tools: {browser_tools}")
            logger.info(f"browser_tools type: {type(browser_tools)}")
            
            # Use shared browser tools if provided, otherwise create new instance
            if browser_tools:
                self.browser_tools = browser_tools
                logger.info("Tool service using shared browser tools")
            else:
                self.browser_tools = BrowserTools()
                logger.info("Tool service created new browser tools instance")
            
            self._register_browser_tools()
            
            # Initialize system tools
            self.system_tools = SystemTools()
            await self.system_tools.initialize()
            self._register_system_tools()
            
            # Initialize custom tools
            self.custom_tools = CustomTools()
            await self.custom_tools.initialize()
            self._register_custom_tools()
            
            logger.info(f"Tool service initialized with {len(self.tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize tool service: {e}")
            raise
    
    def _register_browser_tools(self):
        """Register browser automation tools"""
        if not self.browser_tools:
            return
            
        browser_tool_definitions = [
            ToolDefinition(
                name="navigate",
                description="Navigate to a specific URL",
                tool_type="browser",
                function=self.browser_tools.navigate,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to navigate to"}
                    },
                    "required": ["url"]
                }
            ),
            ToolDefinition(
                name="click",
                description="Click on an element using selector or coordinates",
                tool_type="browser",
                function=self.browser_tools.click,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector or XPath"},
                        "coordinates": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "integer"},
                                "y": {"type": "integer"}
                            }
                        }
                    },
                    "required": ["selector"]
                }
            ),
            ToolDefinition(
                name="type_text",
                description="Type text into an input field",
                tool_type="browser",
                function=self.browser_tools.type_text,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector or XPath"},
                        "text": {"type": "string", "description": "Text to type"}
                    },
                    "required": ["selector", "text"]
                }
            ),
            ToolDefinition(
                name="scroll",
                description="Scroll the page or element",
                tool_type="browser",
                function=self.browser_tools.scroll,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                        "amount": {"type": "integer", "description": "Scroll amount in pixels"},
                        "selector": {"type": "string", "description": "Element selector to scroll"}
                    },
                    "required": ["direction"]
                }
            ),
            ToolDefinition(
                name="wait_for_element",
                description="Wait for an element to appear",
                tool_type="browser",
                function=self.browser_tools.wait_for_element,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector or XPath"},
                        "timeout": {"type": "integer", "description": "Timeout in milliseconds"}
                    },
                    "required": ["selector"]
                }
            ),
            ToolDefinition(
                name="find_element_with_scroll",
                description="Find an element by scrolling down if needed",
                tool_type="browser",
                function=self.browser_tools.find_element_with_scroll,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector or XPath"},
                        "max_scroll_attempts": {"type": "integer", "description": "Maximum scroll attempts"}
                    },
                    "required": ["selector"]
                }
            ),
            ToolDefinition(
                name="get_page_info",
                description="Get current page information (URL, title, DOM)",
                tool_type="browser",
                function=self.browser_tools.get_page_info,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "include_dom": {"type": "boolean", "description": "Include DOM information"},
                        "include_screenshot": {"type": "boolean", "description": "Include screenshot"}
                    }
                }
            ),
            ToolDefinition(
                name="clear_cookies",
                description="Clear all saved cookies and browser cookies",
                tool_type="browser",
                function=self.browser_tools.clear_cookies,
                parameters_schema={}
            ),
            ToolDefinition(
                name="get_cookies",
                description="Get current cookies from browser",
                tool_type="browser",
                function=self.browser_tools.get_cookies,
                parameters_schema={}
            ),
            ToolDefinition(
                name="is_authenticated",
                description="Check if user is authenticated by looking for authentication cookies",
                tool_type="browser",
                function=self.browser_tools.is_authenticated,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Domain to check authentication for"}
                    }
                }
            )
        ]
        
        for tool_def in browser_tool_definitions:
            self.tools[tool_def.name] = tool_def
    
    def _register_system_tools(self):
        """Register system interaction tools"""
        if not self.system_tools:
            return
            
        system_tool_definitions = [
            ToolDefinition(
                name="file_operation",
                description="Perform file system operations",
                tool_type="system",
                function=self.system_tools.file_operation,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string", "enum": ["read", "write", "delete", "list"]},
                        "path": {"type": "string", "description": "File or directory path"},
                        "content": {"type": "string", "description": "Content for write operations"}
                    },
                    "required": ["operation", "path"]
                }
            ),
            ToolDefinition(
                name="system_command",
                description="Execute system commands",
                tool_type="system",
                function=self.system_tools.system_command,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "System command to execute"},
                        "timeout": {"type": "number", "description": "Command timeout in seconds"}
                    },
                    "required": ["command"]
                }
            )
        ]
        
        for tool_def in system_tool_definitions:
            self.tools[tool_def.name] = tool_def
    
    def _register_custom_tools(self):
        """Register custom automation tools"""
        if not self.custom_tools:
            return
            
        custom_tool_definitions = [
            ToolDefinition(
                name="custom_action",
                description="Execute a custom automation action",
                tool_type="custom",
                function=self.custom_tools.custom_action,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "action_name": {"type": "string", "description": "Name of custom action"},
                        "parameters": {"type": "object", "description": "Action parameters"}
                    },
                    "required": ["action_name"]
                }
            ),
            ToolDefinition(
                name="human_intervention_required",
                description="Pause agent execution and wait for human intervention",
                tool_type="control",
                function=self._handle_human_intervention,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string", "description": "Reason for human intervention"},
                        "message": {"type": "string", "description": "Message to display to user"},
                        "action": {"type": "string", "description": "Type of action required"},
                        "resume_after": {"type": "string", "description": "Condition to resume after"}
                    },
                    "required": ["reason", "message", "action", "resume_after"]
                }
            )
        ]
        
        for tool_def in custom_tool_definitions:
            self.tools[tool_def.name] = tool_def
    
    def _handle_human_intervention(self, reason: str, message: str, action: str, resume_after: str) -> Dict[str, Any]:
        """Handle human intervention requirement"""
        logger.info(f"Human intervention required: {reason}")
        logger.info(f"Message: {message}")
        logger.info(f"Action: {action}")
        logger.info(f"Resume after: {resume_after}")
        
        return {
            "success": True,
            "status": "paused_for_human_intervention",
            "reason": reason,
            "message": message,
            "action": action,
            "resume_after": resume_after,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get a tool by name"""
        return self.tools.get(tool_name)
    
    def get_all_tools(self) -> List[ToolDefinition]:
        """Get all available tools"""
        return list(self.tools.values())
    
    def get_tools_by_type(self, tool_type: str) -> List[ToolDefinition]:
        """Get tools by type"""
        return [tool for tool in self.tools.values() if tool.tool_type == tool_type]
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool with given parameters"""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        if not tool.is_active:
            raise ValueError(f"Tool '{tool_name}' is not active")
        
        try:
            logger.info(f"Executing tool '{tool_name}' with parameters: {kwargs}")
            result = tool.function(**kwargs)
            
            # Check if the function is async and await it if needed
            import asyncio
            if asyncio.iscoroutine(result):
                result = await result
                
            logger.info(f"Tool '{tool_name}' executed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Tool '{tool_name}' execution failed: {e}")
            raise
    
    def register_custom_tool(self, name: str, description: str, function: Callable, 
                           parameters_schema: Optional[Dict[str, Any]] = None):
        """Register a custom tool at runtime"""
        if name in self.tools:
            logger.warning(f"Tool '{name}' already exists, overwriting")
        
        custom_tool = ToolDefinition(
            name=name,
            description=description,
            tool_type="custom",
            function=function,
            parameters_schema=parameters_schema
        )
        
        self.tools[name] = custom_tool
        logger.info(f"Custom tool '{name}' registered successfully")
    
    def unregister_tool(self, tool_name: str):
        """Unregister a tool"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"Tool '{tool_name}' unregistered successfully")
        else:
            logger.warning(f"Tool '{tool_name}' not found for unregistration")
    
    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """Get tools in format suitable for LLM consumption"""
        llm_tools = []
        
        for tool in self.tools.values():
            if not tool.is_active:
                continue
                
            llm_tool = {
                "name": tool.name,
                "description": tool.description,
                "type": tool.tool_type,
                "parameters_schema": tool.parameters_schema or {}
            }
            llm_tools.append(llm_tool)
        
        return llm_tools
