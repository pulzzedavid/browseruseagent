#!/usr/bin/env python3
"""
Example usage of the Browser Use Agent
"""

import asyncio
import requests
import json
import time
from typing import Dict, Any


class BrowserUseAgentClient:
    """Client for interacting with the Browser Use Agent API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
    
    def start_session(self, task: str, initial_url: str = None) -> Dict[str, Any]:
        """Start a new agent session"""
        url = f"{self.base_url}/agent/start"
        data = {
            "task": task,
            "initial_url": initial_url
        }
        
        response = requests.post(url, json=data)
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            self.session_id = result["session_id"]
            print(f"✅ Session started: {self.session_id}")
            print(f"Task: {task}")
            if initial_url:
                print(f"Initial URL: {initial_url}")
        else:
            print(f"❌ Failed to start session: {result.get('error')}")
        
        return result
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get the current session status"""
        if not self.session_id:
            print("❌ No active session")
            return {}
        
        url = f"{self.base_url}/agent/{self.session_id}/status"
        response = requests.get(url)
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            print(f"📊 Session Status: {result['status']}")
            print(f"Task: {result['task']}")
            print(f"Created: {result['created_at']}")
            print(f"Updated: {result['updated_at']}")
        else:
            print(f"❌ Failed to get status: {result.get('error')}")
        
        return result
    
    def wait_for_completion(self, max_wait_time: int = 300, check_interval: int = 5):
        """Wait for the session to complete"""
        if not self.session_id:
            print("❌ No active session")
            return
        
        print(f"⏳ Waiting for session completion (max {max_wait_time}s)...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            status_result = self.get_session_status()
            
            if not status_result or not status_result.get("success"):
                print("❌ Failed to get status")
                break
            
            status = status_result["status"]
            if status in ["completed", "failed", "stopped"]:
                print(f"🏁 Session {status}!")
                break
            
            print(f"⏳ Still running... ({status})")
            time.sleep(check_interval)
        else:
            print("⏰ Timeout waiting for completion")
    
    def stop_session(self) -> Dict[str, Any]:
        """Stop the current session"""
        if not self.session_id:
            print("❌ No active session")
            return {}
        
        url = f"{self.base_url}/agent/{self.session_id}/stop"
        response = requests.post(url)
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            print(f"🛑 Session stopped: {result['message']}")
        else:
            print(f"❌ Failed to stop session: {result.get('error')}")
        
        return result
    
    def get_session_history(self) -> Dict[str, Any]:
        """Get the session history"""
        if not self.session_id:
            print("❌ No active session")
            return {}
        
        url = f"{self.base_url}/agent/{self.session_id}/history"
        response = requests.get(url)
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            print(f"📚 Session History:")
            print(f"  Task: {result['task']}")
            print(f"  Status: {result['status']}")
            print(f"  Message: {result['message']}")
        else:
            print(f"❌ Failed to get history: {result.get('error')}")
        
        return result
    
    def update_task(self, new_task: str) -> Dict[str, Any]:
        """Update the session task"""
        if not self.session_id:
            print("❌ No active session")
            return {}
        
        url = f"{self.base_url}/agent/{self.session_id}/task"
        data = {"new_task": new_task}
        
        response = requests.put(url, json=data)
        response.raise_for_status()
        
        result = response.json()
        if result["success"]:
            print(f"✏️ Task updated: {new_task}")
        else:
            print(f"❌ Failed to update task: {result.get('error')}")
        
        return result


async def example_basic_usage():
    """Example of basic agent usage"""
    print("🚀 Browser Use Agent - Basic Usage Example")
    print("=" * 50)
    
    # Create client
    client = BrowserUseAgentClient()
    
    # Example 1: Simple web search
    print("\n📝 Example 1: Web Search")
    print("-" * 30)
    
    task = "Go to Google and search for 'Python programming tutorials'"
    initial_url = "https://www.google.com"
    
    # Start session
    client.start_session(task, initial_url)
    
    # Wait a bit for the agent to start working
    print("⏳ Waiting for agent to start...")
    time.sleep(2)
    
    # Check status
    client.get_session_status()
    
    # Wait for completion (with shorter timeout for demo)
    client.wait_for_completion(max_wait_time=60, check_interval=3)
    
    # Get history
    client.get_session_history()
    
    # Stop session
    client.stop_session()
    
    print("\n" + "=" * 50)


async def example_form_filling():
    """Example of form filling task"""
    print("\n📝 Example 2: Form Filling")
    print("-" * 30)
    
    client = BrowserUseAgentClient()
    
    task = "Go to a contact form page and fill out the form with sample data"
    initial_url = "https://httpbin.org/forms/post"
    
    # Start session
    client.start_session(task, initial_url)
    
    # Wait for completion
    client.wait_for_completion(max_wait_time=60, check_interval=3)
    
    # Get history
    client.get_session_history()
    
    # Stop session
    client.stop_session()
    
    print("\n" + "=" * 50)


async def example_e_commerce():
    """Example of e-commerce browsing task"""
    print("\n📝 Example 3: E-commerce Browsing")
    print("-" * 30)
    
    client = BrowserUseAgentClient()
    
    task = "Go to an e-commerce site, browse products, and add an item to cart"
    initial_url = "https://demo.opencart.com"
    
    # Start session
    client.start_session(task, initial_url)
    
    # Wait for completion
    client.wait_for_completion(max_wait_time=60, check_interval=3)
    
    # Get history
    client.get_session_history()
    
    # Stop session
    client.stop_session()
    
    print("\n" + "=" * 50)


async def main():
    """Run all examples"""
    try:
        # Check if the API is running
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("✅ Browser Use Agent API is running")
            else:
                print("❌ Browser Use Agent API is not responding correctly")
                return
        except requests.exceptions.RequestException:
            print("❌ Browser Use Agent API is not running")
            print("Please start the API first with: uvicorn app.main:app --reload")
            return
        
        # Run examples
        await example_basic_usage()
        await example_form_filling()
        await example_e_commerce()
        
        print("\n🎉 All examples completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())
