"""
Main agent service for the Browser Use Agent
"""

import logging
import uuid
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.tool_service import ToolService
from app.services.llm_service import LLMService
from app.services.browser_service import BrowserService
# from app.models.agent import AgentSession, AgentAction, AgentObservation, AgentMemory

# Simple in-memory session class for when database is not available
class SimpleAgentSession:
    """Simple in-memory agent session"""
    def __init__(self, session_id: str, task: str, initial_url: Optional[str] = None):
        self.session_id = session_id
        self.task = task
        self.initial_url = initial_url
        self.status = "running"
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.current_state: Dict[str, Any] = {}
        self.task_history: List[Dict[str, Any]] = []

logger = logging.getLogger(__name__)


class AgentService:
    """Main service for orchestrating the Observe-Reason-Act loop"""
    
    def __init__(self):
        self.tool_service: Optional[ToolService] = None
        self.llm_service: Optional[LLMService] = None
        self.browser_service: Optional[BrowserService] = None
        self.active_sessions: Dict[str, SimpleAgentSession] = {}
        self.is_initialized = False
        
    async def initialize(self, tool_service: ToolService, browser_service: BrowserService):
        """Initialize the agent service"""
        try:
            self.tool_service = tool_service
            
            # Store browser service
            self.browser_service = browser_service
            
            # Initialize LLM service
            self.llm_service = LLMService(tool_service)
            await self.llm_service.initialize()
            
            self.is_initialized = True
            logger.info("Agent service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent service: {e}")
            raise
    
    def _ensure_initialized(self):
        """Ensure agent service is initialized"""
        if not self.is_initialized:
            raise RuntimeError("Agent service not initialized")
    
    async def start_session(self, task: str, initial_url: Optional[str] = None) -> Dict[str, Any]:
        """Start a new agent session"""
        self._ensure_initialized()
        
        try:
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Use LLM to plan initial navigation strategy
            logger.info(f"Planning initial navigation strategy for task: {task}")
            navigation_plan = await self.llm_service.plan_initial_navigation(task)
            
            if not navigation_plan["success"]:
                logger.error(f"Failed to plan navigation: {navigation_plan['error']}")
                return {
                    "success": False,
                    "error": f"Navigation planning failed: {navigation_plan['error']}"
                }
            
            # Check if browser is needed
            if not navigation_plan["browser_needed"]:
                logger.info("LLM determined browser is not needed for this task")
                return {
                    "success": True,
                    "session_id": session_id,
                    "status": "completed",
                    "message": "Task completed without browser - browser not needed",
                    "navigation_plan": navigation_plan
                }
            
            # Use LLM's suggested initial URL if none provided
            if not initial_url and navigation_plan["initial_url"]:
                initial_url = navigation_plan["initial_url"]
                logger.info(f"Using LLM-suggested initial URL: {initial_url}")
            
            # Create session object with navigation plan
            session = SimpleAgentSession(
                session_id=session_id,
                task=task,
                initial_url=initial_url
            )
            
            # Store navigation plan in session for reference
            session.navigation_plan = navigation_plan
            
            # Store session
            self.active_sessions[session_id] = session
            
            # Start the agent loop in background
            try:
                asyncio.create_task(self._run_agent_loop(session))
            except Exception as e:
                logger.warning(f"Could not start agent loop: {e}")
                # Continue without the background loop
            
            logger.info(f"Started agent session {session_id} for task: {task[:50]}...")
            logger.info(f"Navigation strategy: {navigation_plan['navigation_strategy']}")
            
            return {
                "success": True,
                "session_id": session_id,
                "status": "started",
                "message": "Agent session started successfully",
                "navigation_plan": navigation_plan
            }
            
        except Exception as e:
            logger.error(f"Failed to start agent session: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get the status of an agent session"""
        if session_id not in self.active_sessions:
            return {
                "success": False,
                "error": "Session not found"
            }
        
        session = self.active_sessions[session_id]
        
        return {
            "success": True,
            "session_id": session_id,
            "status": session.status,
            "task": session.task,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat()
        }
    
    async def stop_session(self, session_id: str) -> Dict[str, Any]:
        """Stop an agent session"""
        if session_id not in self.active_sessions:
            return {
                "success": False,
                "error": "Session not found"
            }
        
        session = self.active_sessions[session_id]
        session.status = "stopped"
        session.updated_at = datetime.utcnow()
        
        logger.info(f"Stopped agent session {session_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "status": "stopped",
            "message": "Session stopped successfully"
        }
    
    async def _run_agent_loop(self, session: SimpleAgentSession) -> None:
        """Run the main agent loop"""
        try:
            iteration = 0
            max_iterations = 20  # Prevent infinite loops
            
            # Initialize browser navigation first
            if hasattr(session, 'navigation_plan') and session.navigation_plan:
                nav_plan = session.navigation_plan
                logger.info(f"Following LLM navigation plan: {nav_plan['navigation_strategy']}")
                
                # Let the LLM handle all navigation decisions - no hardcoded URLs
                if nav_plan.get("initial_url"):
                    logger.info(f"Navigating to LLM-suggested URL: {nav_plan['initial_url']}")
                    try:
                        await self.browser_service.navigate(nav_plan['initial_url'])
                        await asyncio.sleep(3)
                        logger.info("Initial navigation completed successfully")
                    except Exception as e:
                        logger.error(f"Initial navigation failed: {e}")
                        session.status = "failed"
                        return
                else:
                    logger.info("No initial URL in navigation plan - letting LLM decide first action")
                
                # Now check if already authenticated
                try:
                    auth_check = await self.browser_service.is_authenticated()
                    logger.info(f"Authentication check result: {auth_check}")
                    
                    if auth_check.get('success') and auth_check.get('authenticated'):
                        logger.info("✅ User already authenticated, proceeding with main task")
                        # Don't hardcode navigation - let the LLM decide what to do next
                        # Just set the session state to indicate we're ready
                        session.current_state = {
                            'status': 'authenticated_ready',
                            'message': 'User authenticated, ready for main task',
                            'timestamp': datetime.now().isoformat()
                        }
                        
                    else:
                        logger.info("🔐 User not authenticated, proceeding with login flow")
                        # Let the LLM decide how to handle authentication
                        logger.info("Authentication needed - LLM will decide next action")
                except Exception as e:
                    logger.warning(f"Authentication check failed, proceeding with login: {e}")
                    # Let the LLM decide how to handle this situation
                    logger.info("Authentication check failed - LLM will decide next action")
                
                # Wait for page to load and let the LLM decide what to do next
                # Don't hardcode what elements to wait for - let the AI agent figure it out
                logger.info("Page loaded, letting LLM decide next actions")
                
                # Small delay to ensure page is fully loaded
                await asyncio.sleep(2)
            elif session.initial_url: # Fallback to provided initial URL if no nav plan
                logger.info(f"Using fallback initial URL: {session.initial_url}")
                try:
                    await self.browser_service.navigate(session.initial_url)
                    await asyncio.sleep(3)
                    logger.info("Fallback navigation completed successfully")
                except Exception as e:
                    logger.error(f"Fallback navigation failed: {e}")
                    session.status = "failed"
                    return
            
            while iteration < max_iterations and session.status == "running":
                iteration += 1
                logger.info(f"Agent loop iteration {iteration} for session {session.session_id}")
                
                # Check if browser is still accessible
                try:
                    # Quick health check
                    await self.browser_service.get_page_info(include_dom=False, include_screenshot=False)
                except Exception as e:
                    logger.error(f"Browser health check failed: {e}")
                    session.status = "failed"
                    session.current_state = {'error': f"Browser not accessible: {e}"}
                    break
                
                # Get current state
                current_state = await self._get_current_state(session)
                if 'error' in current_state:
                    logger.error(f"Failed to get current state: {current_state['error']}")
                    session.status = "failed"
                    break
                
                # Decide next action
                available_tools = self.tool_service.get_tools_for_llm()
                action_decision = await self.llm_service.decide_next_action(
                    current_state,
                    available_tools,
                    session.task
                )
                
                # Check if human intervention is required
                if action_decision.get('action') == 'human_intervention_required' or \
                   (isinstance(action_decision, dict) and 
                    action_decision.get('decision', {}).get('action') == 'human_intervention_required'):
                    
                    # Extract intervention details
                    if isinstance(action_decision, dict) and 'decision' in action_decision:
                        intervention_params = action_decision['decision'].get('parameters', {})
                    else:
                        intervention_params = action_decision.get('parameters', {})
                    
                    reason = intervention_params.get('reason', 'Unknown reason')
                    message = intervention_params.get('message', 'Human intervention required')
                    action = intervention_params.get('action', 'wait_for_human')
                    resume_after = intervention_params.get('resume_after', 'action_complete')
                    
                    logger.info(f"Agent paused for human intervention: {reason}")
                    logger.info(f"Message: {message}")
                    logger.info(f"Resume after: {resume_after}")
                    
                    # Update session status
                    session.status = "paused_for_human_intervention"
                    session.current_state = {
                        'status': 'paused_for_human_intervention',
                        'reason': reason,
                        'message': message,
                        'action': action,
                        'resume_after': resume_after,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Add to task history
                    session.task_history.append({
                        'action': 'human_intervention_required',
                        'parameters': intervention_params,
                        'timestamp': datetime.now().isoformat(),
                        'status': 'paused'
                    })
                    
                    logger.info(f"Agent loop paused for session {session.session_id}")
                    return  # Exit the loop and wait for resume
                
                # Execute all suggested actions from the LLM
                action_results = await self._execute_all_actions(action_decision, session)
                
                # Add all actions to task history
                for action_result in action_results:
                    session.task_history.append({
                        'action': action_result.get('action', 'unknown'),
                        'parameters': action_result.get('parameters', {}),
                        'result': action_result.get('result', {}),
                        'timestamp': datetime.now().isoformat(),
                        'status': 'completed'
                    })
                
                # Get observation
                observation = await self._get_observation(session)
                if not observation or 'error' in observation:
                    logger.error(f"Failed to get observation: {observation}")
                    session.status = "failed"
                    break
                
                # Analyze observation
                analysis = await self.llm_service.analyze_observation(
                    observation,
                    session.task
                )
                
                # Check if task is complete
                if analysis.get('task_complete', False):
                    session.status = "completed"
                    logger.info(f"Task completed for session {session.session_id}")
                    break
                
                # Small delay to prevent rapid iterations
                await asyncio.sleep(1)
            
            if iteration >= max_iterations:
                session.status = "timeout"
                logger.warning(f"Agent loop timeout for session {session.session_id}")
            elif session.status == "running":
                session.status = "failed"
                logger.error(f"Agent loop failed for session {session.session_id}")
                
        except Exception as e:
            logger.error(f"Agent loop error for session {session.session_id}: {e}")
            session.status = "failed"
            session.current_state = {'error': str(e)}
        finally:
            # Ensure session status is properly set
            if session.status == "running":
                session.status = "failed"
            logger.info(f"Agent loop completed for session {session.session_id} with status: {session.status}")
    
    async def resume_after_human_intervention(self, session_id: str) -> Dict[str, Any]:
        """Resume agent execution after human intervention"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                return {"success": False, "error": "Session not found"}
            
            if session.status != "paused_for_human_intervention":
                return {"success": False, "error": "Session is not paused for human intervention"}
            
            logger.info(f"Resuming agent execution for session {session_id}")
            
            # Reset session status
            session.status = "running"
            session.current_state = {}
            
            # Continue the agent loop
            await self._run_agent_loop(session)
            
            return {
                "success": True,
                "session_id": session_id,
                "status": session.status,
                "message": "Agent execution resumed"
            }
            
        except Exception as e:
            logger.error(f"Failed to resume agent execution: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_current_state(self, session: SimpleAgentSession) -> Dict[str, Any]:
        """Get current browser state for the session"""
        try:
            # Get page information
            page_info_response = await self.browser_service.get_page_info(include_dom=True, include_screenshot=False)
            
            if not page_info_response.get('success'):
                return {'error': f"Failed to get page info: {page_info_response.get('error', 'Unknown error')}"}
            
            page_info = page_info_response.get('page_info', {})
            
            # Get browser state
            browser_state = {
                'url': page_info.get('url', 'Unknown'),
                'title': page_info.get('title', 'Unknown'),
                'timestamp': page_info.get('timestamp', datetime.now().isoformat())
            }
            
            # Get DOM information
            dom = page_info.get('dom', {})
            interactive_elements = dom.get('interactive_elements', [])
            page_structure = dom.get('page_structure', {})
            
            # Create current state
            current_state = {
                'browser_state': browser_state,
                'page_info': page_info,
                'dom': dom,
                'interactive_elements': interactive_elements,
                'page_structure': page_structure,
                'session_id': session.session_id,
                'task': session.task,
                'timestamp': datetime.now().isoformat()
            }
            
            return current_state
            
        except Exception as e:
            logger.error(f"Failed to get current state: {e}")
            return {'error': str(e)}
    
    async def _execute_all_actions(self, action_decision: Dict[str, Any], session: SimpleAgentSession) -> List[Dict[str, Any]]:
        """Execute all suggested actions from the LLM in sequence"""
        action_results = []
        
        try:
            logger.info(f"=== EXECUTING ALL ACTIONS ===")
            logger.info(f"Action decision structure: {action_decision}")
            
            # Get the analysis from the action decision
            analysis = None
            if "analysis" in action_decision:
                analysis = action_decision["analysis"]
            elif "decision" in action_decision and "analysis" in action_decision["decision"]:
                analysis = action_decision["decision"]["analysis"]
            
            if not analysis:
                logger.warning("No analysis found in action decision, falling back to single action execution")
                # Fallback to single action execution
                single_result = await self._execute_single_action(action_decision, session)
                return [single_result]
            
            # Get next steps from analysis
            next_steps = analysis.get("next_steps", [])
            logger.info(f"Found {len(next_steps)} next steps to execute: {next_steps}")
            
            # Execute each action in sequence
            for i, step in enumerate(next_steps):
                logger.info(f"Executing step {i+1}/{len(next_steps)}: {step}")
                
                # Parse the action from the step string
                parsed_action = self._parse_action_from_step(step)
                if not parsed_action:
                    logger.warning(f"Could not parse action from step: {step}")
                    continue
                
                # Execute the action
                action_result = await self._execute_single_action(parsed_action, session)
                action_results.append(action_result)
                
                # Small delay between actions
                if i < len(next_steps) - 1:  # Don't delay after the last action
                    await asyncio.sleep(0.5)
            
            logger.info(f"Completed execution of {len(action_results)} actions")
            return action_results
            
        except Exception as e:
            logger.error(f"Failed to execute all actions: {e}")
            return [{
                "success": False,
                "error": str(e),
                "action": "execute_all_actions"
            }]
    
    def _parse_action_from_step(self, step: str) -> Dict[str, Any]:
        """Parse action name and parameters from a step string"""
        try:
            # Handle different step formats
            if step.startswith("type_text("):
                # Parse: type_text("selector", "text")
                parts = step[10:-1].split(", ")  # Remove "type_text(" and ")"
                if len(parts) == 2:
                    selector = parts[0].strip('"')
                    text = parts[1].strip('"')
                    return {
                        "action": "type_text",
                        "parameters": {
                            "selector": selector,
                            "text": text
                        }
                    }
            
            elif step.startswith("click("):
                # Parse: click("selector")
                selector = step[6:-1].strip('"')  # Remove "click(" and ")"
                return {
                    "action": "click",
                    "parameters": {
                        "selector": selector
                    }
                }
            
            elif step.startswith("wait_for_element("):
                # Parse: wait_for_element("selector")
                selector = step[17:-1].strip('"')  # Remove "wait_for_element(" and ")"
                return {
                    "action": "wait_for_element",
                    "parameters": {
                        "selector": selector
                    }
                }
            
            elif step.startswith("navigate("):
                # Parse: navigate("url")
                url = step[9:-1].strip('"')  # Remove "navigate(" and ")"
                return {
                    "action": "navigate",
                    "parameters": {
                        "url": url
                    }
                }
            
            logger.warning(f"Unknown step format: {step}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse step '{step}': {e}")
            return None
    
    async def _execute_single_action(self, action_decision: Dict[str, Any], session: SimpleAgentSession) -> Dict[str, Any]:
        """Execute a single action"""
        try:
            logger.info(f"=== SINGLE ACTION EXECUTION ===")
            logger.info(f"Action decision structure: {action_decision}")
            
            # Handle different possible structures
            if "decision" in action_decision:
                decision = action_decision["decision"]
                action_name = decision["action"]
                parameters = decision["parameters"]
                logger.info(f"Using 'decision' structure: action={action_name}, parameters={parameters}")
            elif "action" in action_decision:
                action_name = action_decision["action"]
                parameters = action_decision.get("parameters", {})
                logger.info(f"Using direct structure: action={action_name}, parameters={parameters}")
            else:
                logger.error(f"Unknown action decision structure: {action_decision}")
                return {
                    "success": False,
                    "error": f"Unknown action decision structure: {action_decision}",
                    "action": "unknown"
                }
            
            # Execute the action using tool service
            action_result = await self.tool_service.execute_tool(action_name, **parameters)
            
            # Record the action
            if session.session_id in self.active_sessions:
                session = self.active_sessions[session.session_id]
                logger.info(f"Action executed: {action_name} with parameters: {parameters}")
            
            return {
                "success": True,
                "action": action_name,
                "parameters": parameters,
                "result": action_result,
                "execution_time_ms": action_result.get("execution_time_ms", 0)
            }
            
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": action_decision.get("action", "unknown")
            }
    
    async def _get_observation(self, session: SimpleAgentSession) -> Dict[str, Any]:
        """Get the current state of the browser for the LLM"""
        try:
            page_info = await self.browser_service.get_page_info(
                include_dom=True,
                include_screenshot=False
            )
            if not page_info["success"]:
                return {"error": "Failed to get page info"}
            
            return {
                "page_info": page_info["page_info"],
                "browser_state": {
                    "url": page_info["page_info"]["url"],
                    "title": page_info["page_info"]["title"],
                    "viewport": page_info["page_info"]["viewport_info"]
                }
            }
        except Exception as e:
            logger.error(f"Failed to get observation: {e}")
            return {"error": str(e)}
    
    async def _handle_action_failure(self, action_result: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle action failures and attempt recovery"""
        try:
            # Analyze the failure
            failure_analysis = await self.llm_service.analyze_observation(
                observation=action_result,
                task_context="Action failure recovery"
            )
            
            if not failure_analysis["success"]:
                return failure_analysis
            
            # Try alternative approaches based on analysis
            analysis = failure_analysis["analysis"]
            next_steps = analysis.get("next_steps", [])
            
            if next_steps:
                logger.info(f"Attempting recovery with next steps: {next_steps}")
                # Here you would implement recovery logic
                return {
                    "success": True,
                    "recovery_attempted": True,
                    "next_steps": next_steps
                }
            
            return {
                "success": False,
                "recovery_attempted": False,
                "error": "No recovery steps available"
            }
            
        except Exception as e:
            logger.error(f"Failure recovery failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_session_history(self, session_id: str) -> Dict[str, Any]:
        """Get the action and observation history for a session"""
        if session_id not in self.active_sessions:
            return {
                "success": False,
                "error": "Session not found"
            }
        
        # Here you would retrieve history from the database
        # For now, return basic session info
        session = self.active_sessions[session_id]
        
        return {
            "success": True,
            "session_id": session_id,
            "task": session.task,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "message": "History retrieval not yet implemented"
        }
    
    async def update_session_task(self, session_id: str, new_task: str) -> Dict[str, Any]:
        """Update the task for an existing session"""
        if session_id not in self.active_sessions:
            return {
                "success": False,
                "error": "Session not found"
            }
        
        session = self.active_sessions[session_id]
        session.task = new_task
        session.updated_at = datetime.utcnow()
        
        logger.info(f"Updated task for session {session_id}: {new_task[:50]}...")
        
        return {
            "success": True,
            "session_id": session_id,
            "new_task": new_task,
            "message": "Task updated successfully"
        }
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of all active sessions"""
        sessions = []
        for session_id, session in self.active_sessions.items():
            sessions.append({
                "session_id": session_id,
                "task": session.task,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            })
        
        return sessions
    
    async def cleanup(self):
        """Clean up agent service resources"""
        try:
            # Stop all active sessions
            for session_id in list(self.active_sessions.keys()):
                await self.stop_session(session_id)
            
            # Clean up browser service
            if self.browser_service:
                await self.browser_service.cleanup()
            
            logger.info("Agent service cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during agent service cleanup: {e}")
