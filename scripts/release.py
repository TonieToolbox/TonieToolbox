#!/usr/bin/env python3
"""
TonieToolbox Release Automation Script

This script automates the release process for TonieToolbox, handling:
- Version bumping (major, minor, patch, pre-release)
- CHANGELOG.md updates
- Git operations (branching, tagging, merging)
- GitHub Actions integration

Usage:
    python scripts/release.py --type patch --message "Bug fixes and improvements"
    python scripts/release.py --type minor --pre-release --message "New features (beta)"
    python scripts/release.py --type major --message "Breaking changes"
"""

import argparse
import os
import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from packaging.version import Version
except ImportError:
    print("❌ Error: 'packaging' library not found.")
    print("Please install it with: pip install packaging")
    print("Or install project dependencies: pip install -e .")
    sys.exit(1)


class ReleaseManager:
        
    def get_current_version(self):
        """Extract current version from __init__.py"""
        with open(self.version_file, 'r') as f:
            content = f.read()
            match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
            if not match:
                raise ValueError("Could not find version in __init__.py")
            return Version(match.group(1))
    
    def bump_version(self, current_version, bump_type, pre_release=None):
        """Calculate new version based on bump type using packaging.version.Version"""
        major, minor, patch = current_version.major, current_version.minor, current_version.micro
        
        # Remove any existing pre-release suffix for main releases
        if not pre_release and current_version.pre:
            # If we're doing a main release from a pre-release, don't bump further
            return Version(f"{major}.{minor}.{patch}")
        
        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        
        version_str = f"{major}.{minor}.{patch}"
        
        if pre_release:
            # Handle different pre-release types
            pre_num = 1  # Default to 1 for new pre-release
            
            # If we already have a pre-release, increment appropriately
            if current_version.pre:
                current_pre_type = current_version.pre[0]
                current_pre_num = current_version.pre[1]
                
                # Map pre-release types to their string representations
                pre_type_map = {'a': 'alpha', 'b': 'beta', 'rc': 'rc'}
                current_pre_name = pre_type_map.get(current_pre_type, current_pre_type)
                
                # If same pre-release type, increment number
                if pre_release == current_pre_name or (pre_release == 'alpha' and current_pre_type == 'a'):
                    pre_num = current_pre_num + 1
            
            # Convert pre-release type to PEP 440 format
            if pre_release == "alpha":
                version_str += f"a{pre_num}"
            elif pre_release == "beta":
                version_str += f"b{pre_num}"
            elif pre_release == "rc":
                version_str += f"rc{pre_num}"
        
        return Version(version_str)
    
    def update_version_file(self, new_version):
        """Update version in __init__.py (or simulate in dry run)"""
        if self.dry_run:
            print(f"[DRY RUN] Would update version to {new_version} in {self.version_file}")
            return
            
        with open(self.version_file, 'r') as f:
            content = f.read()
        
        updated_content = re.sub(
            r"__version__\s*=\s*['\"][^'\"]+['\"]",
            f"__version__ = '{new_version}'",
            content
        )
        
        with open(self.version_file, 'w') as f:
            f.write(updated_content)
        
        print(f"✓ Updated version to {new_version} in {self.version_file}")
    
    def update_changelog(self, version, release_message, is_prerelease=False):
        """Update CHANGELOG.md with new release entry (or simulate in dry run)"""
        if self.dry_run:
            today = datetime.now().strftime("%Y-%m-%d")
            release_type = "Pre-release" if is_prerelease else "Release"
            print(f"[DRY RUN] Would update CHANGELOG.md with:")
            print(f"  ## [{version}] - {today}")
            print(f"  ### {release_type}")
            print(f"  {release_message}")
            return
            
        with open(self.changelog_file, 'r') as f:
            content = f.read()
        
        # Find the [Unreleased] section
        today = datetime.now().strftime("%Y-%m-%d")
        release_type = "Pre-release" if is_prerelease else "Release"
        
        # Create new release section
        new_section = f"""## [Unreleased]
### Added
### Fixed
### Changed
### Removed

## [{version}] - {today}
### {release_type}
{release_message}
"""
        
        # Replace the [Unreleased] section
        updated_content = re.sub(
            r"## \[Unreleased\].*?(?=## \[|\Z)",
            new_section,
            content,
            flags=re.DOTALL
        )
        
        with open(self.changelog_file, 'w') as f:
            f.write(updated_content)
        
        print(f"✓ Updated CHANGELOG.md with release {version}")
    
    def __init__(self):
        self.repo_root = Path(__file__).parent.parent
        self.version_file = self.repo_root / "TonieToolbox" / "__init__.py"
        self.changelog_file = self.repo_root / "CHANGELOG.md"
        self.dry_run = False
        
    def set_dry_run(self, dry_run):
        """Enable or disable dry run mode"""
        self.dry_run = dry_run
    
    def run_command(self, command, cwd=None, check=True):
        """Run shell command and return output (or simulate in dry run)"""
        if cwd is None:
            cwd = self.repo_root
        
        command_str = ' '.join(command) if isinstance(command, list) else command
        
        if self.dry_run:
            print(f"[DRY RUN] Would run: {command_str}")
            # Return a mock result for dry run
            class MockResult:
                def __init__(self):
                    self.stdout = ""
                    self.stderr = ""
                    self.returncode = 0
            return MockResult()
        else:
            print(f"Running: {command_str}")
            result = subprocess.run(command, shell=isinstance(command, str), cwd=cwd, 
                                  capture_output=True, text=True, check=check)
            
            if result.stdout:
                print(result.stdout.strip())
            if result.stderr:
                print(f"stderr: {result.stderr.strip()}", file=sys.stderr)
            
            return result
    
    def check_git_status(self):
        """Ensure working directory is clean (or simulate in dry run)"""
        if self.dry_run:
            print("[DRY RUN] Would check git status for uncommitted changes")
            return
            
        result = self.run_command(["git", "status", "--porcelain"])
        if result.stdout.strip():
            print("❌ Working directory is not clean. Please commit or stash changes.")
            sys.exit(1)
        print("✓ Working directory is clean")
    
    def check_current_branch(self):
        """Get current git branch"""
        result = self.run_command(["git", "branch", "--show-current"])
        return result.stdout.strip()
    
    def run_tests(self):
        """Run test suite before release (or simulate in dry run)"""
        if self.dry_run:
            print("[DRY RUN] Would run test suite: make test")
            return
            
        print("🧪 Running test suite...")
        try:
            self.run_command(["make", "test"])
            print("✓ All tests passed")
        except subprocess.CalledProcessError:
            print("❌ Tests failed. Please fix issues before releasing.")
            sys.exit(1)
    
    def create_release_branch(self, version, is_prerelease=False):
        """Create release branch for main releases (or simulate in dry run)"""
        if is_prerelease:
            if self.dry_run:
                print("[DRY RUN] Pre-release: would stay on develop branch")
            return None  # Pre-releases stay on develop
        
        branch_name = f"release/v{version}"
        if self.dry_run:
            print(f"[DRY RUN] Would create release branch: {branch_name}")
        else:
            self.run_command(["git", "checkout", "-b", branch_name])
            print(f"✓ Created release branch: {branch_name}")
        return branch_name
    
    def commit_changes(self, version, release_message):
        """Commit version and changelog updates (or simulate in dry run)"""
        commit_msg = f"Release v{version}: {release_message}"
        if self.dry_run:
            print(f"[DRY RUN] Would commit changes with message: {commit_msg}")
            return
            
        self.run_command(["git", "add", str(self.version_file), str(self.changelog_file)])
        self.run_command(["git", "commit", "-m", commit_msg])
        print(f"✓ Committed changes: {commit_msg}")
    
    def create_tag(self, version):
        """Create git tag (or simulate in dry run)"""
        tag_name = f"v{version}"
        if self.dry_run:
            print(f"[DRY RUN] Would create tag: {tag_name}")
        else:
            self.run_command(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"])
            print(f"✓ Created tag: {tag_name}")
        return tag_name
    
    def merge_to_main(self, release_branch):
        """Merge release branch to main (or simulate in dry run)"""
        if not release_branch:
            return  # Skip for pre-releases
        
        if self.dry_run:
            print(f"[DRY RUN] Would merge {release_branch} to main")
            return
        
        self.run_command(["git", "checkout", "main"])
        self.run_command(["git", "pull", "origin", "main"])
        self.run_command(["git", "merge", "--no-ff", release_branch, "-m", f"Merge {release_branch}"])
        print("✓ Merged release branch to main")
    
    def push_changes(self, tag_name, is_prerelease=False):
        """Push branches and tags to remote (or simulate in dry run)"""
        if self.dry_run:
            if is_prerelease:
                print("[DRY RUN] Would push develop branch and tag for pre-release")
            else:
                print("[DRY RUN] Would push main branch, merge back to develop, and push develop")
            print(f"[DRY RUN] Would push tag {tag_name} (triggers GitHub Actions)")
            return
        
        if is_prerelease:
            # Push develop branch and tag for pre-releases
            self.run_command(["git", "push", "origin", "develop"])
        else:
            # Push main branch for regular releases
            self.run_command(["git", "push", "origin", "main"])
            # Also push back to develop
            self.run_command(["git", "checkout", "develop"])
            self.run_command(["git", "merge", "main"])
            self.run_command(["git", "push", "origin", "develop"])
        
        # Push tag (triggers GitHub Actions)
        self.run_command(["git", "push", "origin", tag_name])
        print(f"✓ Pushed {tag_name} - GitHub Actions will handle PyPI publishing")
    
    def cleanup_release_branch(self, release_branch):
        """Clean up release branch after successful merge (or simulate in dry run)"""
        if not release_branch:
            return
        
        if self.dry_run:
            print(f"[DRY RUN] Would delete local release branch: {release_branch}")
            return
        
        self.run_command(["git", "branch", "-d", release_branch])
        print(f"✓ Deleted local release branch: {release_branch}")


def main():
    parser = argparse.ArgumentParser(description="TonieToolbox Release Automation")
    parser.add_argument("--type", choices=["major", "minor", "patch"], required=True,
                       help="Type of version bump")
    parser.add_argument("--message", required=True,
                       help="Release message for changelog")
    parser.add_argument("--pre-release", choices=["alpha", "beta", "rc"], 
                       help="Create pre-release (stays on develop branch): alpha, beta, or rc")
    parser.add_argument("--skip-tests", action="store_true",
                       help="Skip running test suite")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    manager = ReleaseManager()
    manager.set_dry_run(args.dry_run)
    
    # Validate environment
    current_branch = manager.check_current_branch()
    
    if args.pre_release and current_branch != "develop":
        print("❌ Pre-releases must be created from develop branch")
        sys.exit(1)
    
    if not args.pre_release and current_branch not in ["develop", "main"]:
        print("❌ Regular releases must be created from develop or main branch")
        sys.exit(1)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Get current version and calculate new version
    current_version = manager.get_current_version()
    new_version = manager.bump_version(current_version, args.type, args.pre_release)
    
    print(f"📦 Release Plan:")
    print(f"   Current version: {current_version}")
    print(f"   New version: {new_version}")
    print(f"   Type: {f'{args.pre_release.title()} pre-release' if args.pre_release else 'Release'}")
    print(f"   Branch strategy: {'Stay on develop' if args.pre_release else 'develop → main'}")
    print(f"   Message: {args.message}")
    
    # For dry run, simulate all steps
    if args.dry_run:
        print(f"\n🔍 DRY RUN - Simulating release process for v{new_version}")
        
        # Simulate pre-flight checks
        manager.check_git_status()
        
        if not args.skip_tests:
            manager.run_tests()
        
        # Simulate release process
        print(f"\n[DRY RUN] Starting release process for v{new_version}")
        
        # Simulate file updates on develop branch FIRST
        manager.update_version_file(new_version)
        manager.update_changelog(new_version, args.message, args.pre_release)
        
        # Simulate committing version changes to develop
        manager.commit_changes(new_version, args.message)
        
        # Simulate release branch creation AFTER version update
        release_branch = manager.create_release_branch(new_version, args.pre_release)
        
        # Simulate tag creation
        tag_name = manager.create_tag(new_version)
        
        # Simulate merge and push for regular releases
        if not args.pre_release:
            manager.merge_to_main(release_branch)
            manager.cleanup_release_branch(release_branch)
        
        # Simulate push changes
        manager.push_changes(tag_name, args.pre_release)
        
        print(f"\n✅ DRY RUN completed successfully!")
        print(f"📋 This would have created release v{new_version}")
        print(f"🔗 No actual changes were made to files or git repository")
        return
    
    # Confirm before proceeding with real release
    confirm = input(f"\nProceed with release v{new_version}? [y/N]: ")
    if confirm.lower() != 'y':
        print("Release cancelled")
        return
    
    try:
        # Pre-flight checks
        manager.check_git_status()
        
        if not args.skip_tests:
            manager.run_tests()
        
        # Start release process
        print(f"\n🚀 Starting release process for v{new_version}")
        
        # Update files on develop branch FIRST
        manager.update_version_file(new_version)
        manager.update_changelog(new_version, args.message, args.pre_release)
        
        # Commit version changes to develop
        manager.commit_changes(new_version, args.message)
        
        # Create release branch for main releases AFTER version update
        release_branch = manager.create_release_branch(new_version, args.pre_release)
        
        # Create tag
        tag_name = manager.create_tag(new_version)
        
        # Merge and push for regular releases
        if not args.pre_release:
            manager.merge_to_main(release_branch)
            manager.cleanup_release_branch(release_branch)
        
        # Push changes (this triggers GitHub Actions)
        manager.push_changes(tag_name, args.pre_release)
        
        print(f"\n🎉 Release v{new_version} completed successfully!")
        print(f"📊 GitHub Actions will build and publish to PyPI")
        print(f"🔗 Monitor: https://github.com/TonieToolbox/TonieToolbox/actions")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Release failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()