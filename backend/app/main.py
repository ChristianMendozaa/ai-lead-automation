from fastapi import FastAPI

from app.routers import config, leads

app = FastAPI(title="AI Lead Automation API", version="0.1.0")

app.include_router(leads.router)
app.include_router(config.router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
