#!/usr/bin/env python3
"""
git_sync.py — Automate git operations for the Obsidian Wiki repo.

Pushes changes from Werkbestanden AI/obsidian/ to MonkeyBIHazeleger/Wiki on GitHub.

Usage:
    python scripts/git_sync.py                    # Uses timestamp as commit message
    python scripts/git_sync.py "Custom message"   # Uses provided commit message
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_command(cmd, cwd=None):
    """Execute shell command and return result."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=True,
            check=True
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()


def sync_wiki(commit_message=None):
    """Sync obsidian/ folder to GitHub Wiki repo."""

    # Set up paths
    repo_root = Path(__file__).parent.parent.parent  # Werkbestanden AI/
    wiki_repo = repo_root / "obsidian"

    # Verify wiki repo exists
    if not wiki_repo.exists():
        print(f"❌ Error: Wiki repo not found at {wiki_repo}")
        return False

    # Generate commit message if not provided
    if not commit_message:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"wiki: auto-sync ({timestamp})"

    print(f"[*] Working in: {wiki_repo}")
    print(f"[*] Commit message: {commit_message}")
    print()

    # Stage all changes
    print("[+] Staging changes...")
    success, output = run_command("git add -A", cwd=wiki_repo)
    if not success:
        print(f"[!] Failed to stage changes: {output}")
        return False
    print("[OK] Changes staged")

    # Check if there are changes to commit
    success, output = run_command("git diff --cached --quiet", cwd=wiki_repo)
    if success:
        print("[*] No changes to commit")
        return True

    # Commit changes
    print(f"[+] Committing...")
    success, output = run_command(
        f'git commit -m "{commit_message}"',
        cwd=wiki_repo
    )
    if not success:
        print(f"[!] Failed to commit: {output}")
        return False
    print(f"[OK] Committed: {output.splitlines()[0] if output else 'OK'}")

    # Push to remote
    print("[+] Pushing to GitHub...")
    success, output = run_command("git push origin master", cwd=wiki_repo)
    if not success:
        # Check if it's a "no changes" error (branch already up to date)
        if "up-to-date" in output or "Everything up-to-date" in output:
            print("[*] Branch already up to date")
            return True
        print(f"[!] Failed to push: {output}")
        return False

    print(f"[OK] Pushed to GitHub")
    print()
    print("[OK] Wiki sync complete!")
    return True


def main():
    """Entry point."""
    commit_message = None

    # Get commit message from CLI if provided
    if len(sys.argv) > 1:
        commit_message = sys.argv[1]

    success = sync_wiki(commit_message)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
