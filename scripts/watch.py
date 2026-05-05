#!/usr/bin/env python3
"""
watch.py — Monitor obsidian/raw/ for new research files and auto-trigger ingest.py

Watches for new files matching pattern: research-*.md
Triggers: python scripts/ingest.py --file {filepath}

Usage:
    python scripts/watch.py                  # Watch and process as files appear
    python scripts/watch.py --verbose        # With verbose output
"""

import argparse
import sys
import subprocess
from pathlib import Path
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("[!] Error: watchdog library required. Install with: pip install watchdog")
    sys.exit(1)

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


class ResearchFileHandler(FileSystemEventHandler):
    """Handle new research files in raw/ directory."""

    def __init__(self, vault_path, verbose=False):
        self.vault_path = vault_path
        self.verbose = verbose
        self.raw_dir = vault_path / "raw"

    def on_created(self, event):
        """Triggered when file is created."""
        if event.is_directory:
            return

        filepath = Path(event.src_path)

        # Only process research-*.md files
        if not filepath.name.startswith("research-") or not filepath.suffix == ".md":
            return

        # Give the file a moment to finish writing
        import time
        time.sleep(0.5)

        if not filepath.exists():
            return

        print()
        print(f"[*] New file detected: {filepath.name}")
        print(f"[*] Triggering ingest.py...")

        try:
            # Call ingest.py with the file path
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parent / "ingest.py"),
                    "--file",
                    str(filepath.relative_to(self.vault_path.parent))
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                print("[OK] Ingest completed successfully")
            else:
                print(f"[!] Ingest failed with code {result.returncode}")
                if result.stdout:
                    print("[*] Output:", result.stdout)
                if result.stderr:
                    print("[!] Error:", result.stderr)
        except subprocess.TimeoutExpired:
            print("[!] Ingest timed out after 60 seconds")
        except Exception as e:
            print(f"[!] Error triggering ingest: {e}")

        print()


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Watch obsidian/raw/ and auto-ingest on new files")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    config = load_config()
    vault_path = Path(config["paths"]["vault_path"])
    raw_dir = vault_path / "raw"

    if not raw_dir.exists():
        print(f"[!] Raw directory not found: {raw_dir}")
        return False

    print("[*] Watch pipeline")
    print(f"[*] Monitoring: {raw_dir}")
    print("[*] Press Ctrl+C to stop")
    print()

    # Set up watcher
    handler = ResearchFileHandler(vault_path, verbose=args.verbose)
    observer = Observer()
    observer.schedule(handler, str(raw_dir), recursive=False)

    try:
        observer.start()
        observer.join()
    except KeyboardInterrupt:
        observer.stop()
        print()
        print("[*] Watch stopped")
        observer.join()
        return True
    except Exception as e:
        print(f"[!] Error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
