import asyncio
import logging
from typing import Optional

import uvicorn
from fastapi import FastAPI

from .mcp.server import MCPServer

logger = logging.getLogger(__name__)


def create_mcp_app(config: Optional[dict] = None) -> FastAPI:
    """Create and return the MCP FastAPI app."""
    server = MCPServer(config or {})
    return server.app


def run_mcp_server(config: Optional[dict] = None, host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the MCP server directly."""
    server = MCPServer(config or {})
    server.run(host=host, port=port, reload=reload)


if __name__ == "__main__":
    import yaml
    from pathlib import Path

    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    run_mcp_server(config.get("mcp", {}), reload=False)
