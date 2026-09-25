"""
TruthLens AI/ML — Module 08: Audio-Visual Synchronization Analysis
Blueprint Section D, E, F, G (AV Sync Pipeline)
"""

__all__ = [
    "analyze_av_sync_bytes",
    "analyze_av_sync_from_path",
]


def __getattr__(name: str):
    if name in ("analyze_av_sync_bytes", "analyze_av_sync_from_path"):
        from services.av_sync.service import (
            analyze_av_sync_bytes,
            analyze_av_sync_from_path,
        )
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
