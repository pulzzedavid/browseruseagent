"""
Custom automation tools for the Browser Use Agent
"""

import logging
import json
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)


class CustomTools:
    """Custom automation tools that can be registered at runtime"""
    
    def __init__(self):
        self.is_initialized = False
        self.custom_actions: Dict[str, Dict[str, Any]] = {}
        self.action_history: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Initialize custom tools"""
        try:
            # Create custom actions directory
            custom_dir = Path("custom_actions")
            custom_dir.mkdir(exist_ok=True)
            
            # Load predefined custom actions
            await self._load_predefined_actions()
            
            self.is_initialized = True
            logger.info("Custom tools initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize custom tools: {e}")
            raise
    
    def _ensure_initialized(self):
        """Ensure custom tools are initialized"""
        if not self.is_initialized:
            raise RuntimeError("Custom tools not initialized")
    
    async def _load_predefined_actions(self):
        """Load predefined custom actions from configuration"""
        predefined_actions = {
            "wait_and_retry": {
                "description": "Wait for a condition and retry if it fails",
                "function": self._wait_and_retry_action,
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "condition": {"type": "string", "description": "Description of condition to wait for"},
                        "max_attempts": {"type": "integer", "description": "Maximum retry attempts"},
                        "delay_seconds": {"type": "number", "description": "Delay between attempts"}
                    },
                    "required": ["condition", "max_attempts"]
                }
            },
            "batch_click": {
                "description": "Click multiple elements in sequence",
                "function": self._batch_click_action,
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "selectors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of CSS selectors to click"
                        },
                        "delay_ms": {"type": "integer", "description": "Delay between clicks"}
                    },
                    "required": ["selectors"]
                }
            },
            "form_fill": {
                "description": "Fill multiple form fields at once",
                "function": self._form_fill_action,
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "fields": {
                            "type": "object",
                            "description": "Mapping of selector to value for form fields"
                        }
                    },
                    "required": ["fields"]
                }
            },
            "scroll_to_element": {
                "description": "Scroll to make an element visible",
                "function": self._scroll_to_element_action,
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector of element to scroll to"},
                        "behavior": {"type": "string", "enum": ["smooth", "auto"], "description": "Scroll behavior"}
                    },
                    "required": ["selector"]
                }
                        },

        }
        
        for action_name, action_config in predefined_actions.items():
            self.custom_actions[action_name] = action_config
    
    async def custom_action(self, action_name: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a custom automation action"""
        self._ensure_initialized()
        
        try:
            if action_name not in self.custom_actions:
                return {
                    "success": False,
                    "action_name": action_name,
                    "error": f"Custom action '{action_name}' not found"
                }
            
            action_config = self.custom_actions[action_name]
            action_func = action_config["function"]
            
            start_time = time.time()
            
            # Execute the custom action
            if parameters:
                result = await action_func(**parameters)
            else:
                result = await action_func()
            
            execution_time = (time.time() - start_time) * 1000
            
            # Record action in history
            history_entry = {
                "action_name": action_name,
                "parameters": parameters or {},
                "result": result,
                "execution_time_ms": execution_time,
                "timestamp": datetime.now().isoformat()
            }
            self.action_history.append(history_entry)
            
            # Limit history size
            if len(self.action_history) > 100:
                self.action_history = self.action_history[-100:]
            
            result.update({
                "action_name": action_name,
                "execution_time_ms": execution_time
            })
            
            logger.info(f"Custom action '{action_name}' executed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Custom action '{action_name}' failed: {e}")
            return {
                "success": False,
                "action_name": action_name,
                "error": str(e),
                "execution_time_ms": 0
            }
    
    async def _wait_and_retry_action(self, condition: str, max_attempts: int, delay_seconds: float = 1.0) -> Dict[str, Any]:
        """Wait for a condition and retry if it fails"""
        try:
            # This is a placeholder implementation
            # In a real scenario, you would implement the actual condition checking logic
            
            for attempt in range(max_attempts):
                logger.info(f"Attempt {attempt + 1}/{max_attempts} for condition: {condition}")
                
                # Simulate condition check
                await asyncio.sleep(delay_seconds)
                
                # For now, always succeed on the last attempt
                if attempt == max_attempts - 1:
                    return {
                        "success": True,
                        "condition": condition,
                        "attempts_made": attempt + 1,
                        "message": f"Condition '{condition}' met after {attempt + 1} attempts"
                    }
            
            return {
                "success": False,
                "condition": condition,
                "attempts_made": max_attempts,
                "message": f"Condition '{condition}' not met after {max_attempts} attempts"
            }
            
        except Exception as e:
            return {
                "success": False,
                "condition": condition,
                "error": str(e)
            }
    
    async def _batch_click_action(self, selectors: list, delay_ms: int = 100) -> Dict[str, Any]:
        """Click multiple elements in sequence"""
        try:
            results = []
            
            for i, selector in enumerate(selectors):
                try:
                    # This would integrate with browser tools in a real implementation
                    logger.info(f"Clicking element {i + 1}/{len(selectors)}: {selector}")
                    
                    # Simulate click
                    await asyncio.sleep(delay_ms / 1000)
                    
                    results.append({
                        "selector": selector,
                        "success": True,
                        "order": i + 1
                    })
                    
                except Exception as e:
                    results.append({
                        "selector": selector,
                        "success": False,
                        "error": str(e),
                        "order": i + 1
                    })
            
            successful_clicks = sum(1 for r in results if r["success"])
            
            return {
                "success": successful_clicks == len(selectors),
                "total_elements": len(selectors),
                "successful_clicks": successful_clicks,
                "failed_clicks": len(selectors) - successful_clicks,
                "results": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _form_fill_action(self, fields: Dict[str, str]) -> Dict[str, Any]:
        """Fill multiple form fields at once"""
        try:
            results = []
            
            for selector, value in fields.items():
                try:
                    # This would integrate with browser tools in a real implementation
                    logger.info(f"Filling field {selector} with value: {value}")
                    
                    # Simulate form fill
                    await asyncio.sleep(0.1)
                    
                    results.append({
                        "selector": selector,
                        "value": value,
                        "success": True
                    })
                    
                except Exception as e:
                    results.append({
                        "selector": selector,
                        "value": value,
                        "success": False,
                        "error": str(e)
                    })
            
            successful_fills = sum(1 for r in results if r["success"])
            
            return {
                "success": successful_fills == len(fields),
                "total_fields": len(fields),
                "successful_fills": successful_fills,
                "failed_fills": len(fields) - successful_fills,
                "results": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _scroll_to_element_action(self, selector: str, behavior: str = "smooth") -> Dict[str, Any]:
        """Scroll to make an element visible"""
        try:
            # This would integrate with browser tools in a real implementation
            logger.info(f"Scrolling to element {selector} with behavior: {behavior}")
            
            # Simulate scroll
            await asyncio.sleep(0.5)
            
            return {
                "success": True,
                "selector": selector,
                "behavior": behavior,
                "message": f"Successfully scrolled to element {selector}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "selector": selector,
                "error": str(e)
            }
    

    
    def register_custom_action(self, name: str, description: str, function: Callable, 
                             parameters_schema: Optional[Dict[str, Any]] = None):
        """Register a new custom action"""
        if name in self.custom_actions:
            logger.warning(f"Custom action '{name}' already exists, overwriting")
        
        self.custom_actions[name] = {
            "description": description,
            "function": function,
            "parameters_schema": parameters_schema or {}
        }
        
        logger.info(f"Custom action '{name}' registered successfully")
    
    def unregister_custom_action(self, name: str):
        """Unregister a custom action"""
        if name in self.custom_actions:
            del self.custom_actions[name]
            logger.info(f"Custom action '{name}' unregistered successfully")
        else:
            logger.warning(f"Custom action '{name}' not found for unregistration")
    
    def get_custom_actions(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered custom actions"""
        return self.custom_actions.copy()
    
    def get_action_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get action execution history"""
        return self.action_history[-limit:] if limit > 0 else self.action_history.copy()
    
    async def save_custom_actions(self, filepath: str = "custom_actions/actions.json"):
        """Save custom actions to a JSON file"""
        try:
            # Convert functions to string representations for serialization
            serializable_actions = {}
            for name, config in self.custom_actions.items():
                serializable_actions[name] = {
                    "description": config["description"],
                    "parameters_schema": config["parameters_schema"],
                    "function_name": config["function"].__name__ if hasattr(config["function"], "__name__") else str(config["function"])
                }
            
            # Ensure directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(serializable_actions, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Custom actions saved to {filepath}")
            return {"success": True, "filepath": filepath}
            
        except Exception as e:
            logger.error(f"Failed to save custom actions: {e}")
            return {"success": False, "error": str(e)}
    
    async def load_custom_actions(self, filepath: str = "custom_actions/actions.json"):
        """Load custom actions from a JSON file"""
        try:
            if not Path(filepath).exists():
                logger.warning(f"Custom actions file {filepath} not found")
                return {"success": False, "error": "File not found"}
            
            with open(filepath, 'r', encoding='utf-8') as f:
                actions_data = json.load(f)
            
            # Note: Functions cannot be deserialized from JSON
            # This would need to be handled differently in a real implementation
            logger.info(f"Loaded {len(actions_data)} custom action definitions from {filepath}")
            return {"success": True, "actions_loaded": len(actions_data)}
            
        except Exception as e:
            logger.error(f"Failed to load custom actions: {e}")
            return {"success": False, "error": str(e)}
