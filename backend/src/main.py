from fastapi import FastAPI

app = FastAPI(
    title="AI Data Factory",
    version="0.1.0",
    description="Production-grade AI training data pipeline",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
