#!/usr/bin/env python3
"""
Test script to demonstrate the status history formatting with arrows.
"""

def format_status_history_demo(history_data):
    """Demonstrate the status history formatting."""
    status_emojis = []
    for entry in history_data:
        status = entry.get('status', '').upper()
        if status == 'PASS':
            status_emojis.append('✅')
        elif status == 'FAIL':
            status_emojis.append('❌')
        else:
            status_emojis.append('⚠️')  # inconclusive
    
    # Join with arrows to show direction (oldest → newest)
    return ' → '.join(status_emojis)

# Test scenarios
test_scenarios = [
    {
        "name": "Stable test - all passing",
        "history": [
            {"status": "PASS", "timestamp": "2025-07-17T10:00:00"},
            {"status": "PASS", "timestamp": "2025-07-17T11:00:00"},
            {"status": "PASS", "timestamp": "2025-07-17T12:00:00"},
            {"status": "PASS", "timestamp": "2025-07-17T13:00:00"},
        ]
    },
    {
        "name": "Clear regression - PASS to FAIL",
        "history": [
            {"status": "PASS", "timestamp": "2025-07-17T10:00:00"},
            {"status": "PASS", "timestamp": "2025-07-17T11:00:00"},
            {"status": "PASS", "timestamp": "2025-07-17T12:00:00"},
            {"status": "FAIL", "timestamp": "2025-07-17T13:00:00"},
        ]
    },
    {
        "name": "Flaky test - mixed results",
        "history": [
            {"status": "PASS", "timestamp": "2025-07-17T10:00:00"},
            {"status": "FAIL", "timestamp": "2025-07-17T11:00:00"},
            {"status": "PASS", "timestamp": "2025-07-17T12:00:00"},
            {"status": "FAIL", "timestamp": "2025-07-17T13:00:00"},
        ]
    },
    {
        "name": "Infrastructure issues - inconclusive results",
        "history": [
            {"status": "PASS", "timestamp": "2025-07-17T10:00:00"},
            {"status": "ERROR", "timestamp": "2025-07-17T11:00:00"},
            {"status": "SKIP", "timestamp": "2025-07-17T12:00:00"},
            {"status": "MISS", "timestamp": "2025-07-17T13:00:00"},
        ]
    },
    {
        "name": "Recovery pattern - failure then recovery",
        "history": [
            {"status": "FAIL", "timestamp": "2025-07-17T10:00:00"},
            {"status": "FAIL", "timestamp": "2025-07-17T11:00:00"},
            {"status": "PASS", "timestamp": "2025-07-17T12:00:00"},
            {"status": "PASS", "timestamp": "2025-07-17T13:00:00"},
        ]
    }
]

print("🧪 Status History Demo with Arrows")
print("=" * 50)
print()

for scenario in test_scenarios:
    history_display = format_status_history_demo(scenario["history"])
    print(f"📊 {scenario['name']}:")
    print(f"   History: {history_display}")
    print()

print("Legend:")
print("✅ = PASS")
print("❌ = FAIL") 
print("⚠️ = INCONCLUSIVE (ERROR, SKIP, MISS, etc.)")
print("→ = Direction of time (oldest → newest)")