#!/usr/bin/env python3
"""
Data Analysis Script for KernelCI Dashboard API

This script pulls boot results data from the KernelCI Dashboard API for analysis.
It finds the second most recent mainline/master checkout and retrieves all boot results.

API Documentation: https://dashboard.kernelci.org/api/schema/swagger-ui/#/

Usage:
    python data_analysis.py
    poetry run python data_analysis.py
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any

import requests


class KernelCIDataAnalyzer:
    """Analyzer for KernelCI boot results data."""
    
    def __init__(self, base_url: str = "https://dashboard.kernelci.org/api", show_full: bool = False, hist_size: int = 10, test_path: str = "boot"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 30
        self.show_full = show_full
        self.hist_size = hist_size
        self.test_path = test_path
        
        # Mainline repository configuration
        self.mainline_url = "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git"
        self.mainline_branch = "master"
    
    def get_trees(self, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """Get all available trees from the API."""
        try:
            params = {"limit": limit}
            response = self.session.get(f"{self.base_url}/tree/", params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Error fetching trees: {e}")
            return None
    
    def find_mainline_tree(self, trees: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the mainline tree from the list of trees."""
        for tree in trees:
            if (tree.get("git_repository_url") == self.mainline_url and 
                tree.get("git_repository_branch") == self.mainline_branch):
                return tree
        return None
    
    def get_tree_commits(self, tree_id: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """Get recent commits for a specific tree."""
        try:
            params = {"limit": limit}
            response = self.session.get(f"{self.base_url}/tree/{tree_id}/commits", params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Error fetching commits for tree {tree_id}: {e}")
            return None
    
    def get_boot_status_from_tree(self, tree: Dict[str, Any]) -> Dict[str, Any]:
        """Extract boot status information from tree data."""
        boot_status = tree.get('boot_status', {})
        if not boot_status:
            return None
        
        return {
            'tree_info': {
                'commit_hash': tree.get('git_commit_hash'),
                'commit_name': tree.get('git_commit_name'),
                'repository': tree.get('git_repository_url'),
                'branch': tree.get('git_repository_branch'),
                'start_time': tree.get('start_time'),
                'tree_id': tree.get('id')
            },
            'boot_status': boot_status,
            'total_boots': sum(boot_status.values())
        }
    
    def get_detailed_test_results(self, tree_info: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Get detailed test results for a specific tree using correct API parameters."""
        commit_hash = tree_info.get('commit_hash')
        git_url = tree_info.get('repository')
        git_branch = tree_info.get('branch')
        
        if not all([commit_hash, git_url, git_branch]):
            print(f"  ❌ Missing required parameters: commit_hash={commit_hash}, git_url={git_url}, git_branch={git_branch}")
            return []
        
        # Choose endpoint based on test path
        if self.test_path == "boot":
            endpoint = f"{self.base_url}/tree/{commit_hash}/boots"
        else:
            endpoint = f"{self.base_url}/tree/{commit_hash}/tests"
        
        params = {
            'git_url': git_url,
            'git_branch': git_branch,
            'origin': 'maestro'
        }
        
        # Add path filter for non-boot tests
        if self.test_path != "boot":
            params['path'] = self.test_path
        
        try:
            print(f"  🔗 Trying: {endpoint}")
            print(f"     📋 Params: {params}")
            response = self.session.get(endpoint, params=params)
            
            if response.status_code == 200:
                result = response.json()
                
                # Check for error in response
                if isinstance(result, dict) and 'error' in result:
                    print(f"  ⚠️  API Error: {result['error']}")
                    return []
                
                # Handle different response formats
                if isinstance(result, list):
                    test_type_label = self.test_path if self.test_path != "boot" else "boot"
                    print(f"  ✅ Success: Found {len(result)} {test_type_label} results")
                    return result
                elif isinstance(result, dict):
                    # Check for 'boots' key (KernelCI format for boot tests)
                    if 'boots' in result:
                        test_results = result['boots']
                        if isinstance(test_results, list):
                            print(f"  ✅ Success: Found {len(test_results)} boot results")
                            return test_results
                    # Check for 'tests' key (KernelCI format for non-boot tests)
                    elif 'tests' in result:
                        test_results = result['tests']
                        if isinstance(test_results, list):
                            test_type_label = self.test_path if self.test_path != "boot" else "test"
                            print(f"  ✅ Success: Found {len(test_results)} {test_type_label} results")
                            return test_results
                    # Check for 'results' key (alternative format)
                    elif 'results' in result:
                        test_results = result['results']
                        if isinstance(test_results, list):
                            test_type_label = self.test_path if self.test_path != "boot" else "result"
                            print(f"  ✅ Success: Found {len(test_results)} {test_type_label} results")
                            return test_results
                
                print(f"  ⚠️  Unexpected response format. Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                return []
            else:
                print(f"  ❌ HTTP {response.status_code}: {response.text[:100]}")
                return []
                
        except requests.RequestException as e:
            print(f"  ❌ Request failed: {e}")
            return []
    
    def analyze_boot_status(self, boot_status_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze boot status data from tree information."""
        boot_status = boot_status_data['boot_status']
        total_boots = boot_status_data['total_boots']
        
        analysis = {
            "total_boots": total_boots,
            "status_breakdown": boot_status,
            "tree_info": boot_status_data['tree_info']
        }
        
        return analysis
    
    def print_boot_status_summary(self, analysis: Dict[str, Any]):
        """Print a formatted summary of the boot status analysis."""
        print("\n" + "="*80)
        print("📊 BOOT STATUS ANALYSIS SUMMARY")
        print("="*80)
        
        # Tree/Commit information
        tree_info = analysis["tree_info"]
        print(f"🔍 Commit: {tree_info['commit_hash'][:12] if tree_info['commit_hash'] else 'Unknown'}")
        print(f"📅 Date: {tree_info.get('start_time', 'Unknown')}")
        print(f"📂 Repository: {tree_info.get('repository', 'Unknown')}")
        print(f"🌿 Branch: {tree_info.get('branch', 'Unknown')}")
        print(f"💬 Name: {tree_info.get('commit_name', 'No name available')}")
        print()
        
        # Boot results summary
        total_boots = analysis["total_boots"]
        print(f"🥾 Total Boot Tests: {total_boots}")
        
        if total_boots == 0:
            print("⚠️  No boot results found for this tree")
            return
        
        print("\n📈 BOOT STATUS BREAKDOWN:")
        print("-" * 50)
        status_counts = analysis["status_breakdown"]
        
        # Define status icons and order
        status_mapping = {
            'pass': ('✅', 'PASS'),
            'fail': ('❌', 'FAIL'), 
            'error': ('💥', 'ERROR'),
            'miss': ('❓', 'MISS'),
            'skip': ('⏭️', 'SKIP'),
            'done': ('✔️', 'DONE'),
            'null': ('⚪', 'NULL')
        }
        
        for status_key, count in sorted(status_counts.items()):
            if count > 0:
                percentage = (count / total_boots) * 100
                icon, display_name = status_mapping.get(status_key.lower(), ('⚠️', status_key.upper()))
                print(f"  {icon} {display_name:>8}: {count:>4} ({percentage:>5.1f}%)")
        
        print("\n" + "="*80)
    
    def get_status_icon(self, status: str) -> str:
        """Get emoji icon for boot status."""
        status_lower = status.lower()
        status_mapping = {
            'pass': '✅',
            'fail': '❌', 
            'error': '💥',
            'miss': '❓',
            'skip': '⏭️',
            'done': '✔️',
            'null': '⚪'
        }
        return status_mapping.get(status_lower, '⚠️')
    
    def fetch_dashboard_details(self, node_id: str, node_type: str = "test") -> Optional[Dict]:
        """Fetch detailed information from dashboard API for a specific node."""
        try:
            if node_type == "build":
                endpoint = f"{self.base_url}/build/{node_id}"
            else:  # tests, boots
                endpoint = f"{self.base_url}/test/{node_id}"

            response = self.session.get(endpoint, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except requests.RequestException:
            return None
        except Exception:
            return None

    def fetch_test_status_history(self, node_id: str, details: Dict = None) -> Optional[List[Dict]]:
        """Fetch test status history from main dashboard API."""
        try:
            endpoint = f"{self.base_url}/test/status-history"

            # Build parameters based on the actual structure from details
            params = {
                'origin': 'maestro',
                'limit': self.hist_size
            }
            
            # Add parameters using correct field mapping
            if details:
                # Use config field (not config_name)
                if 'config_name' in details:
                    params['config_name'] = details['config_name']
                    
                # Extract platform from environment_misc if it exists there
                if 'environment_misc' in details and isinstance(details['environment_misc'], dict):
                    if 'platform' in details['environment_misc']:
                        params['platform'] = details['environment_misc']['platform']
                    
                # Add other standard parameters
                if 'path' in details:
                    params['path'] = details['path']
                if 'git_repository_url' in details:
                    params['git_repository_url'] = details['git_repository_url']
                if 'git_repository_branch' in details:
                    params['git_repository_branch'] = details['git_repository_branch']
                if details and 'field_timestamp' in details:
                    params['field_timestamp'] = details['field_timestamp']
                if details and 'start_time' in details:
                    params['current_test_start_time'] = details['start_time']
            
            response = self.session.get(endpoint, params=params, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                return data
            elif response.status_code == 400:
                # Check if it's specifically "Test status history not found"
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict) and 'error' in error_data:
                        if 'not found' in error_data['error'].lower():
                            # This is normal - not all tests have status history
                            return None
                except:
                    pass
                # Other 400 errors
                if not hasattr(self, '_api_400_warning_shown'):
                    print(f"  ℹ️  Status history not available for some tests (HTTP 400)")
                    self._api_400_warning_shown = True
                return None
            elif response.status_code == 403:
                # API requires authentication
                if not hasattr(self, '_api_auth_warning_shown'):
                    print("  ⚠️  Dashboard API requires authentication - status history unavailable")
                    self._api_auth_warning_shown = True
                return None
            elif response.status_code == 404:
                # Test ID not found - this is common
                if not hasattr(self, '_api_404_count'):
                    self._api_404_count = 0
                self._api_404_count += 1
                return None
            else:
                if not hasattr(self, '_api_error_warning_shown'):
                    print(f"  ⚠️  Dashboard API status history unavailable (HTTP {response.status_code})")
                    self._api_error_warning_shown = True
                return None
        except requests.exceptions.ConnectionError:
            # Dashboard API might not be accessible from this environment
            if not hasattr(self, '_connection_warning_shown'):
                print("  ⚠️  Dashboard API not accessible - status history unavailable")
                self._connection_warning_shown = True
            return None
        except requests.exceptions.Timeout:
            if not hasattr(self, '_timeout_warning_shown'):
                print("  ⚠️  Dashboard API timeout - status history unavailable")
                self._timeout_warning_shown = True
            return None
        except requests.RequestException:
            if not hasattr(self, '_request_error_warning_shown'):
                print("  ⚠️  Dashboard API request failed - status history unavailable")
                self._request_error_warning_shown = True
            return None
        except Exception:
            if not hasattr(self, '_unexpected_error_warning_shown'):
                print("  ⚠️  Unexpected error fetching status history - feature unavailable")
                self._unexpected_error_warning_shown = True
            return None

    def format_status_history(self, history_data: Dict) -> str:
        """Format test status history with emojis and arrows."""
        # Extract the actual history list from the response
        if isinstance(history_data, dict) and 'status_history' in history_data:
            history = history_data['status_history']
        elif isinstance(history_data, list):
            history = history_data
        else:
            return "No history available"
        
        if not history:
            return "No history available"
        
        # Sort by start_time (most recent first)
        sorted_history = sorted(history, key=lambda x: x.get('start_time', ''), reverse=True)
        
        # Take only the last 10 entries to keep it manageable
        recent_history = sorted_history[:10]
        
        status_emojis = []
        for entry in reversed(recent_history):  # Reverse to show oldest to newest
            status = entry.get('status', '')
            if status is None:
                status = ''
            status = status.upper()
            if status == 'PASS':
                status_emojis.append('✅')
            elif status == 'FAIL':
                status_emojis.append('❌')
            else:
                status_emojis.append('⚠️')  # inconclusive (all other statuses)
        
        # Join with arrows to show direction (oldest → newest)
        return ' → '.join(status_emojis)
    
    def analyze_test_results(self, tests: List[Dict[str, Any]], tree_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results data for non-boot tests."""
        # Count tests by status
        status_counts = {}
        for test in tests:
            status = test.get('status', 'unknown').lower()
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_tests": len(tests),
            "status_breakdown": status_counts,
            "tree_info": tree_info,
            "detailed_tests": tests
        }
        
    def print_test_status_summary(self, analysis: Dict[str, Any]):
        """Print a formatted summary of the test status analysis."""
        print("\n" + "="*80)
        test_type_title = f"{self.test_path.upper()} TEST" if self.test_path != "boot" else "BOOT"
        print(f"📊 {test_type_title} STATUS ANALYSIS SUMMARY")
        print("="*80)
        
        # Tree/Commit information
        tree_info = analysis["tree_info"]
        print(f"🔍 Commit: {tree_info['commit_hash'][:12] if tree_info['commit_hash'] else 'Unknown'}")
        print(f"📅 Date: {tree_info.get('start_time', 'Unknown')}")
        print(f"📂 Repository: {tree_info.get('repository', 'Unknown')}")
        print(f"🌿 Branch: {tree_info.get('branch', 'Unknown')}")
        print(f"💬 Name: {tree_info.get('commit_name', 'No name available')}")
        print()
        
        # Test results summary
        total_tests = analysis["total_tests"]
        test_type_label = f"{self.test_path} Tests" if self.test_path != "boot" else "Boot Tests"
        print(f"🧪 Total {test_type_label}: {total_tests}")
        
        if total_tests == 0:
            print(f"⚠️  No {self.test_path} test results found for this tree")
            return
        
        print(f"\n📈 {test_type_title} STATUS BREAKDOWN:")
        print("-" * 50)
        status_counts = analysis["status_breakdown"]
        
        # Define status icons and order
        status_mapping = {
            'pass': ('✅', 'PASS'),
            'fail': ('❌', 'FAIL'), 
            'error': ('💥', 'ERROR'),
            'miss': ('❓', 'MISS'),
            'skip': ('⏭️', 'SKIP'),
            'done': ('✔️', 'DONE'),
            'null': ('⚪', 'NULL')
        }
        
        for status_key, count in sorted(status_counts.items()):
            if count > 0:
                percentage = (count / total_tests) * 100
                icon, display_name = status_mapping.get(status_key.lower(), ('⚠️', status_key.upper()))
                print(f"  {icon} {display_name:>8}: {count:>4} ({percentage:>5.1f}%)")
        
        print("\n" + "="*80)
        
    def print_full_test_details(self, analysis: Dict[str, Any]):
        """Print detailed information for each test result."""
        if not self.show_full:
            return
            
        detailed_tests = analysis["detailed_tests"]
        
        print("\n" + "="*80)
        test_type_title = "BOOT RESULTS" if self.test_path == "boot" else f"TEST RESULTS ({self.test_path.upper()})"
        print(f"🔍 DETAILED {test_type_title}")
        print("="*80)
        
        # Group tests by status for better organization
        tests_by_status = {}
        for test in detailed_tests:
            status = test.get('status', 'unknown').lower()
            if status not in tests_by_status:
                tests_by_status[status] = []
            tests_by_status[status].append(test)
        
        # Display tests grouped by status
        for status, tests in sorted(tests_by_status.items()):
            if not tests:
                continue
                
            status_icon = self.get_status_icon(status)
            test_type = "tests" if self.test_path != "boot" else "boots"
            print(f"\n{status_icon} {status.upper()} ({len(tests)} {test_type}):")
            print("-" * 50)
            
            # Show only first 3 tests of each status type
            for i, test in enumerate(tests[:3], 1):
                test_details = self.fetch_dashboard_details(test['id'])
                
                # Create dashboard link (for tests/boots, use 't' endpoint)
                dashboard_link = f"https://d.kernelci.org/t/{test['id']}"
                
                print(f"  {i:2d}.  {status_icon} {dashboard_link}")
                
                # Fetch and display status history for this test if we have detailed info
                if test_details:
                    status_history = self.fetch_test_status_history(test['id'], test_details)
                    if status_history:
                        history_display = self.format_status_history(status_history)
                        if history_display != "No history available":
                            print(f"      📊 History: {history_display}")
            
            # Show count of remaining tests if there are more than 3
            if len(tests) > 3:
                print(f"      ... and {len(tests) - 3} more {status.upper()} {test_type}")
        
        print("\n" + "="*80)
    
    def print_full_boot_details(self, analysis: Dict[str, Any], show_full: bool = False):
        """Print detailed information for each boot result (legacy method for boot tests only)."""
        if not show_full:
            return
            
        tree_info = analysis["tree_info"]
        
        print("\n" + "="*80)
        print(f"🔍 DETAILED RESULTS")
        print("="*80)
        print(f"📡 Fetching detailed records...")
        
        detailed_tests = self.get_detailed_test_results(tree_info)
            
        print(f"✅ Found {len(detailed_tests)} detailed test records\n")
        
        # Group tests by status for better organization
        tests_by_status = {}
        for test in detailed_tests:
            status = test.get('status', 'unknown').lower()
            if status not in tests_by_status:
                tests_by_status[status] = []
            tests_by_status[status].append(test)
        
        # Display tests grouped by status
        for status, tests in sorted(tests_by_status.items()):
            if not tests:
                continue
                
            status_icon = self.get_status_icon(status)
            print(f"\n{status_icon} {status.upper()} ({len(tests)} boots):")
            print("-" * 50)
            
            # Show only first 3 tests of each status type
            for i, test in enumerate(tests[:3], 1):
                test_details = self.fetch_dashboard_details(test['id'])
                
                # Create dashboard link (for tests/boots, use 't' endpoint)
                dashboard_link = f"https://d.kernelci.org/t/{test['id']}"
                
                print(f"  {i:2d}.  {status_icon} {dashboard_link}")
                
                # Fetch and display status history for this test if we have detailed info
                if test_details:
                    status_history = self.fetch_test_status_history(test['id'], test_details)
                    if status_history:
                        history_display = self.format_status_history(status_history)
                        if history_display != "No history available":
                            print(f"      📊 History: {history_display}")
            
            # Show count of remaining tests if there are more than 3
            if len(tests) > 3:
                print(f"      ... and {len(tests) - 3} more {status.upper()} boots")
        
        print("\n" + "="*80)

    
    def find_tree_with_boot_status(self, trees: List[Dict[str, Any]], max_attempts: int = 5) -> Optional[Dict[str, Any]]:
        """Find a tree that has boot status data available."""
        print(f"🔍 Searching for tree with boot status (checking up to {max_attempts} trees)...")
        
        for i, tree in enumerate(trees[:max_attempts]):
            commit_hash = tree.get("git_commit_hash", "unknown")
            boot_status = tree.get("boot_status", {})
            total_boots = sum(boot_status.values()) if boot_status else 0
            
            print(f"  📋 Checking tree {i+1}/{min(len(trees), max_attempts)}: {commit_hash[:12]}... ({total_boots} boots)")
            
            if total_boots > 0:
                boot_status_data = self.get_boot_status_from_tree(tree)
                if boot_status_data:
                    print(f"  ✅ Found tree with {total_boots} boot results")
                    return boot_status_data
                
        print(f"  ⚠️  No trees with boot status found in the {max_attempts} most recent trees")
        return None

    def run_analysis(self) -> bool:
        """Run the complete data analysis workflow."""
        test_type_title = "Boot Results" if self.test_path == "boot" else f"Test Results ({self.test_path})"
        print(f"🚀 Starting KernelCI {test_type_title} Analysis")
        print(f"📍 Preferred target: {self.mainline_url} ({self.mainline_branch})")
        print("="*80)
        
        # Step 1: Get all trees
        print("🌳 Fetching available trees...")
        trees = self.get_trees()
        if not trees:
            print("❌ Failed to fetch trees")
            return False
        
        print(f"✅ Found {len(trees)} trees")
        
        # Step 2: Find mainline trees (there might be multiple recent commits)
        print("🔍 Looking for mainline trees...")
        mainline_trees = [tree for tree in trees 
                         if (tree.get("git_repository_url") == self.mainline_url and 
                             tree.get("git_repository_branch") == self.mainline_branch)]
        
        if not mainline_trees:
            print("⚠️  No mainline trees found")
            return False
            
        # Sort by start_time to get the most recent order
        mainline_trees.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        print(f"✅ Found {len(mainline_trees)} mainline trees")
        
        # For boot tests, use the existing workflow with boot status summary
        if self.test_path == "boot":
            return self.run_boot_analysis(mainline_trees)
        else:
            return self.run_test_analysis(mainline_trees)
        
    def run_boot_analysis(self, mainline_trees: List[Dict[str, Any]]) -> bool:
        """Run analysis workflow for boot tests using boot status summary."""
        # Step 3: Find a tree with boot status
        boot_status_data = self.find_tree_with_boot_status(mainline_trees)
        if not boot_status_data:
            print("⚠️  No mainline trees with boot status found")
            return False
        
        total_boots = boot_status_data['total_boots']
        tree_info = boot_status_data['tree_info']
        commit_hash = tree_info['commit_hash']
        
        print(f"🎯 Using commit: {commit_hash[:12] if commit_hash else 'unknown'} with {total_boots} boot results")
        print(f"📍 From tree: {tree_info.get('repository', 'Unknown')} ({tree_info.get('branch', 'Unknown')})")
        
        # Step 4: Analyze the boot status
        print("📊 Analyzing boot status...")
        analysis = self.analyze_boot_status(boot_status_data)
        
        # Step 5: Display summary
        self.print_boot_status_summary(analysis)
        
        # Step 6: Display full boot details if requested
        self.print_full_boot_details(analysis, show_full=self.show_full)
        
        return True
        
    def run_test_analysis(self, mainline_trees: List[Dict[str, Any]]) -> bool:
        """Run analysis workflow for non-boot tests by fetching test results directly."""
        # Step 3: Try to get test results from the most recent mainline trees
        for i, tree in enumerate(mainline_trees[:5]):
            commit_hash = tree.get("git_commit_hash", "unknown")
            print(f"  📋 Checking tree {i+1}/5: {commit_hash[:12]}... for {self.test_path} tests")
            
            tree_info = {
                'commit_hash': commit_hash,
                'commit_name': tree.get('git_commit_name'),
                'repository': tree.get('git_repository_url'),
                'branch': tree.get('git_repository_branch'),
                'start_time': tree.get('start_time'),
                'tree_id': tree.get('id')
            }
            
            detailed_tests = self.get_detailed_test_results(tree_info)
            if detailed_tests:
                print(f"  ✅ Found {len(detailed_tests)} {self.test_path} test results")
                
                # Create analysis structure for this test data
                analysis = self.analyze_test_results(detailed_tests, tree_info)
                
                # Display summary and details
                self.print_test_status_summary(analysis)
                self.print_full_test_details(analysis)
                
                return True
        
        print(f"  ⚠️  No trees with {self.test_path} test results found")
        return False


def main():
    """Main function to run the data analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze KernelCI boot results for mainline kernel"
    )
    parser.add_argument(
        "--api-url",
        default="https://dashboard.kernelci.org/api",
        help="KernelCI Dashboard API base URL (default: https://dashboard.kernelci.org/api)"
    )
    parser.add_argument(
        "--save-json",
        action="store_true",
        help="Save raw boot results data to JSON file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Show detailed information for each individual boot test with dashboard links"
    )
    parser.add_argument(
        "--hist-size",
        type=int,
        default=10,
        help="Number of status history entries to fetch (default: 10)"
    )
    parser.add_argument(
        "--test-path",
        default="boot",
        help="Test path to analyze (default: boot)"
    )
    
    args = parser.parse_args()
    
    try:
        hist_size = getattr(args, 'hist_size', 10)  # Handle dash to underscore conversion
        test_path = getattr(args, 'test_path', 'boot')  # Handle dash to underscore conversion
        analyzer = KernelCIDataAnalyzer(base_url=args.api_url, show_full=args.full, hist_size=hist_size, test_path=test_path)
        success = analyzer.run_analysis()
        
        if success:
            print("\n✅ Analysis completed successfully")
            sys.exit(0)
        else:
            print("\n❌ Analysis failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ Analysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()