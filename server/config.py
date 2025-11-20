"""
config.py

Central configuration constants and helper functions for the Linux Remote Desktop project.
All values are documented so newcomers understand their impact.

In a later evolution we may load these from environment variables or a TOML/YAML file.
For the initial public-readable version, keeping them here with clear English comments
is simpler.
"""

from dataclasses import dataclass
import os

def _env(key: str, default: str) -> str:
    """Fetch an environment variable with a fallback default (string)."""
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    """Fetch an environment variable as int, falling back to a default if parsing fails."""
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    """Fetch an environment variable as float, with forgiving fallback to default."""
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default

@dataclass
class Settings:
    """Grouped tunable server settings.

    Adjust these to trade off performance vs quality/latency.
    """
    host: str = _env("REMOTE_HOST", "0.0.0.0")  # Listen on all interfaces by default.
    port: int = _env_int("REMOTE_PORT", 8765)    # WebSocket port.
    target_fps: int = _env_int("REMOTE_FPS", 12)  # Frame rate target (soft cap).
    jpeg_quality: int = _env_int("REMOTE_JPEG_QUALITY", 60)  # 1-95 typical range for Pillow.
    max_connections: int = _env_int("REMOTE_MAX_CONNECTIONS", 5)  # Simple guardrail.
    resize_scale: float = _env_float("REMOTE_RESIZE_SCALE", 1.0)  # Scale <1.0 reduces bandwidth.
    send_cursor: bool = bool(int(_env("REMOTE_SEND_CURSOR", "1")))  # Placeholder for future.

settings = Settings()
