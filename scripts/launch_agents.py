#!/usr/bin/env python
"""
Agent Cluster Launcher - Entry point script.

This script starts the A2A agent cluster for distributed scraping.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.scraping.agents.main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down agent cluster...")
        sys.exit(0)
