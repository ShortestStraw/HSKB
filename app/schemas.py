from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)

class CardCreate(BaseModel):
    name: str
    mana_cost: int = Field(..., ge=0, le=10)
    rarity: str = Field(..., pattern="^(common|rare|epic|legendary)$")

class CardInCollection(BaseModel):
    card_id: int
    card_name: str
    mana_cost: int
    rarity: str
    quantity: int
    model_config = ConfigDict(from_attributes=True)

class DeckCardEntry(BaseModel):
    card_id: int
    quantity: int = Field(..., ge=1)

class DeckCreate(BaseModel):
    name: str
    description: Optional[str] = None
    cards: List[DeckCardEntry]

class DeckResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    model_config = ConfigDict(from_attributes=True)

class RecommendationResponse(BaseModel):
    deck_id: Optional[int] = None
    deck_name: str
    match_percentage: float
    missing_cards: List[str]