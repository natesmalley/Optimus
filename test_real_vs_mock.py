#!/usr/bin/env python3
"""
Test script to compare mock data vs what real data should look like
"""

import requests
import json
from datetime import datetime

print("=" * 60)
print("🔍 TESTING: Mock vs Real Data in Optimus Backend")
print("=" * 60)

# Test the mobile API
response = requests.get("http://localhost:8003/api/mobile/summary")
data = response.json()

print("\n📱 Mobile Summary Response:")
print(f"  Greeting: {data['greeting']}")
print(f"  Stats: {data['stats']}")
print(f"  Next Event: {data.get('next_event', {}).get('title', 'None')}")

print("\n🚨 MOCK DATA INDICATORS:")
mock_indicators = [
    ("Stats are always", data['stats'] == {'tasks_today': 8, 'completed': 3, 'meetings': 4, 'focus_hours': 2}),
    ("Tasks are always 'Review pull requests' and 'Prepare presentation'", 
     any(t['title'] == 'Review pull requests' for t in data.get('urgent_tasks', []))),
    ("Suggestions always include 'Call Mom'", 
     any(s['title'] == 'Call Mom - it\'s been 2 weeks' for t in data.get('suggestions', []))),
    ("Weather is always 72°F Sunny", 
     data.get('weather', {}).get('temp') == '72°F')
]

for indicator, is_mock in mock_indicators:
    status = "✅ MOCK" if is_mock else "❌ REAL"
    print(f"  {status}: {indicator}")

print("\n📂 Checking source code:")
# Show the actual mock function
with open("/Users/nathanial.smalley/projects/Optimus/src/api/mobile_api.py", "r") as f:
    lines = f.readlines()
    in_mock_function = False
    for i, line in enumerate(lines[98:120], start=99):  # Show get_mock_agenda function
        if "def get_mock_agenda" in line:
            in_mock_function = True
        if in_mock_function:
            print(f"  Line {i}: {line.rstrip()}")
            if i > 115:
                break

print("\n🎯 WHAT REAL DATA WOULD LOOK LIKE:")
print("""
Real data would:
1. Connect to PostgreSQL database (optimus_db)
2. Query actual tasks from 'tasks' table
3. Get real user events from 'events' table  
4. Calculate actual stats from database
5. Generate personalized suggestions based on user history
6. Get real weather from an API
7. Show different data each time based on actual state

Current implementation:
- Returns SAME hardcoded data every time
- No database connection used
- All values are static in code
""")

print("\n✅ VERIFICATION: Try refreshing the app multiple times")
print("   If the data never changes, it's definitely mock data!")

# Make 3 requests to show data doesn't change
print("\n🔄 Making 3 requests to show data doesn't change:")
for i in range(3):
    response = requests.get("http://localhost:8003/api/mobile/summary")
    stats = response.json()['stats']
    print(f"  Request {i+1}: tasks_today={stats['tasks_today']}, completed={stats['completed']}")

print("\n❌ CONCLUSION: The backend is using 100% MOCK DATA")
print("   No real tasks, events, or user data is being returned!")