#!/usr/bin/env python3
"""
research.py — Query AI research services and save results to obsidian/raw/

Supported services: perplexity, tavily, claude, github (raw fetch)

Usage:
    python scripts/research.py --topic "X" --service perplexity
    python scripts/research.py --topic "X" --wiki tools_wiki --service tavily
    python scripts/research.py --topic "X" --service github --repo "owner/repo"

Output:
    Saves to: obsidian/raw/research-{slug}-{date}.md
    With frontmatter: topic, source, date, target_wiki, query, ingested
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from urllib.parse import slugify

try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli
    except ImportError:
        print("[!] Error: tomli or tomllib required. Install with: pip install tomli")
        sys.exit(1)


def load_config():
    """Load configuration from settings.toml"""
    config_path = Path(__file__).parent.parent / "config" / "settings.toml"

    if not config_path.exists():
        print(f"[!] Config file not found: {config_path}")
        print(f"[*] Copy settings.example.toml to settings.toml and fill in your API keys")
        sys.exit(1)

    try:
        with open(config_path, "rb") as f:
            return tomli.load(f)
    except Exception as e:
        print(f"[!] Error loading config: {e}")
        sys.exit(1)


def research_perplexity(topic, config):
    """Query Perplexity API for research."""
    try:
        import requests
    except ImportError:
        print("[!] Error: requests library required. Install with: pip install requests")
        return None

    api_key = config["api_keys"].get("perplexity_api_key")
    if not api_key or api_key.endswith("-here"):
        print("[!] Error: Perplexity API key not configured")
        return None

    model = config.get("services", {}).get("perplexity_model", "sonar")

    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": topic}],
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            print("[!] Unexpected response format from Perplexity")
            return None
    except Exception as e:
        print(f"[!] Error querying Perplexity: {e}")
        return None


def research_tavily(topic, config):
    """Query Tavily Search API."""
    try:
        import requests
    except ImportError:
        print("[!] Error: requests library required. Install with: pip install requests")
        return None

    api_key = config["api_keys"].get("tavily_api_key")
    if not api_key or api_key.endswith("-here"):
        print("[!] Error: Tavily API key not configured")
        return None

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": api_key, "query": topic, "max_results": 5},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

        # Format Tavily results as markdown
        content = f"# Research Results for: {topic}\n\n"
        if "results" in result:
            for item in result["results"]:
                content += f"## {item.get('title', 'Untitled')}\n"
                content += f"**URL**: {item.get('url', 'N/A')}\n"
                content += f"{item.get('content', 'No description')}\n\n"
        return content
    except Exception as e:
        print(f"[!] Error querying Tavily: {e}")
        return None


def research_claude(topic, config):
    """Query Claude API for research."""
    try:
        from anthropic import Anthropic
    except ImportError:
        print("[!] Error: anthropic library required. Install with: pip install anthropic")
        return None

    api_key = config["api_keys"].get("anthropic_api_key")
    if not api_key or api_key.endswith("-here"):
        print("[!] Error: Anthropic API key not configured")
        return None

    try:
        client = Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-opus-4-1",
            max_tokens=2048,
            messages=[{"role": "user", "content": topic}]
        )
        return message.content[0].text
    except Exception as e:
        print(f"[!] Error querying Claude: {e}")
        return None


def research_github(repo, config):
    """Fetch README from GitHub repo."""
    try:
        import requests
    except ImportError:
        print("[!] Error: requests library required. Install with: pip install requests")
        return None

    try:
        # Try to fetch README
        urls = [
            f"https://raw.githubusercontent.com/{repo}/main/README.md",
            f"https://raw.githubusercontent.com/{repo}/master/README.md",
        ]

        for url in urls:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return f"# {repo} README\n\n{response.text}"

        print(f"[!] Could not find README for {repo}")
        return None
    except Exception as e:
        print(f"[!] Error fetching from GitHub: {e}")
        return None


def save_research(topic, source, content, target_wiki, config, query=""):
    """Save research to obsidian/raw/ with frontmatter."""

    vault_path = Path(config["paths"]["vault_path"])
    raw_dir = vault_path / "raw"

    if not raw_dir.exists():
        print(f"[!] Raw directory not found: {raw_dir}")
        return False

    # Generate filename
    slug = slugify(topic)[:50]  # Limit slug length
    date = datetime.now().strftime("%Y-%m-%d")
    filename = f"research-{slug}-{date}.md"
    filepath = raw_dir / filename

    # Create frontmatter
    frontmatter = f"""---
topic: "{topic}"
source: "{source}"
date: "{date}"
target_wiki: "{target_wiki}"
query: "{query or topic}"
ingested: false
---

"""

    # Write file
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter)
            f.write(content)

        print(f"[OK] Saved research to: {filepath.relative_to(vault_path.parent)}")
        return True
    except Exception as e:
        print(f"[!] Error saving research: {e}")
        return False


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Query research services and save to obsidian/raw/"
    )
    parser.add_argument("--topic", required=True, help="Research topic or query")
    parser.add_argument(
        "--service",
        choices=["perplexity", "tavily", "claude", "github"],
        default="perplexity",
        help="Research service to use"
    )
    parser.add_argument("--wiki", help="Target wiki (fin_wiki, code_wiki, tools_wiki, other_wiki)")
    parser.add_argument("--repo", help="GitHub repo (for --service github)")

    args = parser.parse_args()

    config = load_config()

    # Determine target wiki
    target_wiki = args.wiki or config["wikis"].get("other", "other_wiki")

    print(f"[*] Topic: {args.topic}")
    print(f"[*] Service: {args.service}")
    print(f"[*] Target wiki: {target_wiki}")
    print()

    # Query appropriate service
    print(f"[+] Querying {args.service}...")

    if args.service == "perplexity":
        content = research_perplexity(args.topic, config)
    elif args.service == "tavily":
        content = research_tavily(args.topic, config)
    elif args.service == "claude":
        content = research_claude(args.topic, config)
    elif args.service == "github":
        if not args.repo:
            print("[!] Error: --repo required for GitHub service")
            return False
        content = research_github(args.repo, config)
    else:
        print(f"[!] Unknown service: {args.service}")
        return False

    if not content:
        print("[!] Failed to get research results")
        return False

    print("[OK] Got research results")
    print()

    # Save to raw/
    success = save_research(
        args.topic,
        args.service,
        content,
        target_wiki,
        config,
        query=args.topic
    )

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
