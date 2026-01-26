"""
BIND - Book Indexing Network Daemon

Entry point for running BIND as a Python module:
    python -m src

This provides a clean entry point alternative to calling:
    python -m src.bind daemon
"""

from src.bind import cli

if __name__ == "__main__":
    cli()
