#!/usr/bin/env python3
"""
Working JIRA Bearer Authentication Example

This script demonstrates the correct Bearer authentication method
for JIRA instances that have disabled Basic Authentication.
"""

from jira import JIRA
import os

def create_jira_client():
    """
    Create a JIRA client using Bearer authentication
    """
    # Configuration
    JIRA_SERVER = os.environ.get("JIRA_SERVER", "YOUR_JIRA_SERVER_URL_HERE")
    JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "YOUR_JIRA_API_TOKEN_HERE")
    
    # Create Bearer authentication headers
    headers = JIRA.DEFAULT_OPTIONS["headers"].copy()
    headers["Authorization"] = f"Bearer {JIRA_API_TOKEN}"
    
    # Initialize JIRA client
    jira = JIRA(
        server=JIRA_SERVER,
        options={"headers": headers}
    )
    
    return jira

def main():
    """
    Example usage of JIRA Bearer authentication
    """
    print("=== JIRA Bearer Authentication Example ===")
    
    try:
        # Create JIRA client
        jira = create_jira_client()
        
        # Test 1: Fetch a specific issue
        print("\n1. Fetching issue NCS-8540...")
        issue = jira.issue("NCS-8540")
        print(f"   ✓ Issue: {issue.fields.summary}")
        print(f"   ✓ Status: {issue.fields.status.name}")
        print(f"   ✓ Project: {issue.fields.project.key}")
        
        # Test 2: Get user information
        print("\n2. Getting current user info...")
        try:
            user = jira.myself()
            user_name = getattr(user, 'displayName', getattr(user, 'name', 'Unknown'))
            print(f"   ✓ Logged in as: {user_name}")
        except Exception as e:
            print(f"   ⚠ Could not get user info: {e}")
        
        # Test 3: List projects
        print("\n3. Listing accessible projects...")
        try:
            projects = jira.projects()
            print(f"   ✓ Found {len(projects)} projects:")
            for project in projects[:5]:  # Show first 5
                print(f"     - {project.key}: {project.name}")
            if len(projects) > 5:
                print(f"     ... and {len(projects) - 5} more")
        except Exception as e:
            print(f"   ⚠ Could not list projects: {e}")
        
        # Test 4: Search for issues
        print("\n4. Searching for recent issues...")
        try:
            issues = jira.search_issues('order by created DESC', maxResults=3)
            print(f"   ✓ Found {len(issues)} recent issues:")
            for issue in issues:
                print(f"     - {issue.key}: {issue.fields.summary}")
        except Exception as e:
            print(f"   ⚠ Could not search issues: {e}")
        
        print("\n✅ Bearer authentication is working correctly!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your JIRA_API_TOKEN environment variable")
        print("2. Verify the token has not expired")
        print("3. Ensure you have permissions to access the resources")

if __name__ == "__main__":
    main() 