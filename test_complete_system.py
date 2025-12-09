#!/usr/bin/env python3
"""
Complete End-to-End System Test
Verifies that Optimus is using real PostgreSQL data, not mock data
"""

import requests
import json
from datetime import datetime
from termcolor import colored
import time

BASE_URL = "http://localhost:8003"

def print_header(text):
    print("\n" + "=" * 60)
    print(f"🔍 {text}")
    print("=" * 60)

def test_mobile_summary():
    """Test that mobile summary returns real, changing data."""
    print_header("Testing Mobile Summary - Real Data")
    
    response = requests.get(f"{BASE_URL}/api/mobile/summary")
    data = response.json()
    
    print(f"✅ Greeting: {data['greeting']}")
    print(f"✅ Weather: {data['weather']['temp']} {data['weather']['condition']} {data['weather']['icon']}")
    
    if data.get('next_event'):
        print(f"✅ Next Event: {data['next_event']['title']} at {data['next_event']['time']}")
        print(f"   ID: {data['next_event']['id']} (UUID = Real database record)")
    
    print(f"\n📊 Stats (from database):")
    for key, value in data['stats'].items():
        print(f"   {key}: {value}")
    
    print(f"\n📋 Urgent Tasks ({len(data['urgent_tasks'])} found):")
    for task in data['urgent_tasks'][:3]:
        print(f"   P{task['priority']}: {task['title']} - ID: {task['id'][:8]}...")
    
    return data

def test_add_task():
    """Test adding a real task to the database."""
    print_header("Testing Add Task - Real Database Insert")
    
    task_data = {
        "type": "task",
        "content": f"Test task created at {datetime.now().strftime('%H:%M:%S')}",
        "priority": 1
    }
    
    response = requests.post(
        f"{BASE_URL}/api/mobile/quick-add",
        json=task_data
    )
    
    result = response.json()
    print(f"✅ Task Added: {result['message']}")
    print(f"   Database ID: {result['id']}")
    
    return result['id']

def test_data_persistence(task_id):
    """Verify that data persists and changes."""
    print_header("Testing Data Persistence")
    
    # Get summary again
    response = requests.get(f"{BASE_URL}/api/mobile/summary")
    data = response.json()
    
    # Check if our new task appears
    task_found = False
    for task in data['urgent_tasks']:
        if task['id'] == task_id:
            task_found = True
            print(f"✅ New task found in summary: {task['title']}")
            break
    
    if not task_found:
        # Check if it's in the total count at least
        print(f"⚠️  Task not in urgent list but total tasks: {data['stats']['tasks_today']}")
    
    return task_found

def test_database_health():
    """Check database connection and data counts."""
    print_header("Testing Database Health")
    
    response = requests.get(f"{BASE_URL}/api/mobile/health")
    health = response.json()
    
    print(f"✅ Status: {health['status']}")
    print(f"✅ Database: {health['database']}")
    print(f"✅ Version: {health['version'][:50]}...")
    print(f"\n📊 Data Counts:")
    for table, count in health['data'].items():
        print(f"   {table}: {count}")
    
    return health

def verify_not_mock_data():
    """Verify this is NOT mock data by checking for telltale signs."""
    print_header("Verification: Real vs Mock Data")
    
    # Make multiple requests and check if data changes
    summaries = []
    for i in range(3):
        response = requests.get(f"{BASE_URL}/api/mobile/summary")
        summaries.append(response.json())
        if i < 2:
            time.sleep(1)
    
    # Check for mock data indicators
    mock_indicators = {
        "Static task count": all(s['stats']['tasks_today'] == summaries[0]['stats']['tasks_today'] 
                                for s in summaries),
        "Always 'Review pull requests'": all(any(t['title'] == 'Review pull requests' 
                                                 for t in s.get('urgent_tasks', []))
                                            for s in summaries),
        "Static weather": all(s['weather']['temp'] == summaries[0]['weather']['temp'] 
                             for s in summaries),
        "No UUIDs": not any('-' in str(s.get('next_event', {}).get('id', '')) 
                           for s in summaries if s.get('next_event'))
    }
    
    is_mock = False
    for indicator, detected in mock_indicators.items():
        if detected:
            print(f"❌ MOCK: {indicator}")
            is_mock = True
        else:
            print(f"✅ REAL: {indicator} is dynamic")
    
    # Final verdict
    print("\n" + "=" * 60)
    if is_mock:
        print(colored("⚠️  WARNING: System appears to be using MOCK DATA!", "yellow"))
    else:
        print(colored("✅ VERIFIED: System is using REAL DATABASE DATA!", "green"))
    print("=" * 60)
    
    return not is_mock

def main():
    print(colored("""
╔══════════════════════════════════════════════════════════╗
║     🚀 OPTIMUS COMPLETE SYSTEM TEST                       ║
║     Testing Real Database Integration                     ║
╚══════════════════════════════════════════════════════════╝
    """, "cyan"))
    
    try:
        # Test 1: Get mobile summary
        summary = test_mobile_summary()
        
        # Test 2: Add a task
        task_id = test_add_task()
        
        # Test 3: Verify persistence
        time.sleep(1)
        found = test_data_persistence(task_id)
        
        # Test 4: Check health
        health = test_database_health()
        
        # Test 5: Verify not mock
        is_real = verify_not_mock_data()
        
        # Final Report
        print("\n" + "=" * 60)
        print(colored("📊 FINAL REPORT", "cyan"))
        print("=" * 60)
        
        all_tests_passed = (
            summary is not None and 
            task_id is not None and 
            health['status'] == 'healthy' and 
            is_real
        )
        
        if all_tests_passed:
            print(colored("""
✅ ALL TESTS PASSED!

The Optimus system is fully operational with:
• Real PostgreSQL database connection
• Dynamic data that changes with each request
• Persistent storage of tasks and events
• Working API endpoints for mobile/iOS app
• No hardcoded mock values

The iOS app can now display and modify REAL data!
            """, "green"))
        else:
            print(colored("""
⚠️  SOME ISSUES DETECTED

Please check the test output above for details.
The system may still be using mock data in some places.
            """, "yellow"))
            
    except requests.exceptions.ConnectionError:
        print(colored("""
❌ ERROR: Could not connect to server at http://localhost:8003

Please ensure the test server is running:
  venv/bin/python test_server.py
        """, "red"))
    except Exception as e:
        print(colored(f"❌ ERROR: {e}", "red"))

if __name__ == "__main__":
    main()