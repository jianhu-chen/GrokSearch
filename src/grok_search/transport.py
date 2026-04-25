"""Multi-transport HTTP server for GrokSearch MCP."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


def build_combined_app(mcp_server) -> Starlette:
    """Build a Starlette app serving both SSE and Streamable HTTP transports.

    Routes:
        /sse          -> SSE transport (GET for event stream)
        /messages/    -> SSE message endpoint (POST)
        /mcp          -> Streamable HTTP transport (GET/POST/DELETE)
        /health       -> Health check (GET)
    """
    from fastmcp.server.http import StarletteWithLifespan

    # Create individual transport apps via FastMCP
    sse_app = mcp_server.http_app(transport="sse")
    sh_app = mcp_server.http_app(transport="streamable-http")

    # Merge routes (no path conflicts: SSE uses /sse + /messages/, HTTP uses /mcp)
    all_routes = list(sse_app.routes) + list(sh_app.routes)

    # Take middleware from one sub-app (identical since same auth provider)
    all_middleware = list(sse_app.user_middleware)

    # Combined lifespan: nest both sub-app lifespans.
    # _lifespan_manager is reference-counted so this is safe.
    @asynccontextmanager
    async def combined_lifespan(app: Starlette):
        async with sse_app.router.lifespan_context(sse_app):
            async with sh_app.router.lifespan_context(sh_app):
                yield

    def health_check(request):
        return JSONResponse({"status": "ok", "service": "grok-search"})

    all_routes.append(Route("/health", endpoint=health_check, methods=["GET"]))

    combined = StarletteWithLifespan(
        routes=all_routes,
        middleware=all_middleware,
        debug=False,
        lifespan=combined_lifespan,
    )
    combined.state.fastmcp_server = mcp_server
    combined.state.path = ""
    combined.state.transport_type = "http"

    return combined


async def run_http_server(mcp_server) -> None:
    """Run the combined HTTP server."""
    app = build_combined_app(mcp_server)
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        timeout_graceful_shutdown=2,
        lifespan="on",
    )
    server = uvicorn.Server(config)
    print("[grok-search] HTTP server starting on http://0.0.0.0:8000", file=sys.stderr)
    print("[grok-search]   SSE:             http://0.0.0.0:8000/sse", file=sys.stderr)
    print("[grok-search]   Streamable HTTP: http://0.0.0.0:8000/mcp", file=sys.stderr)
    print("[grok-search]   Health check:    http://0.0.0.0:8000/health", file=sys.stderr)
    await server.serve()
