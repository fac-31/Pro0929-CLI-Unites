#!/usr/bin/env python3
"""Wrapper script for notes command that ensures proper path setup."""

import sys
import os

def main():
    """Main entry point for the notes command."""
    # Add the current directory to Python path for editable installs
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    # Now import and run the CLI
    from cli_unites.cli import cli
    return cli()

if __name__ == "__main__":
    sys.exit(main())
