"""Process health endpoint; business APIs are added separately."""

from fastapi import FastAPI

app = FastAPI(
    title="PORT 8282 AI service",
    version="0.1.0",
    description="Process health only. Scheduling and model inference are not implemented yet.",
)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Report HTTP process health, not model or downstream readiness."""
    return {"status": "ok", "service": "ai"}
