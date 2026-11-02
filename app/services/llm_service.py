"""
LLM service for the Browser Use Agent
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import re # Added for navigation planning

from app.core.config import settings
from app.services.tool_service import ToolService

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with Large Language Models"""
    
    def __init__(self, tool_service: ToolService):
        self.tool_service = tool_service
        self.openai_client = None
        self.google_client = None
        self.current_provider = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize LLM clients"""
        try:
            # Use the configured LLM provider
            provider = settings.bua_llm_provider.lower()
            
            if provider == "openai":
                if not settings.openai_api_key:
                    raise RuntimeError("OpenAI API key not configured")
                import openai
                self.openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
                self.current_provider = "openai"
                logger.info("OpenAI client initialized")
            
            elif provider == "gemini":
                # Try gemini_api_key first, then fall back to google_api_key
                api_key = settings.gemini_api_key or settings.google_api_key
                if not api_key:
                    raise RuntimeError("Gemini API key not configured")
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                
                # Debug logging to see which model is actually being used
                logger.info(f"Loading Gemini model: {settings.google_model}")
                logger.info(f"Full settings object: {settings}")
                
                self.google_client = genai.GenerativeModel(settings.google_model)
                self.current_provider = "google"
                logger.info(f"Google Gemini client initialized with model: {settings.google_model}")
            
            else:
                raise RuntimeError(f"Unsupported LLM provider: {provider}")
            
            self.is_initialized = True
            logger.info(f"LLM service initialized with provider: {self.current_provider}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
            raise
    
    def _ensure_initialized(self):
        """Ensure LLM service is initialized"""
        if not self.is_initialized:
            raise RuntimeError("LLM service not initialized")
    
    async def generate_plan(self, task: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a plan for the given task using LLM"""
        try:
            prompt = self._create_planning_prompt(task, current_state)
            
            if self.current_provider == "openai":
                plan = await self._generate_openai_plan(prompt)
            elif self.current_provider == "google":
                plan = await self._generate_google_plan(prompt)
            else:
                raise RuntimeError(f"Unsupported LLM provider: {self.current_provider}")
            
            # Parse and validate the plan
            validated_plan = self._validate_plan(plan)
            
            return validated_plan
            
        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            return {"success": False, "error": str(e)}
    
    async def decide_next_action(self, current_state: Dict[str, Any], 
                                available_tools: List[Dict[str, Any]], 
                                task_context: str) -> Dict[str, Any]:
        """Decide the next action to take"""
        self._ensure_initialized()
        
        try:
            # Check if we have interactive elements before proceeding with action decision
            interactive_elements_available = False
            if 'page_info' in current_state and 'dom' in current_state['page_info']:
                dom = current_state['page_info']['dom']
                if 'interactive_elements' in dom and isinstance(dom['interactive_elements'], list):
                    interactive_elements = dom['interactive_elements']
                    # Filter for actually interactive and visible elements
                    visible_interactive = [elem for elem in interactive_elements 
                                         if elem.get('isVisible', False) and 
                                         elem.get('tagName') in ['button', 'input', 'a', 'select', 'textarea']]
                    interactive_elements_available = len(visible_interactive) > 0
                    
                    logger.info(f"Interactive elements check: {len(visible_interactive)} visible interactive elements found")
            
            # Don't hardcode actions - let the LLM decide what to do
            # Even if no interactive elements are visible, the LLM might want to navigate, scroll, or take other actions
            logger.info("Letting LLM decide next action based on current state and task")
            
            # Log the current state (DOM information) being sent to LLM
            logger.info("=== DOM INFORMATION SENT TO LLM FOR ACTION DECISION ===")
            logger.info(f"Task Context: {task_context}")
            logger.info(f"Current State Keys: {list(current_state.keys())}")
            
            # Log DOM structure if available
            if 'page_info' in current_state:
                page_info = current_state['page_info']
                logger.info(f"Page Info Keys: {list(page_info.keys()) if isinstance(page_info, dict) else 'Not a dict'}")
                
                # Log complete page info structure
                logger.info("=== COMPLETE PAGE INFO STRUCTURE ===")
                logger.info(f"Complete Page Info: {page_info}")
                
                if 'interactive_elements' in page_info:
                    elements = page_info['interactive_elements']
                    logger.info(f"Interactive Elements Count: {len(elements) if isinstance(elements, list) else 'Not a list'}")
                    if isinstance(elements, list) and elements:
                        logger.info("Interactive Elements Available:")
                        for i, elem in enumerate(elements):
                            tag = elem.get('tagName', 'N/A')
                            text = elem.get('textContent', 'N/A') if elem.get('textContent') else 'N/A'
                            selector = elem.get('id', '') or elem.get('className', '')
                            visible = elem.get('isVisible', 'N/A')
                            logger.info(f"  {i+1}. {tag} - '{text}' - visible: {visible} - selector: {selector}")
                
                if 'page_structure' in page_info:
                    structure = page_info['page_structure']
                    logger.info(f"Page Structure: {structure}")
                
                if 'viewport_info' in page_info:
                    viewport = page_info['viewport_info']
                    logger.info(f"Viewport Info: {viewport}")
            
            # Create system prompt for action decision
            system_prompt = self._create_action_decision_prompt(current_state, available_tools, task_context)
            
            # Log the prompt being sent to LLM
            logger.info(f"=== ACTION DECISION PROMPT SENT TO LLM ===")
            logger.info(f"Prompt Length: {len(system_prompt)} characters")
            logger.info(f"Complete Prompt: {system_prompt}")
            
            # Generate action decision using LLM
            if self.current_provider == "openai":
                action_decision = await self._generate_openai_action_decision(system_prompt)
            elif self.current_provider == "google":
                action_decision = await self._generate_google_action_decision(system_prompt)
            else:
                raise RuntimeError(f"Unsupported LLM provider: {self.current_provider}")
            
            # Log the LLM response for debugging
            logger.info("=== LLM RESPONSE FOR ACTION DECISION ===")
            logger.info(f"Raw LLM Response: {action_decision}")
            logger.info(f"Response Length: {len(action_decision)} characters")
            
            # Parse and validate action decision
            validated_decision = self._validate_action_decision(action_decision)
            
            # CRITICAL: Force authentication actions when authentication is required
            if self._is_authentication_required(current_state):
                logger.info("Authentication required detected - validating AI decision")
                
                # Find actual login elements on the page
                login_info = self._find_login_elements(current_state)
                
                if login_info['found']:
                    logger.info(f"Found login element: {login_info['element_text']} -> {login_info['login_url']}")
                    
                    # Check if AI is trying to avoid authentication
                    if validated_decision.get("action") in ["get_page_info", "wait_for_element"]:
                        logger.warning("AI trying to avoid authentication - forcing login navigation")
                        
                        # Use the actual login URL from the page
                        login_url = login_info['login_url']
                        if not login_url.startswith('http'):
                            # Make relative URL absolute if needed
                            if 'browser_state' in current_state and 'url' in current_state['browser_state']:
                                base_url = current_state['browser_state']['url']
                                if base_url:
                                    from urllib.parse import urljoin
                                    login_url = urljoin(base_url, login_url)
                                    logger.info(f"Converted relative URL '{login_info['login_url']}' to absolute URL '{login_url}'")
                                else:
                                    logger.warning("No base URL found, using relative URL as-is")
                            else:
                                logger.warning("No browser state found, using relative URL as-is")
                        
                        # Ensure URL is absolute for Playwright
                        if not login_url.startswith('http'):
                            logger.error(f"Failed to construct absolute URL for login: {login_url}")
                            # Don't hardcode fallback URLs - let the LLM handle this
                            logger.warning("Failed to construct absolute login URL - letting LLM decide next action")
                            # Remove the forced authentication override and let LLM decide
                            validated_decision = validated_decision  # Keep original decision
                        else:
                            # Override with authentication action using actual login element
                            validated_decision = {
                                "success": True,
                                "action": "navigate",
                                "parameters": {"url": login_url},
                                "reasoning": f"Authentication required - navigating to actual login element: {login_info['element_text']}",
                                "expected_outcome": f"Navigate to login page at {login_url} to handle authentication",
                                "authentication_check": "Forced authentication action using page elements",
                                "confidence": 0.99
                            }
                            
                            logger.info(f"Forced authentication action: navigate to {login_url}")
                    else:
                        logger.info("AI correctly chose authentication action")
                        # Still need to ensure URL is absolute for any navigation action
                        if validated_decision.get("action") == "navigate":
                            navigation_url = validated_decision.get("parameters", {}).get("url", "")
                            if navigation_url and not navigation_url.startswith('http'):
                                # Convert relative URL to absolute
                                if 'browser_state' in current_state and 'url' in current_state['browser_state']:
                                    base_url = current_state['browser_state']['url']
                                    if base_url:
                                        from urllib.parse import urljoin
                                        absolute_url = urljoin(base_url, navigation_url)
                                        validated_decision["parameters"]["url"] = absolute_url
                                        logger.info(f"Converted AI navigation URL '{navigation_url}' to absolute URL '{absolute_url}'")
                                    else:
                                        logger.warning("No base URL found for URL conversion")
                                else:
                                    logger.warning("No browser state found for URL conversion")
                else:
                    logger.warning("Authentication required but no login elements found - letting LLM decide")
                    # Don't hardcode fallback actions - let the LLM figure out what to do
                    logger.info("No login elements found, LLM will decide next action")
            else:
                logger.info("No authentication required detected")
            
            # UNIVERSAL: Ensure ALL navigation actions have absolute URLs
            action = validated_decision.get('decision', {}).get('action') if isinstance(validated_decision, dict) else validated_decision.get('action')
            logger.info(f"=== UNIVERSAL URL CONSTRUCTION CHECK ===")
            logger.info(f"Extracted action: '{action}' from validated_decision")
            logger.info(f"Validated decision structure: {validated_decision}")
            
            # Check if human intervention is required
            human_intervention = self._requires_human_intervention(current_state, validated_decision)
            if human_intervention['requires_intervention']:
                logger.info(f"Human intervention required: {human_intervention['reason']}")
                
                # Override the decision to pause for human intervention
                if isinstance(validated_decision, dict) and 'decision' in validated_decision:
                    validated_decision['decision'] = {
                        'action': 'human_intervention_required',
                        'parameters': {
                            'reason': human_intervention['reason'],
                            'message': human_intervention['message'],
                            'action': human_intervention['action'],
                            'resume_after': human_intervention['resume_after']
                        },
                        'reasoning': f"Human intervention required: {human_intervention['reason']}",
                        'expected_outcome': "Agent will pause and wait for human to complete the required action",
                        'authentication_check': "Human intervention detected",
                        'confidence': 0.99
                    }
                else:
                    validated_decision = {
                        'success': True,
                        'action': 'human_intervention_required',
                        'parameters': {
                            'reason': human_intervention['reason'],
                            'message': human_intervention['message'],
                            'action': human_intervention['action'],
                            'resume_after': human_intervention['resume_after']
                        },
                        'reasoning': f"Human intervention required: {human_intervention['reason']}",
                        'expected_outcome': "Agent will pause and wait for human to complete the required action",
                        'authentication_check': "Human intervention detected",
                        'confidence': 0.99
                    }
                
                logger.info(f"Decision overridden for human intervention: {validated_decision}")
                logger.info("=== VALIDATED ACTION DECISION RESPONSE ===")
                logger.info(f"Validated Decision: {validated_decision}")
                return validated_decision
            
            if action == "navigate":
                logger.info("Navigation action detected")
                # Get parameters from the correct location
                if isinstance(validated_decision, dict) and 'decision' in validated_decision:
                    parameters = validated_decision['decision'].get('parameters', {})
                else:
                    parameters = validated_decision.get('parameters', {})
                
                navigation_url = parameters.get("url", "")
                logger.info(f"Navigation action detected with URL: '{navigation_url}'")
                logger.info(f"URL starts with 'http': {navigation_url.startswith('http') if navigation_url else 'No URL'}")
                
                if navigation_url and not navigation_url.startswith('http'):
                    logger.info(f"Relative URL detected: '{navigation_url}' - converting to absolute")
                    # Convert relative URL to absolute
                    if 'browser_state' in current_state and 'url' in current_state['browser_state']:
                        base_url = current_state['browser_state']['url']
                        logger.info(f"Base URL from browser state: '{base_url}'")
                        if base_url:
                            from urllib.parse import urljoin
                            absolute_url = urljoin(base_url, navigation_url)
                            # Update the URL in the correct location
                            if isinstance(validated_decision, dict) and 'decision' in validated_decision:
                                validated_decision['decision']['parameters']['url'] = absolute_url
                            else:
                                validated_decision['parameters']['url'] = absolute_url
                            logger.info(f"✅ Converted navigation URL '{navigation_url}' to absolute URL '{absolute_url}'")
                        else:
                            logger.warning("No base URL found for URL conversion")
                    else:
                        logger.warning("No browser state found for URL conversion")
                        logger.info(f"Current state keys: {list(current_state.keys()) if current_state else 'No state'}")
                else:
                    if navigation_url:
                        logger.info(f"URL '{navigation_url}' is already absolute, no conversion needed")
                    else:
                        logger.warning("No navigation URL found in parameters")
            else:
                logger.info(f"Not a navigation action: {action}")
            
            logger.info("=== VALIDATED ACTION DECISION RESPONSE ===")
            logger.info(f"Validated Decision: {validated_decision}")
            
            # Extract action for logging
            final_action = validated_decision.get('decision', {}).get('action') if isinstance(validated_decision, dict) else validated_decision.get('action')
            logger.info(f"Decided next action: {final_action}")
            return validated_decision
            
        except Exception as e:
            logger.error(f"Failed to decide next action: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": None
            }
    
    async def analyze_observation(self, observation: Dict[str, Any], 
                                 task_context: str) -> Dict[str, Any]:
        """Analyze an observation and provide insights"""
        self._ensure_initialized()
        
        try:
            # Log the observation (DOM information) being sent to LLM
            logger.info("=== DOM INFORMATION SENT TO LLM FOR OBSERVATION ANALYSIS ===")
            logger.info(f"Task Context: {task_context}")
            logger.info(f"Observation Keys: {list(observation.keys())}")
            
            # Log DOM structure if available
            if 'page_info' in observation:
                page_info = observation['page_info']
                logger.info(f"Page Info Keys: {list(page_info.keys()) if isinstance(page_info, dict) else 'Not a dict'}")
                
                # Log complete page info structure
                logger.info("=== COMPLETE PAGE INFO STRUCTURE ===")
                logger.info(f"Complete Page Info: {page_info}")
                
                if 'interactive_elements' in page_info:
                    elements = page_info['interactive_elements']
                    logger.info(f"Interactive Elements Count: {len(elements) if isinstance(elements, list) else 'Not a list'}")
                    if isinstance(elements, list) and elements:
                        logger.info("Interactive Elements in Observation:")
                        for i, elem in enumerate(elements):
                            tag = elem.get('tagName', 'N/A')
                            text = elem.get('textContent', 'N/A') if elem.get('textContent') else 'N/A'
                            selector = elem.get('id', '') or elem.get('className', 'N/A')
                            visible = elem.get('isVisible', 'N/A')
                            logger.info(f"  {i+1}. {tag} - '{text}' - visible: {visible} - selector: {selector}")
                
                if 'page_structure' in page_info:
                    structure = page_info['page_structure']
                    logger.info(f"Page Structure: {structure}")
                
                if 'viewport_info' in page_info:
                    viewport = page_info['viewport_info']
                    logger.info(f"Viewport Info: {viewport}")
            
            # Create system prompt for observation analysis
            system_prompt = self._create_observation_analysis_prompt(observation, task_context)
            
            # Log the prompt being sent to LLM
            logger.info(f"=== OBSERVATION ANALYSIS PROMPT SENT TO LLM ===")
            logger.info(f"Prompt Length: {len(system_prompt)} characters")
            logger.info(f"Complete Prompt: {system_prompt}")
            
            # Generate analysis using LLM
            if self.current_provider == "openai":
                analysis = await self._generate_openai_analysis(system_prompt)
            elif self.current_provider == "google":
                analysis = await self._generate_google_analysis(system_prompt)
            else:
                raise RuntimeError(f"Unsupported LLM provider: {self.current_provider}")
            
            # Log the LLM response for debugging
            logger.info("=== LLM RESPONSE FOR OBSERVATION ANALYSIS ===")
            logger.info(f"Raw LLM Response: {analysis}")
            logger.info(f"Response Length: {len(analysis)} characters")

            # Parse and validate analysis
            validated_analysis = self._validate_analysis(analysis)
            
            logger.info("=== VALIDATED OBSERVATION ANALYSIS RESPONSE ===")
            logger.info(f"Validated Analysis: {validated_analysis}")
            
            logger.info("Observation analysis completed")
            return validated_analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze observation: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis": {}
            }
    
    async def plan_initial_navigation(self, task: str) -> Dict[str, Any]:
        """Plan initial navigation strategy using LLM"""
        try:
            prompt = self._create_navigation_planning_prompt(task)
            
            if self.current_provider == "google":
                response = await self._generate_google_navigation_plan(prompt)
            else:
                response = await self._generate_openai_navigation_plan(prompt)
            
            # Extract JSON from response
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without markdown
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("No JSON found in response")
            
            # Parse and validate response
            try:
                plan_data = json.loads(json_str)
                
                # Ensure we have a valid URL
                if not plan_data.get("initial_url") or not plan_data["initial_url"].startswith("http"):
                    # Default to google.com for search tasks, otherwise use a generic fallback
                    if "search" in task.lower() or "google" in task.lower():
                        plan_data["initial_url"] = "https://www.google.com"
                    else:
                        plan_data["initial_url"] = "https://www.google.com"  # Generic fallback
                
                # Validate required fields
                validated_plan = {
                    "success": True,
                    "browser_needed": plan_data.get("browser_needed", True),
                    "initial_url": plan_data["initial_url"],
                    "navigation_strategy": plan_data.get("navigation_strategy", "Navigate to the main application URL"),
                    "expected_elements": plan_data.get("expected_elements", ["UI elements of the application"]),
                    "fallback_urls": plan_data.get("fallback_urls", []),
                    "reasoning": plan_data.get("reasoning", "Starting at the main application URL")
                }
                
                logger.info("=== VALIDATED NAVIGATION PLAN ===")
                logger.info(f"Validated Plan: {validated_plan}")
                
                return validated_plan
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse navigation plan JSON: {e}")
                logger.error(f"Raw response: {response}")
                
                # Return fallback plan
                return {
                    "success": True,
                    "browser_needed": True,
                    "initial_url": "https://www.google.com",
                    "navigation_strategy": "Navigate to Google for search tasks",
                    "expected_elements": ["Search box and search results"],
                    "fallback_urls": [],
                    "reasoning": "Fallback plan due to JSON parsing error"
                }
                
        except Exception as e:
            logger.error(f"Failed to plan navigation: {e}")
            # Return fallback plan
            return {
                "success": True,
                "browser_needed": True,
                "initial_url": "https://www.google.com",
                "navigation_strategy": "Navigate to Google for search tasks",
                "expected_elements": ["Search box and search results"],
                "fallback_urls": [],
                "reasoning": "Fallback plan due to error"
            }
    
    def _create_planning_prompt(self, task: str, current_state: Dict[str, Any]) -> str:
        """Create system prompt for planning"""
        return f"""You are an intelligent browser automation agent. Create a detailed execution plan for the given task.

TASK: {task}

CURRENT STATE:
{json.dumps(current_state, indent=2)}

AVAILABLE TOOLS:
- navigate: Navigate to a specific URL
- click: Click on an element using CSS selector
- type_text: Type text into an input field
- wait_for_element: Wait for an element to appear
- scroll: Scroll the page in a specific direction
- find_element_with_scroll: Find an element by scrolling if needed
- get_page_info: Get current page information

IMPORTANT TOOL SELECTION GUIDELINES:
- For navigation: Use the "navigate" tool
- For clicking elements: Use the "click" tool with CSS selectors
- For typing text: Use the "type_text" tool
- For waiting: Use the "wait_for_element" tool
- For scrolling: Use the "scroll" or "find_element_with_scroll" tools
- For form interactions: Use "click", "type_text", and "click" in sequence
- AVOID using "custom_action" unless you need a specific predefined custom action

AUTHENTICATION & LOGIN FLOW RECOGNITION:
- ALWAYS check if the current page requires authentication first
- Look for signs like: "Authentication Required", "Login Required", "Please Sign In", "Access Denied"
- If login is required, the FIRST step should be to navigate to the login page
- Common login page URLs: /auth/login, /login, /signin, /auth
- After login, wait for successful authentication before proceeding with the main task

COMMON TASK PATTERNS:
- Form interactions: click field → type_text value → repeat for all fields → click submit
- Navigation: navigate to URL → wait_for_element → click target element
- Login flow: navigate to login page → type_text username/email → type_text password → click login button → wait for redirect
- Element discovery: analyze page structure → identify relevant elements → use appropriate tools

INSTRUCTIONS:
1. Analyze the task and current state
2. Check if authentication is required (look for login indicators)
3. If login needed, plan the authentication flow FIRST
4. Break down the task into logical steps using the basic browser tools
5. For each step, specify:
    - The tool to use (prefer basic browser tools over custom actions)
    - The parameters for the tool
    - What you expect to happen
    - How to handle potential failures

Return your plan as a JSON object with this structure:
{{
  "success": true,
  "plan": [
    {{
      "step": 1,
      "action": "tool_name",
      "parameters": {{"param1": "value1"}},
      "expected_outcome": "What should happen",
      "failure_handling": "What to do if this fails"
    }}
  ],
  "authentication_required": true/false,
  "login_url": "URL if login needed",
  "reasoning": "Why this plan makes sense"
}}"""
    
    def _create_action_decision_prompt(self, current_state: Dict[str, Any], available_tools: List[Dict[str, Any]], task: str) -> str:
        """Create prompt for action decision"""
        # Extract key information from current state
        page_info = current_state.get('page_info', {})
        dom = page_info.get('dom', {})
        interactive_elements = dom.get('interactive_elements', [])
        page_structure = dom.get('page_structure', {})
        headings = page_structure.get('headings', [])
        
        # Check for authentication indicators
        auth_indicators = []
        if 'title' in page_info:
            title = page_info['title'].lower()
            if any(indicator in title for indicator in ['authentication required', 'login required', 'please sign in']):
                auth_indicators.append(f"Page title: {page_info['title']}")
        
        for heading in headings:
            heading_text = heading.get('text', '').lower()
            if any(indicator in heading_text for indicator in ['authentication required', 'login required', 'please sign in']):
                auth_indicators.append(f"Heading: {heading['text']}")
        
        # Check for login buttons
        login_buttons = []
        for element in interactive_elements:
            if element.get('tagName') == 'a' and element.get('textContent'):
                text = element.get('textContent', '').lower()
                if any(indicator in text for indicator in ['log in', 'login', 'sign in']):
                    href = element.get('attributes', {}).get('href', '')
                    login_buttons.append(f"{element['textContent']} -> {href}")
        
        # Check for button creation elements
        button_creation_elements = []
        for element in interactive_elements:
            if element.get('tagName') == 'button' and element.get('textContent'):
                text = element.get('textContent', '').lower()
                if any(indicator in text for indicator in ['new button', 'create button', 'add button']):
                    button_creation_elements.append(f"{element['textContent']} - visible: {element.get('isVisible', False)}")
        
        prompt = f"""You are an intelligent browser automation agent. Analyze the current state and decide the next action.
            
            TASK: {task}
            
            CURRENT PAGE STATE:
            - URL: {page_info.get('url', 'Unknown')}
            - Title: {page_info.get('title', 'Unknown')}
            - Interactive Elements: {len(interactive_elements)} found
            
            AUTHENTICATION STATUS:
            {f"Authentication Required: {', '.join(auth_indicators)}" if auth_indicators else "No authentication indicators found"}
            {f"Login Options: {', '.join(login_buttons)}" if login_buttons else "No login buttons found"}
            
            INTERACTIVE ELEMENTS STATUS:
            {f"Interactive Elements: {', '.join(button_creation_elements)}" if button_creation_elements else "No specific interactive elements found"}
            
            AVAILABLE TOOLS:
            {chr(10).join([f"- {tool['name']}: {tool['description']}" for tool in available_tools])}
            
            AUTHENTICATION & LOGIN FLOW RECOGNITION:
            - ALWAYS check if the current page requires authentication first
            - Look for signs like: "Authentication Required", "Login Required", "Please Sign In", "Access Denied", "Unauthorized"
            - If you see these indicators, the user needs to log in before proceeding
            - Common login page URLs: /auth/login, /login, /signin, /auth
            - If login is required, use "navigate" to go to the login page FIRST
            CRITICAL AUTHENTICATION RULES:
            - If you detect "Authentication Required" or similar, you MUST navigate to login
            - Do NOT wait for elements that will never appear without authentication
            - Do NOT repeatedly get page info when authentication is blocking progress
            - Authentication takes priority over all other actions
            - Only proceed with main task after successful authentication
            
            TASK EXECUTION GUIDELINES:
            - Analyze the current page to understand what needs to be done
            - Look for relevant UI elements that match your task
            - Use appropriate tools to accomplish the task step by step
            - Adapt to whatever page structure you find
            - Don't assume specific workflows - discover them dynamically
            
            GOOGLE SEARCH TASK:
            - If the task involves searching on Google, execute these steps in sequence:
              1. Use type_text to enter the search term into the search box
              2. Use click to submit the search by clicking the search button
              3. Use wait_for_element to wait for search results
            - CRITICAL: Execute BOTH typing AND clicking - do not stop after typing
            
            TOOL SELECTION RULES:
            1. PREFER basic browser tools: navigate, click, type_text, wait_for_element, scroll
            2. Use "click" for any button, link, or clickable element
            3. Use "type_text" for input fields, text areas, or any text input
            4. Use "navigate" to go to specific URLs
            5. Use "wait_for_element" to wait for elements to appear
            
            GOOGLE SEARCH SPECIFIC RULES:
            - For Google search: Use "type_text" with selector "#APjFqb" for the search box
            - After typing, use "click" with selector ".gNO89b" for the search button
            - Do NOT use "find_element_with_scroll" for Google search - the search box is always visible
            - Go directly to the action - no need to find elements first
            - CRITICAL: Execute BOTH type_text AND click actions in sequence
            6. Use "find_element_with_scroll" if elements might be below the fold
            7. AVOID "custom_action" unless you specifically need wait_and_retry, batch_click, form_fill, or scroll_to_element
            COMMON ACTIONS:
            - To click a button: use "click" with the button's CSS selector
            - To fill a form field: use "click" on the field, then "type_text" with the value
            - To submit a form: use "click" on the submit button
            - To navigate: use "navigate" with the URL
            - To wait for something: use "wait_for_element" with the selector
            INSTRUCTIONS:
            1. Analyze the current state
            2. Check if authentication is required (look for login indicators in page title, headings, or text)
            3. If login needed, navigate to login page first - THIS IS MANDATORY
            4. Consider the task context
            5. Choose the most appropriate basic browser tool
            6. Specify the exact parameters for the tool
            7. Explain your reasoning
            
            GOOGLE SEARCH WORKFLOW:
            - If you're on Google and need to search: Execute type_text first, then click
            - The search is NOT complete until you click the search button after typing
            - Always execute both actions: type_text then click
            - Example: type_text("#APjFqb", "Python tutorials") then click(".gNO89b")
            Return your decision as a JSON object with this structure:
            {{
              "action": "tool_name",
              "parameters": {{"param1": "value1"}},
              "reasoning": "Why this action is the best choice",
              "expected_outcome": "What should happen after this action",
              "authentication_check": "Whether you checked for login requirements",
              "confidence": 0.95
            }}
            Return only the JSON object, no additional text."""
        
        return prompt
    
    def _create_observation_analysis_prompt(self, observation: Dict[str, Any], 
                                          task_context: str) -> str:
        """Create system prompt for observation analysis"""
        return f"""You are an intelligent browser automation agent. Analyze the current observation and provide insights.

TASK CONTEXT: {task_context}

OBSERVATION:
{json.dumps(observation, indent=2)}

ANALYSIS INSTRUCTIONS:
1. Analyze the current page state
2. Check for authentication requirements (look for "Authentication Required", "Login Required", "Please Sign In", "Access Denied")
3. Identify any changes from previous state
4. Note any errors or issues
5. If there are tool execution errors, suggest better tool alternatives
6. Identify patterns or useful information
7. Suggest next steps using basic browser tools (navigate, click, type_text, wait_for_element)

AUTHENTICATION STATE ANALYSIS:
- If you see authentication indicators, the user needs to log in first
- Common login page URLs: /auth/login, /login, /signin, /auth
- After login, wait for successful authentication before proceeding
- Look for successful login indicators like redirects, user menu, or logout button

TOOL ERROR RECOVERY:
- If "custom_action" failed: Suggest using basic browser tools instead
- If element not found: Suggest using "find_element_with_scroll" or "wait_for_element"
- If click failed: Check if element is visible and suggest waiting or scrolling
- If navigation failed: Verify URL and suggest retry with "navigate"
- If authentication required: Suggest navigating to login page first

Return your analysis as a JSON object with this structure:
{{
  "current_state": "Description of current state",
  "authentication_required": true/false,
  "login_url": "URL if login needed",
  "changes_detected": ["List of changes"],
  "issues_found": ["List of issues"],
  "next_steps": ["Suggested next steps using basic browser tools"],
  "patterns": ["Identified patterns"],
  "confidence": 0.95
}}

IMPORTANT: Return ONLY valid JSON. Do not include any comments, explanations, or additional text outside the JSON object."""
    
    async def _generate_openai_plan(self, prompt: str) -> str:
        """Generate plan using OpenAI"""
        response = await self.openai_client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": prompt}
            ],
            max_tokens=settings.openai_max_tokens,
            temperature=settings.openai_temperature
        )
        
        return response.choices[0].message.content
    
    async def _generate_google_plan(self, prompt: str) -> str:
        """Generate plan using Google Gemini"""
        response = self.google_client.generate_content(prompt)
        return response.text
    
    async def _generate_openai_action_decision(self, prompt: str) -> str:
        """Generate action decision using OpenAI"""
        response = await self.openai_client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": prompt}
            ],
            max_tokens=1000,
            temperature=settings.openai_temperature
        )
        
        return response.choices[0].message.content
    
    async def _generate_google_action_decision(self, prompt: str) -> str:
        """Generate action decision using Google Gemini"""
        response = self.google_client.generate_content(prompt)
        return response.text
    
    async def _generate_openai_analysis(self, prompt: str) -> str:
        """Generate analysis using OpenAI"""
        response = await self.openai_client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": prompt}
            ],
            max_tokens=1000,
            temperature=settings.openai_temperature
        )
        
        return response.choices[0].message.content
    
    async def _generate_google_analysis(self, prompt: str) -> str:
        """Generate analysis using Google Gemini"""
        response = self.google_client.generate_content(prompt)
        return response.text
    
    def _validate_plan(self, plan_text: str) -> Dict[str, Any]:
        """Validate and parse the generated plan"""
        try:
            # Extract JSON from the response
            plan_json = self._extract_json(plan_text)
            
            if not isinstance(plan_json, dict):
                raise ValueError("Plan must be a dictionary")
            
            # Validate each step
            validated_steps = []
            for i, step in enumerate(plan_json.get("plan", [])):
                if not isinstance(step, dict):
                    continue
                
                validated_step = {
                    "step_number": step.get("step", i + 1),
                    "description": step.get("expected_outcome", ""),
                    "tool": step.get("action", ""),
                    "parameters": step.get("parameters", {}),
                    "expected_result": step.get("expected_outcome", ""),
                    "error_handling": step.get("failure_handling", ""),
                    "retry_strategy": "" # No retry strategy in this new structure
                }
                validated_steps.append(validated_step)
            
            return {
                "success": plan_json.get("success", False),
                "plan": validated_steps,
                "total_steps": len(validated_steps),
                "authentication_required": plan_json.get("authentication_required", False),
                "login_url": plan_json.get("login_url", ""),
                "reasoning": plan_json.get("reasoning", "")
            }
            
        except Exception as e:
            logger.error(f"Plan validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "plan": [],
                "authentication_required": False,
                "login_url": "",
                "reasoning": ""
            }
    
    def _validate_action_decision(self, decision_text: str) -> Dict[str, Any]:
        """Validate and parse the generated action decision"""
        try:
            logger.info(f"=== ACTION DECISION VALIDATION DEBUG ===")
            logger.info(f"Raw decision text: {decision_text}")
            
            # Extract JSON from the response
            decision_json = self._extract_json(decision_text)
            logger.info(f"Extracted JSON: {decision_json}")
            
            if not isinstance(decision_json, dict):
                raise ValueError("Action decision must be a dictionary")
            
            validated_decision = {
                "action": decision_json.get("action", ""),
                "parameters": decision_json.get("parameters", {}),
                "reasoning": decision_json.get("reasoning", ""),
                "expected_outcome": decision_json.get("expected_outcome", ""),
                "authentication_check": decision_json.get("authentication_check", ""),
                "confidence": decision_json.get("confidence", 0.5)
            }
            
            result = {
                "success": True,
                "decision": validated_decision
            }
            
            logger.info(f"Validated decision result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Action decision validation failed: {e}")
            logger.error(f"Raw decision text: {decision_text}")
            # Return a fallback decision to type in the search box
            return {
                "success": True,
                "decision": {
                    "action": "type_text",
                    "parameters": {
                        "selector": "#APjFqb",
                        "text": "Python tutorials"
                    },
                    "reasoning": "Fallback: Type search query into Google search box",
                    "expected_outcome": "Search query will be entered into the search box",
                    "authentication_check": "No authentication required for Google search",
                    "confidence": 0.8
                }
            }
    
    def _validate_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Validate and parse the generated analysis"""
        try:
            # Extract JSON from the response
            analysis_json = self._extract_json(analysis_text)
            
            if not isinstance(analysis_json, dict):
                raise ValueError("Analysis must be a dictionary")
            
            validated_analysis = {
                "current_state": analysis_json.get("current_state", ""),
                "changes_detected": analysis_json.get("changes_detected", []),
                "issues_found": analysis_json.get("issues_found", []),
                "next_steps": analysis_json.get("next_steps", []),
                "patterns": analysis_json.get("patterns", []),
                "confidence": analysis_json.get("confidence", 0.5)
            }
            
            return {
                "success": True,
                "analysis": validated_analysis
            }
            
        except Exception as e:
            logger.error(f"Analysis validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis": {}
            }
    
    def _validate_navigation_plan(self, navigation_plan_text: str) -> Dict[str, Any]:
        """Validate and parse navigation plan from LLM response"""
        try:
            # Extract JSON from response
            plan_json = self._extract_json(navigation_plan_text)
            
            if not isinstance(plan_json, dict):
                raise ValueError("Navigation plan must be a dictionary")
            
            # Validate required fields
            required_fields = ["browser_needed", "initial_url", "navigation_strategy"]
            for field in required_fields:
                if field not in plan_json:
                    raise ValueError(f"Missing required field: {field}")
            
            return {
                "success": True,
                "browser_needed": plan_json.get("browser_needed", False),
                "initial_url": plan_json.get("initial_url", ""),
                "navigation_strategy": plan_json.get("navigation_strategy", ""),
                "expected_elements": plan_json.get("expected_elements", []),
                "fallback_urls": plan_json.get("fallback_urls", []),
                "reasoning": plan_json.get("reasoning", "")
            }
            
        except Exception as e:
            logger.error(f"Failed to validate navigation plan: {e}")
            return {
                "success": False,
                "error": str(e),
                "browser_needed": False,
                "initial_url": "",
                "navigation_strategy": "",
                "expected_elements": [],
                "fallback_urls": [],
                "reasoning": ""
            }
    
    def _extract_json(self, text: str) -> Any:
        """Extract JSON from text response"""
        try:
            # Try to find JSON in the text
            start_idx = text.find('{')
            if start_idx == -1:
                start_idx = text.find('[')
            
            if start_idx == -1:
                raise ValueError("No JSON found in response")
            
            # Find the matching closing bracket/brace
            if text[start_idx] == '{':
                bracket_count = 0
                for i in range(start_idx, len(text)):
                    if text[i] == '{':
                        bracket_count += 1
                    elif text[i] == '}':
                        bracket_count -= 1
                        if bracket_count == 0:
                            json_text = text[start_idx:i+1]
                            break
                else:
                    raise ValueError("Unmatched braces in JSON")
            else:  # [
                bracket_count = 0
                for i in range(start_idx, len(text)):
                    if text[i] == '[':
                        bracket_count += 1
                    elif text[i] == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            json_text = text[start_idx:i+1]
                            break
                else:
                    raise ValueError("Unmatched brackets in JSON")
            
            return json.loads(json_text)
            
        except Exception as e:
            logger.error(f"JSON extraction failed: {e}")
            raise
    
    def _is_authentication_required(self, current_state: Dict[str, Any]) -> bool:
        """Check if the current state indicates authentication is required"""
        try:
            # Check page info for authentication indicators
            if 'page_info' in current_state:
                page_info = current_state['page_info']
                
                # Check page title
                if 'title' in page_info:
                    title = page_info['title'].lower()
                    auth_indicators = ['authentication required', 'login required', 'please sign in', 'access denied', 'unauthorized']
                    if any(indicator in title for indicator in auth_indicators):
                        logger.info(f"Authentication required detected in title: {page_info['title']}")
                        return True
                
                # Check page structure headings
                if 'dom' in page_info and 'page_structure' in page_info['dom']:
                    page_structure = page_info['dom']['page_structure']
                    if 'headings' in page_structure:
                        for heading in page_structure['headings']:
                            heading_text = heading.get('text', '').lower()
                            auth_indicators = ['authentication required', 'login required', 'please sign in', 'access denied', 'unauthorized']
                            if any(indicator in heading_text for indicator in auth_indicators):
                                logger.info(f"Authentication required detected in heading: {heading['text']}")
                                return True
                
                # Check for login buttons (indicates authentication needed)
                if 'dom' in page_info and 'interactive_elements' in page_info['dom']:
                    elements = page_info['dom']['interactive_elements']
                    login_indicators = ['log in', 'login', 'sign in', 'signin']
                    for element in elements:
                        if element.get('tagName') == 'a' and element.get('textContent'):
                            text = element.get('textContent', '').lower()
                            if any(indicator in text for indicator in login_indicators):
                                logger.info(f"Login button detected: {element.get('textContent')}")
                                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking authentication requirement: {e}")
            return False
    
    def _find_login_elements(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """Find actual login-related interactive elements and their URLs"""
        try:
            login_elements = []
            
            if 'page_info' in current_state and 'dom' in current_state['page_info']:
                dom = current_state['page_info']['dom']
                
                if 'interactive_elements' in dom:
                    elements = dom['interactive_elements']
                    
                    # Look for login-related elements
                    login_indicators = ['log in', 'login', 'sign in', 'signin', 'authenticate']
                    
                    for element in elements:
                        if element.get('isVisible', False):  # Only visible elements
                            tag = element.get('tagName', '')
                            text = element.get('textContent', '').lower() if element.get('textContent') else ''
                            
                            # Check if element is login-related
                            if any(indicator in text for indicator in login_indicators):
                                login_elements.append({
                                    'tagName': tag,
                                    'textContent': element.get('textContent', ''),
                                    'href': element.get('attributes', {}).get('href', ''),
                                    'id': element.get('id'),
                                    'className': element.get('className'),
                                    'isVisible': element.get('isVisible', False)
                                })
                                logger.info(f"Found login element: {element.get('textContent')} -> {element.get('attributes', {}).get('href', '')}")
            
            if login_elements:
                # Find the best login element (prefer links over buttons, prefer specific login text)
                best_element = None
                for element in login_elements:
                    if element['tagName'] == 'a' and element['href']:
                        if 'login' in element['textContent'].lower():
                            best_element = element
                            break
                        elif not best_element:  # Fallback to first link
                            best_element = element
                
                if best_element:
                    return {
                        'found': True,
                        'login_url': best_element['href'],
                        'element_text': best_element['textContent'],
                        'element_type': best_element['tagName'],
                        'all_elements': login_elements
                    }
            
            return {
                'found': False,
                'login_url': None,
                'element_text': None,
                'element_type': None,
                'all_elements': []
            }
            
        except Exception as e:
            logger.error(f"Error finding login elements: {e}")
            return {
                'found': False,
                'login_url': None,
                'element_text': None,
                'element_type': None,
                'all_elements': []
            }
    
    def _requires_human_intervention(self, current_state: Dict[str, Any], action_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Check if the current situation requires human intervention"""
        try:
            # Check if we're in an authentication flow that needs human completion
            if 'browser_state' in current_state and 'url' in current_state['browser_state']:
                current_url = current_state['browser_state']['url']
                
                # Google OAuth flow - user needs to complete login manually
                if 'accounts.google.com' in current_url and 'signin' in current_url:
                    return {
                        'requires_intervention': True,
                        'reason': 'Google OAuth login requires human completion',
                        'message': 'Please complete the Google login process in the browser window. Enter your credentials and complete the authentication flow.',
                        'action': 'wait_for_human_login',
                        'resume_after': 'authentication_complete'
                    }
                
                # Generic OAuth callback or authentication page
                if any(domain in current_url for domain in ['oauth', 'auth', 'login', 'signin']):
                    if 'callback' in current_url or 'consent' in current_url:
                        return {
                            'requires_intervention': True,
                            'reason': 'OAuth authentication flow requires human completion',
                            'message': 'Please complete the authentication process in the browser window. Follow any prompts or complete the login flow.',
                            'action': 'wait_for_human_login',
                            'resume_after': 'authentication_complete'
                        }
                
                # Check if we're stuck in a login form without credentials
                if action_decision.get('action') == 'type_text' and 'email' in action_decision.get('parameters', {}).get('text', '').lower():
                    if 'your_google_email@example.com' in action_decision.get('parameters', {}).get('text', ''):
                        return {
                            'requires_intervention': True,
                            'reason': 'AI cannot provide real credentials for login',
                            'message': 'Please enter your actual Google email address and password in the browser window to complete the login.',
                            'action': 'wait_for_human_login',
                            'resume_after': 'authentication_complete'
                        }
            
            # Check if we're waiting for elements that may never appear
            if action_decision.get('action') == 'wait_for_element':
                selector = action_decision.get('parameters', {}).get('selector', '')
                if any(keyword in selector.lower() for keyword in ['button', 'input', 'form']):
                    # If we've been waiting too long, ask for human help
                    return {
                        'requires_intervention': True,
                        'reason': 'Waiting for interactive elements that may require human action',
                        'message': 'The system is waiting for interactive elements to appear. Please check the browser window and complete any required actions manually.',
                        'action': 'wait_for_human_action',
                        'resume_after': 'elements_visible'
                    }
            
            return {
                'requires_intervention': False,
                'reason': None,
                'message': None,
                'action': None,
                'resume_after': None
            }
            
        except Exception as e:
            logger.error(f"Error checking human intervention requirement: {e}")
            return {
                'requires_intervention': False,
                'reason': None,
                'message': None,
                'action': None,
                'resume_after': None
            }
    
    def get_current_provider(self) -> str:
        """Get the current LLM provider"""
        return self.current_provider or "none"
    
    def get_available_providers(self) -> List[str]:
        """Get list of available LLM providers"""
        providers = []
        if settings.openai_api_key:
            providers.append("openai")
        if settings.google_api_key:
            providers.append("google")
        return providers

    def _create_navigation_planning_prompt(self, task: str) -> str:
        """Create prompt for navigation planning"""
        return f"""You are an intelligent browser automation agent. Your task is to plan the initial navigation strategy.

TASK: {task}

AVAILABLE TOOLS:
- navigate: Navigate to a specific URL
- wait_for_element: Wait for an element to appear
- get_page_info: Get current page information

STRATEGIC NAVIGATION PLANNING:
1. Analyze the task to understand what needs to be accomplished
2. Determine if a browser is needed at all
3. If browser needed, decide the optimal starting URL
4. Plan the initial navigation sequence

NAVIGATION STRATEGY RULES:
- For web applications: Start at the main app URL or login page
- For specific features: Navigate directly to the feature URL
- For authentication: Start at the login page
- For public sites: Start at the homepage
- Always consider the most efficient path

COMMON TASK PATTERNS:
- "create a new button in ButtonLog app" → Navigate to ButtonLog app URL first
- "login to localhost:4001" → Navigate to localhost:4001/auth/login
- "search for something on google" → Navigate to google.com
- "navigate to google.com and search for" → Navigate to google.com
- "fill out a form on example.com" → Navigate to example.com

Return your navigation plan as a JSON object with this structure:
{{
  "browser_needed": true/false,
  "initial_url": "URL to navigate to first",
  "navigation_strategy": "Description of the navigation approach",
  "expected_elements": ["What elements we expect to find"],
  "fallback_urls": ["Alternative URLs if initial fails"],
  "reasoning": "Why this navigation strategy makes sense"
}}

Return only the JSON object, no additional text."""

    async def _generate_google_navigation_plan(self, prompt: str) -> str:
        """Generate navigation plan using Google Gemini"""
        try:
            response = self.google_client.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Failed to generate Google navigation plan: {e}")
            raise

    async def _generate_openai_navigation_plan(self, prompt: str) -> str:
        """Generate navigation plan using OpenAI"""
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.openai_client.model, # Use the model from openai_client
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.openai_client.max_tokens, # Use the max_tokens from openai_client
                temperature=self.openai_client.temperature # Use the temperature from openai_client
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to generate OpenAI navigation plan: {e}")
            raise
