"""Authentication provider for GrokSearch MCP server."""

from __future__ import annotations

import os
import sys
from typing import Any


def _load_tokens_from_env() -> list[str]:
    """Load tokens from MCP_AUTH_TOKENS env var (comma-separated)."""
    raw = os.getenv("MCP_AUTH_TOKENS", "").strip()
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def _load_tokens_from_file() -> list[str]:
    """Load tokens from MCP_AUTH_TOKENS_FILE, one per line."""
    path = os.getenv("MCP_AUTH_TOKENS_FILE", "").strip()
    if not path:
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [
                line.strip()
                for line in f
                if line.strip() and not line.startswith("#")
            ]
    except OSError as e:
        print(
            f"[grok-search] WARNING: Failed to read token file {path}: {e}",
            file=sys.stderr,
        )
        return []


def _all_tokens() -> list[str]:
    """Combine tokens from env var and file, deduplicating."""
    seen: set[str] = set()
    result: list[str] = []
    for t in _load_tokens_from_env() + _load_tokens_from_file():
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def build_auth_provider():
    """Build a StaticTokenVerifier from environment configuration.

    Returns None when no tokens are configured (auth disabled).
    """
    tokens = _all_tokens()
    if not tokens:
        return None

    from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

    token_dict: dict[str, dict[str, Any]] = {}
    for i, token in enumerate(tokens):
        token_dict[token] = {
            "client_id": f"client-{i + 1}",
            "scopes": [],
            "expires_at": None,
        }

    return StaticTokenVerifier(tokens=token_dict)
