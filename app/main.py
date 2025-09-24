from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.routes import auth, transactions, categories, budgets, users, reports, ai
from app.core import Base
from app.core.database import engine
from app.models.user import User
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.budget import Budget
from contextlib import asynccontextmanager

origins = [
    "http://localhost:3000"
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # Eliminamos por si hacemos cambios en las tablas
        # await conn.run_sync(Base.metadata.drop_all)
        # Crear tablas si no existen
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="FinTrack API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # Permitir cookies/autenticación
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Permitir todos los headers
)

# Rutas
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(budgets.router)
app.include_router(users.router)
app.include_router(reports.router)
app.include_router(ai.router)


@app.get("/")
async def root():
    return {"message": "FinTrack API funcionando 🚀"}
