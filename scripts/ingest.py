#!/usr/bin/env python3
"""
ingest.py — Process raw research files into structured wiki pages

Reads raw/*.md files with frontmatter, uses Claude API to structure content,
creates/updates wiki pages, and marks files as ingested.

Usage:
    python scripts/ingest.py                 # Process all unprocessed files
    python scripts/ingest.py --file raw/research-xyz-2026-05-05.md
    python scripts/ingest.py --watch         # Watch for new files (requires watchdog)
"""

import argparse
import sys
import re
import os
from pathlib import Path
from datetime import datetime

try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli
    except ImportError:
        print("[!] Error: tomli or tomllib required")
        sys.exit(1)


def load_config():
    """Load configuration."""
    config_path = Path(__file__).parent.parent / "config" / "settings.toml"
    if not config_path.exists():
        print(f"[!] Config not found: {config_path}")
        sys.exit(1)

    try:
        with open(config_path, "rb") as f:
            return tomli.load(f)
    except Exception as e:
        print(f"[!] Error loading config: {e}")
        sys.exit(1)


def parse_frontmatter(content):
    """Extract frontmatter from markdown file."""
    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        return {}, content

    fm_text = match.group(1)
    body = content[match.end():]

    frontmatter = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            # Remove quotes and strip whitespace
            value = value.strip().strip('"')
            frontmatter[key.strip()] = value

    return frontmatter, body


def update_frontmatter(frontmatter):
    """Update frontmatter to mark as ingested."""
    frontmatter["ingested"] = "true"
    return frontmatter


def frontmatter_to_yaml(fm):
    """Convert dict to YAML frontmatter."""
    lines = ["---"]
    for key, value in fm.items():
        lines.append(f'{key}: "{value}"')
    lines.append("---")
    return "\n".join(lines)


def get_raw_files(vault_path, unprocessed_only=True):
    """Find raw research files."""
    raw_dir = vault_path / "raw"

    if not raw_dir.exists():
        print(f"[!] Raw directory not found: {raw_dir}")
        return []

    files = []
    for md_file in raw_dir.glob("research-*.md"):
        content = md_file.read_text(encoding='utf-8')
        fm, _ = parse_frontmatter(content)

        if unprocessed_only and fm.get("ingested") == "true":
            continue

        files.append((md_file, fm))

    return files






def create_wiki_page(wiki_dir, filename, content, source):
    """Create a wiki page with frontmatter."""
    # Ensure filename is safe and has .md extension
    if not filename.endswith(".md"):
        filename = filename.lower().replace(" ", "-") + ".md"
    else:
        filename = filename.lower().replace(" ", "-")

    filepath = wiki_dir / filename

    # Create frontmatter
    frontmatter = f"""---
type: concept
source: "{source}"
created: "{datetime.now().strftime('%Y-%m-%d')}"
---

{content}
"""

    try:
        filepath.write_text(frontmatter, encoding='utf-8')
        return True, filename
    except Exception as e:
        print(f"    [!] Error writing {filename}: {e}")
        return False, filename


def update_wiki_index(wiki_dir, new_pages, topic):
    """Update the wiki's index.md with new pages."""
    index_path = wiki_dir / "index.md"

    if not index_path.exists():
        print(f"  [!] Index not found: {index_path}")
        return False

    try:
        content = index_path.read_text(encoding='utf-8')

        # Add new pages to index (simple append before end)
        new_entries = "\n".join([f"- [[{page['filename'][:-3]}]] — " for page in new_pages])

        # Insert before the last line if it's a log reference
        lines = content.rstrip().split("\n")
        lines.insert(-1, f"\n## Recently Added ({topic})")
        lines.insert(-1, new_entries)

        index_path.write_text("\n".join(lines), encoding='utf-8')
        return True
    except Exception as e:
        print(f"  [!] Error updating index: {e}")
        return False


def update_wiki_log(wiki_dir, new_pages, topic, source):
    """Append to the wiki's log.md with what was added."""
    log_path = wiki_dir / "log.md"

    if not log_path.exists():
        print(f"  [!] Log not found: {log_path}")
        return False

    try:
        content = log_path.read_text(encoding='utf-8')

        date = datetime.now().strftime("%Y-%m-%d")
        page_list = ", ".join([f"[[{p['filename'][:-3]}]]" for p in new_pages])

        entry = f"\n## {date}\n\n**Source**: {source}\n**Topic**: {topic}\n**Pages Created**: {page_list}\n"

        log_path.write_text(content + entry, encoding='utf-8')
        return True
    except Exception as e:
        print(f"  [!] Error updating log: {e}")
        return False


def process_file(filepath, frontmatter, vault_path, config):
    """Process a single raw file by saving to wiki (manual curation)."""

    target_wiki = frontmatter.get("target_wiki", "other_wiki")
    topic = frontmatter.get("topic", "Unknown")
    source = frontmatter.get("source", "unknown")

    # Read raw content
    content = filepath.read_text(encoding='utf-8')
    fm, body = parse_frontmatter(content)

    print(f"  [*] Topic: {topic}")
    print(f"  [*] Target wiki: {target_wiki}")

    wiki_dir = vault_path / target_wiki
    if not wiki_dir.exists():
        print(f"  [!] Wiki directory not found: {wiki_dir}")
        return False

    # Create a single page from raw content
    # Filename based on topic slug
    slug = re.sub(r'[^\w\s-]', '', topic).lower()
    slug = re.sub(r'[-\s]+', '-', slug)[:50]
    filename = slug + ".md"

    print(f"  [+] Saving to wiki page: {filename}")
    success, saved_filename = create_wiki_page(wiki_dir, filename, body, source)

    if not success:
        print(f"  [!] Failed to create wiki page")
        return False

    print(f"    [+] {saved_filename}")
    created_pages = [{"filename": saved_filename}]

    # Update index and log
    if not update_wiki_index(wiki_dir, created_pages, topic):
        print(f"  [!] Failed to update index")

    if not update_wiki_log(wiki_dir, created_pages, topic, source):
        print(f"  [!] Failed to update log")

    # Mark as ingested
    fm["ingested"] = "true"
    updated_content = frontmatter_to_yaml(fm) + "\n" + body

    try:
        filepath.write_text(updated_content, encoding='utf-8')
        print(f"  [OK] Marked as ingested")
        return True
    except Exception as e:
        print(f"  [!] Error updating file: {e}")
        return False


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Ingest raw research files into wiki")
    parser.add_argument("--file", help="Process specific file")
    parser.add_argument("--watch", action="store_true", help="Watch for new files")

    args = parser.parse_args()

    config = load_config()
    vault_path = Path(config["paths"]["vault_path"])

    print("[*] Ingest pipeline")
    print()

    if args.file:
        # Process specific file
        filepath = vault_path / args.file
        if not filepath.exists():
            print(f"[!] File not found: {filepath}")
            return False

        print(f"[+] Processing: {args.file}")
        content = filepath.read_text()
        fm, _ = parse_frontmatter(content)

        return process_file(filepath, fm, vault_path, config)

    # Find and process unprocessed files
    files = get_raw_files(vault_path, unprocessed_only=True)

    if not files:
        print("[*] No unprocessed files found in raw/")
        return True

    print(f"[+] Found {len(files)} unprocessed file(s)")
    print()

    success_count = 0
    for filepath, frontmatter in files:
        print(f"[*] {filepath.name}")
        if process_file(filepath, frontmatter, vault_path, config):
            success_count += 1
        print()

    print(f"[OK] Processed {success_count}/{len(files)} files")
    return success_count == len(files)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
