"""Local read-only dashboard for persisted Tutor Engine state."""

from .server import build_dashboard_state, serve_dashboard

__all__ = ["build_dashboard_state", "serve_dashboard"]
