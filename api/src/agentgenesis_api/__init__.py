"""Agent Genesis extraction backend package."""

__all__ = ["main"]


def main() -> None:
    """uv-managed script entry; defers to uvicorn for actual server boot."""
    import uvicorn

    uvicorn.run(
        "agentgenesis_api.main:create_app",
        host="0.0.0.0",
        port=8000,
        factory=True,
        reload=False,
    )
