#!/usr/bin/env python3
"""
Step-by-step API testing script for Browser Use Agent
This script tests each API endpoint individually with clear instructions
"""

import asyncio
import requests
import json
import time
from typing import Dict, Any


class APITester:
    """Step-by-step API tester for Browser Use Agent"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
        self.test_results = []
    
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        print()
    
    def test_health_endpoint(self):
        """Test the health check endpoint"""
        print("🔍 Testing Health Endpoint")
        print("-" * 40)
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Check", True, f"Status: {data.get('status')}")
                return True
            else:
                self.log_test("Health Check", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Error: {str(e)}")
            return False
    
    def test_browser_navigation(self):
        """Test browser navigation endpoint"""
        print("🌐 Testing Browser Navigation")
        print("-" * 40)
        
        try:
            # Test navigation to a simple page
            data = {"url": "https://httpbin.org/html"}
            response = requests.post(f"{self.base_url}/browser/navigate", json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.log_test("Browser Navigation", True, f"Navigated to: {data['url']}")
                    return True
                else:
                    self.log_test("Browser Navigation", False, f"Navigation failed: {result.get('error')}")
                    return False
            else:
                self.log_test("Browser Navigation", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Browser Navigation", False, f"Error: {str(e)}")
            return False
    
    def test_browser_page_info(self):
        """Test getting page information"""
        print("📄 Testing Page Info Endpoint")
        print("-" * 40)
        
        try:
            response = requests.post(f"{self.base_url}/browser/page-info", json={}, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    page_info = result.get("page_info", {})
                    self.log_test("Page Info", True, f"Title: {page_info.get('title', 'N/A')}")
                    return True
                else:
                    self.log_test("Page Info", False, f"Failed: {result.get('error')}")
                    return False
            else:
                self.log_test("Page Info", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Page Info", False, f"Error: {str(e)}")
            return False
    
    def test_agent_session_start(self):
        """Test starting an agent session"""
        print("🚀 Testing Agent Session Start")
        print("-" * 40)
        
        try:
            data = {
                "task": "Test task: Navigate to a website and get page title",
                "initial_url": "https://httpbin.org/html"
            }
            
            response = requests.post(f"{self.base_url}/agent/start", json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.session_id = result.get("session_id")
                    self.log_test("Agent Session Start", True, f"Session ID: {self.session_id}")
                    return True
                else:
                    self.log_test("Agent Session Start", False, f"Failed: {result.get('error')}")
                    return False
            else:
                self.log_test("Agent Session Start", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Agent Session Start", False, f"Error: {str(e)}")
            return False
    
    def test_agent_session_status(self):
        """Test getting agent session status"""
        print("📊 Testing Agent Session Status")
        print("-" * 40)
        
        if not self.session_id:
            self.log_test("Agent Session Status", False, "No session ID available")
            return False
        
        try:
            response = requests.get(f"{self.base_url}/agent/{self.session_id}/status", timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    status = result.get("status", "unknown")
                    self.log_test("Agent Session Status", True, f"Status: {status}")
                    return True
                else:
                    self.log_test("Agent Session Status", False, f"Failed: {result.get('error')}")
                    return False
            else:
                self.log_test("Agent Session Status", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Agent Session Status", False, f"Error: {str(e)}")
            return False
    
    def test_agent_session_history(self):
        """Test getting agent session history"""
        print("📚 Testing Agent Session History")
        print("-" * 40)
        
        if not self.session_id:
            self.log_test("Agent Session History", False, "No session ID available")
            return False
        
        try:
            response = requests.get(f"{self.base_url}/agent/{self.session_id}/history", timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.log_test("Agent Session History", True, "History retrieved successfully")
                    return True
                else:
                    self.log_test("Agent Session History", False, f"Failed: {result.get('error')}")
                    return False
            else:
                self.log_test("Agent Session History", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Agent Session History", False, f"Error: {str(e)}")
            return False
    
    def test_agent_session_stop(self):
        """Test stopping an agent session"""
        print("🛑 Testing Agent Session Stop")
        print("-" * 40)
        
        if not self.session_id:
            self.log_test("Agent Session Stop", False, "No session ID available")
            return False
        
        try:
            response = requests.post(f"{self.base_url}/agent/{self.session_id}/stop", timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.log_test("Agent Session Stop", True, "Session stopped successfully")
                    return True
                else:
                    self.log_test("Agent Session Stop", False, f"Failed: {result.get('error')}")
                    return False
            else:
                self.log_test("Agent Session Stop", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Agent Session Stop", False, f"Error: {str(e)}")
            return False
    
    def test_browser_click(self):
        """Test browser click functionality"""
        print("🖱️ Testing Browser Click")
        print("-" * 40)
        
        try:
            # First navigate to a page with clickable elements
            nav_data = {"url": "https://httpbin.org/forms/post"}
            nav_response = requests.post(f"{self.base_url}/browser/navigate", json=nav_data, timeout=30)
            
            if nav_response.status_code != 200:
                self.log_test("Browser Click", False, "Navigation failed")
                return False
            
            # Wait a moment for the page to load and verify we're on the right page
            import time
            time.sleep(3)
            
            # Verify we're on the right page
            page_response = requests.post(f"{self.base_url}/browser/page-info", json={}, timeout=30)
            if page_response.status_code == 200:
                page_data = page_response.json()
                if page_data.get("success") and "httpbin.org/forms/post" in page_data.get("page_info", {}).get("url", ""):
                    print(f"   ✅ Page loaded: {page_data['page_info']['url']}")
                else:
                    self.log_test("Browser Click", False, "Page navigation verification failed")
                    return False
            else:
                self.log_test("Browser Click", False, "Could not verify page info")
                return False
            
            # Try to click on a form element (use a more specific selector)
            click_data = {"selector": "input[type='email']"}
            response = requests.post(f"{self.base_url}/browser/click", json=click_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.log_test("Browser Click", True, "Click action successful")
                    return True
                else:
                    self.log_test("Browser Click", False, f"Click failed: {result.get('error')}")
                    return False
            else:
                self.log_test("Browser Click", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Browser Click", False, f"Error: {str(e)}")
            return False
    
    def test_browser_type(self):
        """Test browser type functionality"""
        print("⌨️ Testing Browser Type")
        print("-" * 40)
        
        try:
            # Navigate to a form page
            nav_data = {"url": "https://httpbin.org/forms/post"}
            nav_response = requests.post(f"{self.base_url}/browser/navigate", json=nav_data, timeout=30)
            
            if nav_response.status_code != 200:
                self.log_test("Browser Type", False, "Navigation failed")
                return False
            
            # Wait a moment for the page to load and verify we're on the right page
            import time
            time.sleep(3)
            
            # Verify we're on the right page
            page_response = requests.post(f"{self.base_url}/browser/page-info", json={}, timeout=30)
            if page_response.status_code == 200:
                page_data = page_response.json()
                if page_data.get("success") and "httpbin.org/forms/post" in page_data.get("page_info", {}).get("url", ""):
                    print(f"   ✅ Page loaded: {page_data['page_info']['url']}")
                else:
                    self.log_test("Browser Type", False, "Page navigation verification failed")
                    return False
            else:
                self.log_test("Browser Type", False, "Could not verify page info")
                return False
            
            # Try to type in a form field (use a more specific selector)
            type_data = {"selector": "input[type='email']", "text": "test@example.com"}
            response = requests.post(f"{self.base_url}/browser/type", json=type_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.log_test("Browser Type", True, "Type action successful")
                    return True
                else:
                    self.log_test("Browser Type", False, f"Type failed: {result.get('error')}")
                    return False
            else:
                self.log_test("Browser Type", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Browser Type", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all API tests in sequence"""
        print("🧪 Browser Use Agent - API Testing Suite")
        print("=" * 60)
        print(f"Testing API at: {self.base_url}")
        print()
        
        # Test basic endpoints first
        self.test_health_endpoint()
        
        # Test browser functionality
        self.test_browser_navigation()
        self.test_browser_page_info()
        self.test_browser_click()
        self.test_browser_type()
        
        # Test agent functionality
        self.test_agent_session_start()
        self.test_agent_session_status()
        self.test_agent_session_history()
        self.test_agent_session_stop()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("📊 Test Results Summary")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n" + "=" * 60)


def main():
    """Main function"""
    print("🚀 Starting Browser Use Agent API Testing...")
    print()
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Browser Use Agent API is not responding correctly")
            print("Please make sure the server is running with: python start.py")
            return
    except requests.exceptions.RequestException:
        print("❌ Browser Use Agent API is not running")
        print("Please start the API first with: python start.py")
        return
    
    print("✅ Browser Use Agent API is running")
    print()
    
    # Run tests
    tester = APITester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
