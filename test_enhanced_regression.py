#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced regression analysis with status history.
"""

import json
from datetime import datetime

def create_mock_regression_data():
    """Create mock regression data to demonstrate the enhanced output."""
    return {
        "total_regressions": 3,
        "build_regressions": 1,
        "boot_regressions": 1,
        "test_regressions": 1,
        "regressions": {
            "builds": [
                {
                    "id": "build123",
                    "config": "defconfig",
                    "arch": "x86_64",
                    "compiler": "gcc-11",
                    "inconclusive": False,
                    "inconclusive_reason": "",
                    "status_history": None,
                    "status_history_display": ""
                }
            ],
            "boots": [
                {
                    "id": "boot456",
                    "test_path": "baseline.login.prompt",
                    "hardware": "qemu-x86_64-pc",
                    "config": "defconfig",
                    "arch": "x86_64",
                    "inconclusive": False,
                    "inconclusive_reason": "",
                    "status_history": [
                        {"status": "PASS", "timestamp": "2025-07-15T10:00:00"},
                        {"status": "PASS", "timestamp": "2025-07-15T12:00:00"},
                        {"status": "PASS", "timestamp": "2025-07-16T10:00:00"},
                        {"status": "FAIL", "timestamp": "2025-07-17T10:00:00"},
                    ],
                    "status_history_display": "✅ → ✅ → ✅ → ❌"
                }
            ],
            "tests": [
                {
                    "id": "test789",
                    "test_path": "kselftest.net.socket",
                    "hardware": "rk3588-rock-5b",
                    "config": "defconfig",
                    "arch": "arm64",
                    "inconclusive": True,
                    "inconclusive_reason": "Infrastructure error code",
                    "status_history": [
                        {"status": "PASS", "timestamp": "2025-07-15T10:00:00"},
                        {"status": "ERROR", "timestamp": "2025-07-15T12:00:00"},
                        {"status": "SKIP", "timestamp": "2025-07-16T10:00:00"},
                        {"status": "FAIL", "timestamp": "2025-07-17T10:00:00"},
                    ],
                    "status_history_display": "✅ → ⚠️ → ⚠️ → ❌"
                }
            ]
        }
    }

def format_regression_report(regression_data):
    """Format regression report similar to the enhanced trees script."""
    report = []
    
    report.append("🚨 DETAILED REGRESSION BREAKDOWN:")
    report.append("-" * 40)
    report.append("\n📍 next/master:")
    
    for reg_type in ["builds", "boots", "tests"]:
        regressions = regression_data["regressions"][reg_type]
        if regressions:
            report.append(f"  🔴 {reg_type.capitalize()} regressions ({len(regressions)}):")
            for i, reg in enumerate(regressions):
                # Determine status icon
                if reg.get("inconclusive", False):
                    status_icon = "⚠️"
                    status_text = f" (INCONCLUSIVE: {reg.get('inconclusive_reason', 'Unknown')})"
                else:
                    status_icon = "🔴"
                    status_text = ""

                if reg_type == "builds":
                    dashboard_link = f"https://d.kernelci.org/b/{reg['id']}"
                    report.append(
                        f"    {i+1}. {status_icon} {reg['config']} ({reg['arch']}, {reg['compiler']}){status_text}"
                    )
                    report.append(f"       🔗 {dashboard_link}")
                else:
                    dashboard_link = f"https://d.kernelci.org/t/{reg['id']}"
                    report.append(
                        f"    {i+1}. {status_icon} {reg['test_path']} on {reg['hardware']}{status_text}"
                    )
                    report.append(f"       🔗 {dashboard_link}")
                    
                    # Add status history for boots and tests
                    if reg.get("status_history_display"):
                        report.append(f"       📊 History: {reg['status_history_display']}")
    
    return "\n".join(report)

def main():
    """Demonstrate the enhanced regression analysis output."""
    print("🧪 Enhanced Trees Regression Analysis Demo")
    print("=" * 60)
    print()
    
    # Simulate the script startup
    print("🚀 Starting Trees Regression Analysis")
    print(f"📅 Analysis started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Origin: maestro")
    print("📊 Status history: Enabled (will fetch test status history with emojis)")
    print("📊 Staging API: Accessible")
    print("=" * 80)
    print()
    
    # Simulate analysis
    print("🔍 Analyzing next/master...")
    print("  Running: https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git --branch master --origin maestro --json")
    print("  🔍 Fetching details for 1 builds regressions...")
    print("  🔍 Fetching details for 1 boots regressions...")
    print("    📊 Fetched status history for boot456")
    print("  🔍 Fetching details for 1 tests regressions...")
    print("    📊 Fetched status history for test789")
    print("  ❌ REGRESSIONS FOUND - 3 total regressions")
    print()
    
    # Create and display the regression report
    mock_data = create_mock_regression_data()
    report = format_regression_report(mock_data)
    print(report)
    
    print("\n" + "=" * 60)
    print("\n📊 Status History Legend:")
    print("✅ = PASS")
    print("❌ = FAIL")
    print("⚠️ = INCONCLUSIVE (ERROR, SKIP, MISS, etc.)")
    print("→ = Direction of time (oldest → newest)")
    print("\n🔍 Analysis Notes:")
    print("- Boot regression shows clear pattern: ✅ → ✅ → ✅ → ❌ (recent failure)")
    print("- Test regression shows infrastructure issues: ✅ → ⚠️ → ⚠️ → ❌ (marked inconclusive)")
    print("- Build regression has no history (builds don't use status history API)")

if __name__ == "__main__":
    main()