#!/usr/bin/env python3
"""
Trees Regression Analysis

This script automatically runs regression analysis across multiple kernel tree branches
using kci-dev results compare command and provides a comprehensive summary report.

Features:
- Fetches test status history from main dashboard API (when accessible)
- Displays status history with emojis: ✅ pass, ❌ fail, ⚠️ inconclusive
- Shows chronological progression with arrows: ✅ → ❌ → ✅ → ❌
- Provides comprehensive regression analysis with infrastructure detection
- Supports multiple output formats (human-readable and JSON)

Note: Status history requires access to dashboard.kernelci.org/api/test/{id}/status_history/.
If the dashboard API is not accessible, the script will continue without history.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

# =============================================================================
# CONFIGURATION SECTION
# =============================================================================

# KernelCI settings
KCIDB_ORIGIN = "maestro"
COMMAND_TIMEOUT = 120  # seconds

# Output settings
SHOW_DETAILED_SUMMARY = True
SAVE_JSON_OUTPUT = True
JSON_OUTPUT_DIR = "./regression_reports"

# =============================================================================
# REGRESSION ANALYSIS FUNCTIONS
# =============================================================================


class RegressionAnalyzer:
    def __init__(self, tree_branches: Dict, fetch_status_history: bool = True):
        self.tree_branches = tree_branches
        self.results = {}
        self.start_time = datetime.now()
        self.dashboard_api_base = "https://dashboard.kernelci.org/api/"
        self.fetch_status_history = fetch_status_history

    def run_kci_compare(
        self, giturl: str, branch: str
    ) -> Tuple[bool, Optional[Dict], str]:
        """Run kci-dev results compare for a specific branch."""
        cmd = [
            "poetry",
            "run",
            "kci-dev",
            "results",
            "compare",
            "--giturl",
            giturl,
            "--branch",
            branch,
            "--origin",
            KCIDB_ORIGIN,
            "--json",
        ]

        try:
            print(f"  Running: {' '.join(cmd[-6:])}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT,
                cwd=os.getcwd(),
            )

            if result.returncode == 0:
                # Parse JSON from the last line (after the summary table)
                lines = result.stdout.strip().split("\n")
                json_line = None
                for line in reversed(lines):
                    if line.strip().startswith("{"):
                        json_line = line.strip()
                        break

                if json_line:
                    regression_data = json.loads(json_line)
                    return True, regression_data, result.stdout
                else:
                    return False, None, f"No JSON output found in stdout"
            else:
                error_msg = result.stderr or result.stdout
                return (
                    False,
                    None,
                    f"Command failed (code {result.returncode}): {error_msg}",
                )

        except subprocess.TimeoutExpired:
            return False, None, f"Command timed out after {COMMAND_TIMEOUT} seconds"
        except json.JSONDecodeError as e:
            return False, None, f"JSON parsing error: {e}"
        except Exception as e:
            return False, None, f"Unexpected error: {e}"

    def fetch_dashboard_details(self, node_id: str, node_type: str) -> Optional[Dict]:
        """Fetch detailed information from dashboard API for a specific node."""
        try:
            if node_type == "builds":
                endpoint = f"{self.dashboard_api_base}build/{node_id}"
            else:  # tests, boots
                endpoint = f"{self.dashboard_api_base}test/{node_id}"

            response = requests.get(endpoint, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(
                    f"  ⚠️  Failed to fetch details for {node_id}: HTTP {response.status_code}"
                )
                return None
        except requests.RequestException as e:
            print(f"  ⚠️  API request failed for {node_id}: {e}")
            return None
        except Exception as e:
            print(f"  ⚠️  Unexpected error fetching {node_id}: {e}")
            return None

    def fetch_test_status_history(self, node_id: str) -> Optional[List[Dict]]:
        """Fetch test status history from main dashboard API."""
        try:
            endpoint = f"{self.dashboard_api_base}test/{node_id}/status_history/"
            response = requests.get(endpoint, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                # Test ID not found - this is expected for some tests
                return None
            else:
                print(
                    f"  ⚠️  Failed to fetch status history for {node_id}: HTTP {response.status_code}"
                )
                return None
        except requests.exceptions.ConnectionError:
            # Dashboard API might not be accessible from this environment
            print(f"  ⚠️  Dashboard API not accessible - status history unavailable")
            return None
        except requests.exceptions.Timeout:
            print(f"  ⚠️  Timeout fetching status history for {node_id}")
            return None
        except requests.RequestException as e:
            print(f"  ⚠️  Status history API request failed for {node_id}: {e}")
            return None
        except Exception as e:
            print(f"  ⚠️  Unexpected error fetching status history for {node_id}: {e}")
            return None

    def format_status_history(self, history: List[Dict]) -> str:
        """Format test status history with emojis and arrows."""
        if not history:
            return "No history available"
        
        # Sort by timestamp (most recent first)
        sorted_history = sorted(history, key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Take only the last 10 entries to keep it manageable
        recent_history = sorted_history[:10]
        
        status_emojis = []
        for entry in reversed(recent_history):  # Reverse to show oldest to newest
            status = entry.get('status', '').upper()
            if status == 'PASS':
                status_emojis.append('✅')
            elif status == 'FAIL':
                status_emojis.append('❌')
            else:
                status_emojis.append('⚠️')  # inconclusive (all other statuses)
        
        # Join with arrows to show direction (oldest → newest)
        return ' → '.join(status_emojis)

    def is_infrastructure_error_msg(self, error_msg: str) -> bool:
        """Check if error message indicates infrastructure issues."""
        infrastructure_keywords = [
            "infrastructure",
            "timeout",
            "cancelled",
            "connection",
            "network",
            "unavailable",
            "unreachable",
            "disconnected",
            "interrupted",
            "aborted",
            "killed",
            "terminated",
            "resource",
            "capacity",
            "quota",
            "limit",
            "overload",
            "maintenance",
            "offline",
            "down",
            "failure",
            "crash",
            "socket",
            "broken pipe",
            "connection reset",
            "dns",
            "certificate",
            "ssl",
            "tls",
            "authentication failed",
            "out of memory",
            "oom",
            "disk full",
            "no space left",
            "permission denied",
            "access denied",
            "forbidden",
            "unable",
            "invalid",
        ]

        error_msg_lower = error_msg.lower()
        return any(keyword in error_msg_lower for keyword in infrastructure_keywords)

    def analyze_regression_details(self, regression: Dict, reg_type: str) -> Dict:
        """Analyze regression details and determine if it's inconclusive."""
        enhanced_regression = regression.copy()
        enhanced_regression["inconclusive"] = False
        enhanced_regression["inconclusive_reason"] = ""
        enhanced_regression["dashboard_details"] = None
        enhanced_regression["status_history"] = None
        enhanced_regression["status_history_display"] = ""

        node_id = regression.get("id")
        if not node_id:
            return enhanced_regression

        # Fetch detailed information from dashboard API
        details = self.fetch_dashboard_details(node_id, reg_type)
        if details:
            enhanced_regression["dashboard_details"] = details

            # For boots and tests, fetch status history if enabled
            if reg_type in ["boots", "tests"] and self.fetch_status_history:
                status_history = self.fetch_test_status_history(node_id)
                if status_history:
                    enhanced_regression["status_history"] = status_history
                    enhanced_regression["status_history_display"] = self.format_status_history(status_history)

            # Check for inconclusive conditions based on API response fields
            if reg_type in ["boots", "tests"]:
                status = details.get("status", "")

                # Check for error_code and error_msg in both top level and misc
                error_code = details.get("error_code", "")
                error_msg = details.get("error_msg", "")

                # Also check in misc object if not found at top level
                misc = details.get("misc", {})
                if not error_code and misc:
                    error_code = misc.get("error_code", "")
                if not error_msg and misc:
                    error_msg = misc.get("error_msg", "")

                # Check for Infrastructure error_code
                if error_code == "Infrastructure":
                    enhanced_regression["inconclusive"] = True
                    enhanced_regression["inconclusive_reason"] = (
                        "Infrastructure error code"
                    )

                # Check for Job errors with infrastructure-related error messages
                elif error_code == "Job" and error_msg:
                    if self.is_infrastructure_error_msg(error_msg):
                        enhanced_regression["inconclusive"] = True
                        enhanced_regression["inconclusive_reason"] = (
                            f"Job error with infrastructure issue: {error_msg[:100]}..."
                        )

                # Check for other problematic statuses
                elif status in ["MISS", "ERROR", "SKIP"]:
                    enhanced_regression["inconclusive"] = True
                    enhanced_regression["inconclusive_reason"] = (
                        f"Test status: {status}"
                    )

            elif reg_type == "builds":
                status = details.get("status", "")

                # Check for error_code and error_msg in both top level and misc
                error_code = details.get("error_code", "")
                error_msg = details.get("error_msg", "")

                # Also check in misc object if not found at top level
                misc = details.get("misc", {})
                if not error_code and misc:
                    error_code = misc.get("error_code", "")
                if not error_msg and misc:
                    error_msg = misc.get("error_msg", "")

                # Check for Infrastructure error_code
                if error_code == "Infrastructure":
                    enhanced_regression["inconclusive"] = True
                    enhanced_regression["inconclusive_reason"] = (
                        "Infrastructure error code"
                    )

                # Check for Job errors with infrastructure-related error messages
                elif error_code == "Job" and error_msg:
                    if self.is_infrastructure_error_msg(error_msg):
                        enhanced_regression["inconclusive"] = True
                        enhanced_regression["inconclusive_reason"] = (
                            f"Job error with infrastructure issue: {error_msg[:100]}..."
                        )

                # Check for other problematic build statuses
                elif status in ["MISS", "ERROR", "SKIP"]:
                    enhanced_regression["inconclusive"] = True
                    enhanced_regression["inconclusive_reason"] = (
                        f"Build status: {status}"
                    )

        return enhanced_regression

    def analyze_branch(self, tree_branch_key: str, config: Dict) -> Dict:
        """Analyze a single tree branch for regressions."""
        print(f"\n🔍 Analyzing {tree_branch_key}...")

        branch_result = {
            "tree_branch_key": tree_branch_key,
            "config": config,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "regression_data": None,
            "error": None,
            "commits_analyzed": None,
            "summary": {
                "total_regressions": 0,
                "build_regressions": 0,
                "boot_regressions": 0,
                "test_regressions": 0,
            },
        }

        giturl = config["giturl"]
        branch = config["branch"]
        success, regression_data, output = self.run_kci_compare(giturl, branch)

        if success and regression_data:
            branch_result["success"] = True

            # Enhance regressions with detailed information
            enhanced_regression_data = regression_data.copy()
            for reg_type in ["builds", "boots", "tests"]:
                if reg_type in enhanced_regression_data.get("regressions", {}):
                    enhanced_regressions = []
                    regressions = enhanced_regression_data["regressions"][reg_type]

                    if regressions:
                        print(
                            f"  🔍 Fetching details for {len(regressions)} {reg_type} regressions..."
                        )

                        for regression in regressions:
                            enhanced_regression = self.analyze_regression_details(
                                regression, reg_type
                            )
                            enhanced_regressions.append(enhanced_regression)
                            
                            # Show progress for status history fetching
                            if self.fetch_status_history and reg_type in ["boots", "tests"] and enhanced_regression.get("status_history_display"):
                                print(f"    📊 Fetched status history for {regression.get('id', 'unknown')}")

                    enhanced_regression_data["regressions"][
                        reg_type
                    ] = enhanced_regressions

            branch_result["regression_data"] = enhanced_regression_data
            # Calculate inconclusive statistics
            inconclusive_stats = {
                "total_inconclusive": 0,
                "build_inconclusive": 0,
                "boot_inconclusive": 0,
                "test_inconclusive": 0,
            }

            for reg_type in ["builds", "boots", "tests"]:
                if reg_type in enhanced_regression_data.get("regressions", {}):
                    regressions = enhanced_regression_data["regressions"][reg_type]
                    inconclusive_count = sum(
                        1 for reg in regressions if reg.get("inconclusive", False)
                    )
                    inconclusive_stats[f"{reg_type[:-1]}_inconclusive"] = (
                        inconclusive_count
                    )
                    inconclusive_stats["total_inconclusive"] += inconclusive_count

            branch_result["summary"] = {
                "total_regressions": enhanced_regression_data.get(
                    "total_regressions", 0
                ),
                "build_regressions": enhanced_regression_data.get(
                    "build_regressions", 0
                ),
                "boot_regressions": enhanced_regression_data.get("boot_regressions", 0),
                "test_regressions": enhanced_regression_data.get("test_regressions", 0),
                **inconclusive_stats,
            }

            # Extract commit info from output
            lines = output.split("\n")
            for line in lines:
                if "Latest:" in line and "Previous:" in line:
                    break
                elif "Latest:" in line:
                    branch_result["commits_analyzed"] = line.strip()

            status = (
                "✅ CLEAN"
                if regression_data["total_regressions"] == 0
                else "❌ REGRESSIONS FOUND"
            )
            print(
                f"  {status} - {regression_data['total_regressions']} total regressions"
            )

        else:
            branch_result["error"] = output
            print(f"  ❌ FAILED - {output}")

        return branch_result

    def run_analysis(self) -> Dict:
        """Run regression analysis for all configured tree branches."""
        print("🚀 Starting Trees Regression Analysis")
        print(
            f"📅 Analysis started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"🎯 Origin: {KCIDB_ORIGIN}")
        if self.fetch_status_history:
            print("📊 Status history: Enabled (will fetch test status history with emojis)")
            # Test dashboard API availability for status history
            try:
                response = requests.get(f"{self.dashboard_api_base}test/", timeout=5)
                if response.status_code in [200, 404]:
                    print("📊 Dashboard API: Accessible")
                else:
                    print("📊 Dashboard API: Limited accessibility")
            except:
                print("📊 Dashboard API: Not accessible - history will be unavailable")
        else:
            print("📊 Status history: Disabled (faster analysis)")
        print("=" * 80)

        for tree_branch_key, config in self.tree_branches.items():
            if not config.get("active", True):
                print(f"\n⏭️  Skipping {tree_branch_key} (disabled in config)")
                continue

            branch_result = self.analyze_branch(tree_branch_key, config)
            self.results[tree_branch_key] = branch_result

        return self.results

    def generate_summary_report(self) -> str:
        """Generate a human-readable summary report."""
        end_time = datetime.now()
        duration = end_time - self.start_time

        report = []
        report.append("📊 TREES REGRESSION ANALYSIS SUMMARY")
        report.append("=" * 60)
        report.append(f"🕐 Analysis Duration: {duration.total_seconds():.1f} seconds")
        report.append(f"📅 Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Overall status
        total_regressions = sum(
            result["summary"]["total_regressions"]
            for result in self.results.values()
            if result["success"]
        )

        total_inconclusive = sum(
            result["summary"].get("total_inconclusive", 0)
            for result in self.results.values()
            if result["success"]
        )

        if total_regressions == 0:
            report.append(
                "🎉 OVERALL STATUS: ALL BRANCHES CLEAN - NO REGRESSIONS DETECTED"
            )
        else:
            status_msg = (
                f"⚠️  OVERALL STATUS: {total_regressions} TOTAL REGRESSIONS FOUND"
            )
            if total_inconclusive > 0:
                status_msg += f" ({total_inconclusive} INCONCLUSIVE)"
            report.append(status_msg)

        report.append("")
        report.append("📋 BRANCH RESULTS:")
        report.append("-" * 40)

        # List all branches
        for tree_branch_key, result in self.results.items():
            if result["success"]:
                regressions = result["summary"]["total_regressions"]
                status_icon = "✅" if regressions == 0 else "❌"

                report.append(f"  {status_icon} {tree_branch_key}")
                if regressions > 0:
                    summary = result["summary"]
                    inconclusive_total = summary.get("total_inconclusive", 0)

                    regression_summary = (
                        f"    📊 Builds: {summary['build_regressions']}, "
                        f"Boots: {summary['boot_regressions']}, "
                        f"Tests: {summary['test_regressions']}"
                    )

                    if inconclusive_total > 0:
                        inconclusive_summary = (
                            f"    ⚠️  Inconclusive: {summary.get('build_inconclusive', 0)} builds, "
                            f"{summary.get('boot_inconclusive', 0)} boots, "
                            f"{summary.get('test_inconclusive', 0)} tests"
                        )
                        report.append(regression_summary)
                        report.append(inconclusive_summary)
                    else:
                        report.append(regression_summary)

                if SHOW_DETAILED_SUMMARY and result.get("commits_analyzed"):
                    report.append(f"    📝 {result['commits_analyzed']}")
            else:
                report.append(f"  ❌ {tree_branch_key} - ANALYSIS FAILED")
                report.append(f"    🔍 Error: {result['error'][:100]}...")

        # Detailed regressions if any found
        regression_branches = [
            (tree_branch_key, result)
            for tree_branch_key, result in self.results.items()
            if result["success"] and result["summary"]["total_regressions"] > 0
        ]

        if regression_branches:
            report.append("\n🚨 DETAILED REGRESSION BREAKDOWN:")
            report.append("-" * 40)

            for tree_branch_key, result in regression_branches:
                regression_data = result["regression_data"]
                report.append(f"\n📍 {tree_branch_key}:")

                for reg_type in ["builds", "boots", "tests"]:
                    regressions = regression_data["regressions"][reg_type]
                    if regressions:
                        report.append(
                            f"  🔴 {reg_type.capitalize()} regressions ({len(regressions)}):"
                        )
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

        report.append("\n" + "=" * 60)
        return "\n".join(report)

    def save_json_report(self, filename: Optional[str] = None) -> str:
        """Save detailed JSON report to file."""
        if not SAVE_JSON_OUTPUT:
            return ""

        import os

        os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)

        if filename is None:
            timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
            filename = f"trees_regression_analysis_{timestamp}.json"

        filepath = os.path.join(JSON_OUTPUT_DIR, filename)

        report_data = {
            "analysis_metadata": {
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "origin": KCIDB_ORIGIN,
                "branches_analyzed": len(self.results),
            },
            "results": self.results,
            "summary": {
                "total_regressions": sum(
                    result["summary"]["total_regressions"]
                    for result in self.results.values()
                    if result["success"]
                ),
                "successful_analyses": sum(
                    1 for result in self.results.values() if result["success"]
                ),
                "failed_analyses": sum(
                    1 for result in self.results.values() if not result["success"]
                ),
            },
        }

        with open(filepath, "w") as f:
            json.dump(report_data, f, indent=2)

        return filepath


def load_tree_config(config_path: str) -> Dict:
    """Load tree configuration from JSON file."""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in config file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading config file: {e}")
        sys.exit(1)


def main():
    """Main function to run the regression analysis."""
    parser = argparse.ArgumentParser(
        description="Run regression analysis across multiple kernel tree branches"
    )
    parser.add_argument(
        "--config",
        "-c",
        default="trees_config.json",
        help="Path to trees configuration JSON file (default: trees_config.json)",
    )
    parser.add_argument(
        "--origin", default="maestro", help="KCIDB origin to use (default: maestro)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Command timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--no-json", action="store_true", help="Disable JSON report output"
    )
    parser.add_argument(
        "--json-dir",
        default="./regression_reports",
        help="Directory to save JSON reports (default: ./regression_reports)",
    )
    parser.add_argument(
        "--tree",
        "-t",
        action="append",
        help="Specific tree/branch to analyze (e.g., android/android13-5.15-lts). Can be used multiple times. If not specified, all active trees from config will be analyzed.",
    )
    parser.add_argument(
        "--no-status-history", 
        action="store_true", 
        help="Skip fetching test status history (faster but less detailed)"
    )

    args = parser.parse_args()

    # Update global settings from command line arguments
    global KCIDB_ORIGIN, COMMAND_TIMEOUT, SAVE_JSON_OUTPUT, JSON_OUTPUT_DIR
    KCIDB_ORIGIN = args.origin
    COMMAND_TIMEOUT = args.timeout
    SAVE_JSON_OUTPUT = not args.no_json
    JSON_OUTPUT_DIR = args.json_dir

    # Load tree configuration
    tree_branches = load_tree_config(args.config)

    # Filter trees if specific trees are requested
    if args.tree:
        filtered_trees = {}
        for tree_name in args.tree:
            if tree_name in tree_branches:
                filtered_trees[tree_name] = tree_branches[tree_name]
            else:
                print(f"⚠️  Warning: Tree '{tree_name}' not found in config file")
                available_trees = list(tree_branches.keys())
                print(
                    f"Available trees: {', '.join(available_trees[:5])}{'...' if len(available_trees) > 5 else ''}"
                )

        if not filtered_trees:
            print("❌ Error: No valid trees found to analyze")
            sys.exit(1)

        tree_branches = filtered_trees
        print(
            f"🎯 Analyzing {len(tree_branches)} specific tree(s): {', '.join(tree_branches.keys())}"
        )
    else:
        active_trees = {k: v for k, v in tree_branches.items() if v.get("active", True)}
        print(f"🎯 Analyzing {len(active_trees)} active trees from config")

    try:
        analyzer = RegressionAnalyzer(tree_branches, fetch_status_history=not args.no_status_history)
        analyzer.run_analysis()

        # Generate and display summary
        summary_report = analyzer.generate_summary_report()
        print("\n" + summary_report)

        # Save JSON report
        if SAVE_JSON_OUTPUT:
            json_file = analyzer.save_json_report()
            print(f"\n💾 Detailed JSON report saved to: {json_file}")

        # Exit with appropriate code
        total_regressions = sum(
            result["summary"]["total_regressions"]
            for result in analyzer.results.values()
            if result["success"]
        )

        if total_regressions > 0:
            print(f"\n⚠️  Exiting with code 1 - {total_regressions} regressions found")
            sys.exit(1)
        else:
            print("\n✅ Exiting with code 0 - No regressions detected")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n❌ Analysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
