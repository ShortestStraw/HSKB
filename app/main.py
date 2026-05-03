"""FastAPI application entry point with global configuration."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine
from app.models import Base
from app.router_auth import router as auth_router
from app.router_cards import router as cards_router
from app.router_decks import router as decks_router
from app import schemas


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Creates database tables on startup.
    """
    Base.metadata.create_all(bind=engine)
    yield


# Initialize FastAPI application
app = FastAPI(
    title="Hearthstone Deck Knowledge Base",
    description="API for managing Hearthstone card collections and deck recommendations",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with unified error response format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=schemas.ErrorResponse(
            detail=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            path=request.url.path
        ).model_dump(mode='json'),
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors with detailed field information."""
    errors = []
    for error in exc.errors():
        errors.append(schemas.ValidationErrorDetail(
            field=".".join(str(loc) for loc in error["loc"]),
            message=error["msg"],
            type=error["type"]
        ))
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=schemas.ValidationErrorResponse(
            errors=errors,
            path=request.url.path
        ).model_dump(mode='json'),
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors gracefully."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=schemas.ErrorResponse(
            detail="Database error occurred",
            error_code="DB_ERROR",
            path=request.url.path
        ).model_dump(mode='json'),
    )


app.include_router(auth_router)
app.include_router(cards_router)
app.include_router(decks_router)


@app.get("/", response_model=dict)
def read_root():
    """Root endpoint with API welcome message and status."""
    return {
        "message": "Welcome to Hearthstone Deck KB API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "healthy"
    }


@app.get("/health", response_model=dict, tags=["utility"])
def health_check():
    """Simple health check endpoint for monitoring."""
    return {"status": "ok"}