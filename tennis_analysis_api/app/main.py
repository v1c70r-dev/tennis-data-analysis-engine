from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.models.loader import load_all_models
from app.routers import analysis

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load models once at startup
    app.state.models = load_all_models()
    print("Models loaded.")
    yield
    print("Shutting down.")


app = FastAPI(title="Tennis Analysis API", lifespan=lifespan)
app.include_router(analysis.router)


@app.get("/health")
def health():
    return {"status": "ok"}