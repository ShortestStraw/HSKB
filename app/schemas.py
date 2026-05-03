"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field, field_validator, ConfigDict, EmailStr
from typing import Optional, List
from datetime import datetime

class UserRegister(BaseModel):
    """Schema for user registration request."""
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50, 
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Username must be 3-50 characters, alphanumeric with underscores/hyphens"
    )
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="Password must be at least 8 characters"
    )

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate that password meets security requirements."""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserLogin(BaseModel):
    """Schema for user login request."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    """Schema for user response data."""
    id: int
    username: str
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class CardCreate(BaseModel):
    """Schema for creating a new card in user collection."""
    name: str = Field(..., min_length=1, max_length=100, description="Card name")
    mana_cost: int = Field(..., ge=0, le=10, description="Mana cost (0-10)")
    rarity: str = Field(
        ..., 
        pattern="^(common|rare|epic|legendary)$",
        description="Card rarity: common, rare, epic, or legendary"
    )

    @field_validator('name')
    @classmethod
    def validate_card_name(cls, v: str) -> str:
        """Validate and normalize card name."""
        if not v.strip():
            raise ValueError('Card name cannot be empty or whitespace')
        return v.strip().title()


class CardUpdate(BaseModel):
    """Schema for updating card quantity in collection."""
    quantity: int = Field(..., ge=0, le=2, description="Quantity of card (0-2)")


class CardResponse(BaseModel):
    """Schema for card response data."""
    id: int
    name: str
    mana_cost: int
    rarity: str
    model_config = ConfigDict(from_attributes=True)


class CardInCollection(BaseModel):
    """Schema for card with collection-specific data."""
    card_id: int
    card_name: str
    mana_cost: int
    rarity: str
    quantity: int
    model_config = ConfigDict(from_attributes=True)


class CardListResponse(BaseModel):
    """Schema for paginated card list response."""
    cards: List[CardResponse]
    total: int
    skip: int
    limit: int
    model_config = ConfigDict(from_attributes=True)

class DeckCardEntry(BaseModel):
    """Schema for a card entry in deck composition."""
    card_id: int = Field(..., gt=0, description="ID of the card in global pool")
    quantity: int = Field(..., ge=1, le=2, description="Quantity of this card in deck (1-2)")


class DeckCreate(BaseModel):
    """Schema for creating a new deck."""
    name: str = Field(..., min_length=3, max_length=100, description="Deck name")
    description: Optional[str] = Field(
        None, 
        max_length=500, 
        description="Optional deck description"
    )
    cards: List[DeckCardEntry] = Field(
        ..., 
        description="Exactly 30 cards required for a valid deck"
    )

    @field_validator('cards')
    @classmethod
    def validate_deck_size(cls, v: List[DeckCardEntry]) -> List[DeckCardEntry]:
        """Validate that deck contains exactly 30 cards total."""
        total = sum(card.quantity for card in v)
        if total != 30:
            raise ValueError(f'Deck must contain exactly 30 cards, got {total}')
        return v


class DeckUpdate(BaseModel):
    """Schema for updating deck metadata."""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class DeckResponse(BaseModel):
    """Schema for basic deck response data."""
    id: int
    name: str
    description: Optional[str]
    creator_id: int
    model_config = ConfigDict(from_attributes=True)


class DeckDetailResponse(BaseModel):
    """Schema for detailed deck response with card list."""
    id: int
    name: str
    description: Optional[str]
    creator_id: int
    cards: List[DeckCardEntry]
    model_config = ConfigDict(from_attributes=True)


class DeckListResponse(BaseModel):
    """Schema for paginated deck list response."""
    decks: List[DeckResponse]
    total: int
    skip: int
    limit: int
    model_config = ConfigDict(from_attributes=True)

class RecommendationResponse(BaseModel):
    """Schema for deck recommendation response."""
    deck_id: Optional[int] = None
    deck_name: str
    match_percentage: float = Field(..., ge=0.0, le=100.0)
    missing_cards: List[str]
    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Unified error response schema for API errors."""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    path: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ValidationErrorDetail(BaseModel):
    """Schema for individual validation error details."""
    field: str
    message: str
    type: str


class ValidationErrorResponse(BaseModel):
    """Schema for validation error responses."""
    detail: str = "Validation failed"
    errors: List[ValidationErrorDetail]
    error_code: str = "VALIDATION_ERROR"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(from_attributes=True)