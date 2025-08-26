from fastapi import FastAPI
from app.routes import auth
from app.core import Base
from app.core.database import engine
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # Crear tablas si no existen
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="FinTrack API", version="0.1.0", lifespan=lifespan)

# Rutas
app.include_router(auth.router)

@app.get("/")
async def root():
    return {"message": "FinTrack API funcionando 🚀"}
