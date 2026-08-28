"""Backward-compatible import for the recommendations service."""

from src.services.recommendations import get_recommendations

__all__ = ["get_recommendations"]
