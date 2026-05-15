"""Backward-compatible download wrapper for older local scripts."""

from backend.services.downloader import download_video


__all__ = ["download_video"]
