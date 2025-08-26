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
    
    def __init__(self, base_url: str = "https://dashboard.kernelci.org/api", show_full: bool = False):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 30
        self.show_full = show_full
        
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
    
    def get_detailed_boot_results(self, tree_info: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Get detailed boot results for a specific tree using correct API parameters."""
        commit_hash = tree_info.get('commit_hash')
        git_url = tree_info.get('repository')
        git_branch = tree_info.get('branch')
        
        if not all([commit_hash, git_url, git_branch]):
            print(f"  ❌ Missing required parameters: commit_hash={commit_hash}, git_url={git_url}, git_branch={git_branch}")
            return []
        
        # Use the correct tree boots endpoint with required parameters
        endpoint = f"{self.base_url}/tree/{commit_hash}/boots"
        params = {
            'git_url': git_url,
            'git_branch': git_branch,
            'origin': 'maestro'
        }
        
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
                    print(f"  ✅ Success: Found {len(result)} boot results")
                    return result
                elif isinstance(result, dict):
                    # Check for 'boots' key (KernelCI format)
                    if 'boots' in result:
                        boot_results = result['boots']
                        if isinstance(boot_results, list):
                            print(f"  ✅ Success: Found {len(boot_results)} boot results")
                            return boot_results
                    # Check for 'results' key (alternative format)
                    elif 'results' in result:
                        boot_results = result['results']
                        if isinstance(boot_results, list):
                            print(f"  ✅ Success: Found {len(boot_results)} boot results")
                            return boot_results
                
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
    
    def print_full_boot_details(self, analysis: Dict[str, Any], show_full: bool = False):
        """Print detailed information for each boot result."""
        if not show_full:
            return
            
        tree_info = analysis["tree_info"]
        
        print("\n" + "="*80)
        print("🔍 DETAILED BOOT RESULTS")
        print("="*80)
        print("📡 Fetching detailed boot records...")
        
        detailed_boots = self.get_detailed_boot_results(tree_info)
            
        print(f"✅ Found {len(detailed_boots)} detailed boot records\n")
        
        # Group boots by status for better organization
        boots_by_status = {}
        for boot in detailed_boots:
            status = boot.get('status', 'unknown').lower()
            if status not in boots_by_status:
                boots_by_status[status] = []
            boots_by_status[status].append(boot)
        
        # Display boots grouped by status
        for status, boots in sorted(boots_by_status.items()):
            if not boots:
                continue
                
            status_icon = self.get_status_icon(status)
            print(f"\n{status_icon} {status.upper()} ({len(boots)} boots):")
            print("-" * 50)
            
            # Show only first 3 boots of each status type
            for i, boot in enumerate(boots[:3], 1):
                boot_id = boot.get('id', 'unknown')
                platform = boot.get('platform', 'unknown')
                config = boot.get('config_name', 'unknown')
                arch = boot.get('arch', 'unknown')
                
                # Create dashboard link (for tests/boots, use 't' endpoint)
                dashboard_link = f"https://d.kernelci.org/t/{boot_id}"
                
                print(f"  {i:2d}.  {status_icon} {dashboard_link}")
            
            # Show count of remaining boots if there are more than 3
            if len(boots) > 3:
                print(f"      ... and {len(boots) - 3} more {status.upper()} boots")
        
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
        print("🚀 Starting KernelCI Boot Results Analysis")
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
        
        if mainline_trees:
            # Sort by start_time to get the most recent order
            mainline_trees.sort(key=lambda x: x.get('start_time', ''), reverse=True)
            print(f"✅ Found {len(mainline_trees)} mainline trees")
            
            # Step 3: Find a tree with boot status
            boot_status_data = self.find_tree_with_boot_status(mainline_trees)
            if not boot_status_data:
                print("⚠️  No mainline trees with boot status found, trying any tree...")
        else:
            print("⚠️  No mainline trees found")
            boot_status_data = None
        
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
    
    args = parser.parse_args()
    
    try:
        analyzer = KernelCIDataAnalyzer(base_url=args.api_url, show_full=args.full)
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