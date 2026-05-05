from fastapi import FastAPI

app = FastAPI(title="Meeting MVP Backend")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
