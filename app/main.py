from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine
from app.models import Base
from app.router_auth import router as auth_router
from app.router_cards import router as cards_router
from app.router_decks import router as decks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create SQLite database 
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Hearthstone Deck Knowledge Base", version="1.0.0", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(cards_router)
app.include_router(decks_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Hearthstone Deck KB API"}