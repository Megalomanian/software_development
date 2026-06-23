"""Token persistence — reads/writes ~/.mlp/config.json."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _config_dir() -> Path:
    path = Path.home() / ".mlp"
    path.mkdir(mode=0o700, exist_ok=True)
    return path


def _config_file() -> Path:
    return _config_dir() / "config.json"


def load_config() -> dict:
    """Load full config dict. Returns empty dict if no config exists."""
    cfg = _config_file()
    if not cfg.exists():
        return {}
    try:
        return json.loads(cfg.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(config: dict) -> None:
    """Save full config dict to disk."""
    _config_file().write_text(json.dumps(config, indent=2))


def get_token() -> str | None:
    """Return the stored JWT token, or None."""
    return load_config().get("token")


def get_server() -> str:
    """Return the configured server URL or default."""
    return load_config().get("server", "http://localhost:8000")


def get_user_info() -> dict:
    """Return cached user info (username, email, role)."""
    return load_config().get("user", {})


def save_auth(token: str, server: str, user: dict) -> None:
    """Save token, server URL, and user info after successful login."""
    cfg = load_config()
    cfg["token"] = token
    cfg["server"] = server
    cfg["user"] = {"username": user.get("username"), "email": user.get("email"), "role": user.get("role")}
    save_config(cfg)


def clear_auth() -> None:
    """Remove stored token and user info."""
    cfg = load_config()
    cfg.pop("token", None)
    cfg.pop("user", None)
    save_config(cfg)
